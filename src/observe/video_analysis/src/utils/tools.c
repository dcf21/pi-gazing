// tools.c
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2019 Dominic Ford.

// This file is part of Pi Gazing.

// Pi Gazing is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Pi Gazing is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <unistd.h>
#include "vidtools/v4l2uvc.h"
#include "png/image.h"
#include "vidtools/color.h"
#include "utils/error.h"
#include "utils/tools.h"

#include "str_constants.h"
#include "settings.h"
#include "settings_webcam.h"

#define MIN(X, Y) (((X) < (Y)) ? (X) : (Y))
#define MAX(X, Y) (((X) > (Y)) ? (X) : (Y))

void write_raw_video_metadata(video_metadata v) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s.txt", v.filename);
    FILE *f = fopen(fname, "w");
    if (!f) return;
    fprintf(f, "obstoryId %s\n", v.obstoryId);
    fprintf(f, "tstart %.1f\n", v.tstart);
    fprintf(f, "tstop %.1f\n", v.tstop);
    fprintf(f, "nframe %d\n", v.nframe);
    fprintf(f, "fps %.6f\n", v.nframe / (v.tstop - v.tstart));
    fprintf(f, "fpsTarget %.6f\n", v.fps);
    fprintf(f, "flagGPS %d\n", v.flagGPS);
    fprintf(f, "lat %.6f\n", v.lat);
    fprintf(f, "lng %.6f\n", v.lng);
    fclose(f);
}

int nearest_multiple(double in, int factor) {
    return (int) (round(in / factor) * factor);
}

void frame_invert(unsigned char *buffer, int len) {
    int i;
    int imax = len / 2;
#pragma omp parallel for private(i)
    for (i = 0; i < imax; i++) {
        int j = len - 1 - i;
        unsigned char tmp = buffer[i];
        buffer[i] = buffer[j];
        buffer[j] = tmp;
    }
}

void *video_record(struct vdIn *video_in, double seconds) {
    int i;
    const int frameSize = video_in->width * video_in->height * 3 / 2;
    const int nfr = video_in->fps * seconds;
    const int blen = sizeof(int) + 2 * sizeof(int) + nfr * frameSize;
    void *out = malloc(blen);
    if (!out) return out;
    void *ptr = out;
    *(int *) ptr = blen;
    ptr += sizeof(int);
    *(int *) ptr = video_in->width;
    ptr += sizeof(int);
    *(int *) ptr = video_in->height;
    ptr += sizeof(int);

    for (i = 0; i < nfr; i++) {
        if (uvcGrab(video_in) < 0) {
            printf("Error grabbing\n");
            break;
        }
        Pyuv422to420(video_in->framebuffer, ptr, video_in->width, video_in->height, VIDEO_UPSIDE_DOWN);
        ptr += frameSize;
    }

    return out;
}

void snapshot(struct vdIn *video_in, int frame_count, int zero, double exposure_compensation, char *filename,
              unsigned char *background_raw) {
    int i, j;
    const int frame_size = video_in->width * video_in->height;
    int *tmp_int = calloc(3 * frame_size * sizeof(int), 1);
    if (!tmp_int) return;

    for (j = 0; j < frame_count; j++) {
        if (uvcGrab(video_in) < 0) {
            printf("Error grabbing\n");
            break;
        }
        Pyuv422torgbstack(video_in->framebuffer, tmp_int, tmp_int + frame_size, tmp_int + 2 * frame_size,
                          video_in->width,
                          video_in->height, VIDEO_UPSIDE_DOWN);
    }

    image_ptr img;
    image_alloc(&img, video_in->width, video_in->height);
    for (i = 0; i < frame_size; i++) img.data_w[i] = frame_count;

    if (!background_raw) {
        for (i = 0; i < frame_size; i++) img.data_red[i] = (tmp_int[i] - zero * frame_count) * exposure_compensation;
        for (i = 0; i < frame_size; i++)
            img.data_grn[i] = (tmp_int[i + frame_size] - zero * frame_count) * exposure_compensation;
        for (i = 0; i < frame_size; i++)
            img.data_blu[i] = (tmp_int[i + 2 * frame_size] - zero * frame_count) * exposure_compensation;
    } else {
        for (i = 0; i < frame_size; i++)
            img.data_red[i] = (tmp_int[i] - (zero - background_raw[i]) * frame_count) * exposure_compensation;
        for (i = 0; i < frame_size; i++)
            img.data_grn[i] = (tmp_int[i + frame_size] - (zero - background_raw[i + frame_size]) * frame_count) *
                              exposure_compensation;
        for (i = 0; i < frame_size; i++)
            img.data_blu[i] =
                    (tmp_int[i + 2 * frame_size] - (zero - background_raw[i + 2 * frame_size]) * frame_count) *
                    exposure_compensation;
    }

    image_deweight(&img);
    image_put(filename, img, GREYSCALE_IMAGING);
    image_dealloc(&img);

    free(tmp_int);
}

double estimate_noise_level(int width, int height, unsigned char *buffer, int frame_count) {
    const int frame_size = width * height;
    const int frame_stride = 3 * frame_size / 2;
    const int pixel_stride = 499; // Only study every 499th pixel
    const int study_pixel_count = frame_size / pixel_stride;
    int *sum_y = calloc(study_pixel_count, sizeof(int));
    int *sum_y2 = calloc(study_pixel_count, sizeof(int));
    if ((!sum_y) || (!sum_y2)) return -1;

    int frame, i;
    for (frame = 0; frame < frame_count; frame++) {
        for (i = 0; i < study_pixel_count; i++) {
            const int pixelVal = buffer[frame * frame_stride + i * pixel_stride];
            sum_y[i] += pixelVal;
            sum_y2[i] += pixelVal * pixelVal;
        }
    }

    double sd_sum = 0;
    for (i = 0; i < study_pixel_count; i++) {
        double mean = sum_y[i] / ((double) study_pixel_count);
        double sd = sqrt(sum_y2[i] / ((double) study_pixel_count) - mean * mean);
        sd_sum += sd;
    }

    free(sum_y);
    free(sum_y2);
    return sd_sum / study_pixel_count; // Average standard deviation of the studied pixels
}

void background_calculate(const int width, const int height, const int channels, const int reduction_cycle,
                          const int reduction_cycle_count, int *background_workspace, unsigned char *background_map) {
    const int frame_size = width * height;
    int i;

    const int i_max = frame_size * channels;
    const int i_step = i_max / reduction_cycle_count + 1;
    const int i_start = i_step * reduction_cycle;
    const int i_stop = MIN(i_max, i_start + i_step);

    // Find the modal value of each cell in the background grid
#pragma omp parallel for private(i)
    for (i = i_start; i < i_stop; i++) {
        int f, d;
        const int offset = i * 256;
        int mode = 0, mode_samples = 0;
        for (f = 4; f < 256; f++) {
            const int v = 4 * background_workspace[offset + f - 4] + 8 * background_workspace[offset + f - 3] +
                          10 * background_workspace[offset + f - 2] + 8 * background_workspace[offset + f - 1] +
                          4 * background_workspace[offset + f - 0];
            if (v > mode_samples) {
                mode = f;
                mode_samples = v;
            }
        }
        // This is a slight over-estimate of the background sky brightness, but images look less noisy that way.
        background_map[i] = CLIP256(mode - 1);
    }
}

int dump_frame(int width, int height, int channels, const unsigned char *buffer, char *filename) {
    FILE *outfile;
    const int frameSize = width * height;
    if ((outfile = fopen(filename, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(buffer, 1, frameSize * channels, outfile);
    fclose(outfile);
    return 0;
}

int dump_frame_from_ints(int width, int height, int channels, const int *buffer, int frame_count, int target_brightness,
                         int *gain_out, char *filename) {
    FILE *out_file;
    int frame_size = width * height;
    unsigned char *tmpc = malloc(frame_size * channels);
    if (!tmpc) {
        sprintf(temp_err_string, "ERROR: malloc fail in dump_frame_from_ints.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    if ((out_file = fopen(filename, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    int i, d;

    // Work out what gain to apply to the image
    int gain = 1;
    if (target_brightness > 0) {
        double brightness_sum = 32;
        int brightness_points = 1;
        for (i = 0; i < frame_size; i += 199) {
            brightness_sum += buffer[i];
            brightness_points++;
        }
        gain = (int) (target_brightness / (brightness_sum / frame_count / brightness_points));
        if (gain < 1) gain = 1;
        if (gain > 30) gain = 30;
    }

    // Report the gain we are using as an output
    if (gain_out != NULL) *gain_out = gain;

    // Renormalise image data, dividing by the number of frames which have been stacked, and multiplying by gain factor
#pragma omp parallel for private(i, d)
    for (i = 0; i < frame_size * channels; i++) tmpc[i] = CLIP256(buffer[i] * gain / frame_count);

    // Write image data to raw file
    fwrite(&width, 1, sizeof(int), out_file);
    fwrite(&height, 1, sizeof(int), out_file);
    fwrite(&channels, 1, sizeof(int), out_file);
    fwrite(tmpc, 1, frame_size * channels, out_file);
    fclose(out_file);
    free(tmpc);
    return 0;
}

int dump_frame_from_int_subtraction(int width, int height, int channels, const int *buffer, int frame_count,
                                    int target_brightness, int *gain_out,
                                    const unsigned char *buffer2, char *filename) {
    FILE *outfile;
    int frame_size = width * height;
    unsigned char *tmpc = malloc(frame_size * channels);
    if (!tmpc) {
        sprintf(temp_err_string, "ERROR: malloc fail in dump_frame_from_ints.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    if ((outfile = fopen(filename, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    int i, d;

    // Work out what gain to apply to the image
    int gain = 1;
    if (target_brightness > 0) {
        double brightness_sum = 32;
        int brightness_points = 1;
        for (i = 0; i < frame_size; i += 199) {
            int level = buffer[i] - frame_count * buffer2[i];
            if (level < 0) level = 0;
            brightness_sum += level;
            brightness_points++;
        }
        gain = (int) (target_brightness / (brightness_sum / frame_count / brightness_points));
        if (gain < 1) gain = 1;
        if (gain > 30) gain = 30;
    }

    // Report the gain we are using as an output
    if (gain_out != NULL) *gain_out = gain;

    // Renormalise image data, dividing by the number of frames which have been stacked, and multiplying by gain factor
#pragma omp parallel for private(i, d)
    for (i = 0; i < frame_size * channels; i++)
        tmpc[i] = CLIP256((buffer[i] - frame_count * buffer2[i]) * gain / frame_count);

    // Write image data to raw file
    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(tmpc, 1, frame_size * channels, outfile);
    fclose(outfile);
    free(tmpc);
    return 0;
}


FILE *dump_video_init(int width, int height, const unsigned char *buffer1, int buffer1_frames,
                      const unsigned char *buffer2, int buffer2_frames, char *filename) {
    const size_t frame_size = (size_t) (width * height * 3 / 2);
    const int buffer_len = (int) (sizeof(int) + 2 * sizeof(int) + (buffer1_frames + buffer2_frames) * frame_size);

    FILE *outfile;
    if ((outfile = fopen(filename, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW video file %s.\n", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return NULL;
    }

    fwrite(&buffer_len, 1, sizeof(int), outfile);
    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    return outfile;
}


int dump_video_frame(int width, int height, const unsigned char *buffer1, int buffer1_frames,
                     const unsigned char *buffer2,
                     int buffer2_frames, FILE *out_file, int *frames_written) {
    const size_t frameSize = (size_t) (width * height * 3 / 2);

    const int totalFrames = buffer1_frames + buffer2_frames;
    const int framesToWrite = MIN(totalFrames - *frames_written, TRIGGER_FRAMEGROUP);
    int i;

    for (i = 0; i < framesToWrite; i++) {
        if (*frames_written < buffer1_frames)
            fwrite(buffer1 + (*frames_written) * frameSize, frameSize, 1, out_file);
        else
            fwrite(buffer2 + (*frames_written - buffer1_frames) * frameSize, frameSize, 1, out_file);
        (*frames_written)++;
    }
    if (*frames_written >= totalFrames) {
        fclose(out_file);
        return 0;
    }
    return 1;
}
