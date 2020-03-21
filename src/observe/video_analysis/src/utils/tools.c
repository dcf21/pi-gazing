// tools.c
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

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
#include <stdint.h>
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

//! write_raw_video_metadata - Write a text-based metadata file to accompany a raw video file on disk
//! \param v Data structure containing metadata about the video file

void write_raw_video_metadata(video_metadata v) {
    char filename[FNAME_LENGTH];
    snprintf(filename, FNAME_LENGTH, "%s.txt", v.filename);
    FILE *f = fopen(filename, "w");
    if (!f) return;
    fprintf(f, "obstoryId %s\n", v.obstory_id);
    fprintf(f, "utc %.1f\n", v.utc_start);
    fprintf(f, "semanticType pigazing:");
    fprintf(f, "utc_start %.1f\n", v.utc_start);
    fprintf(f, "utc_stop %.1f\n", v.utc_stop);
    fprintf(f, "frame_count %d\n", v.frame_count);
    fprintf(f, "fps %.6f\n", v.frame_count / (v.utc_stop - v.utc_start));
    fprintf(f, "fpsTarget %.6f\n", v.fps);
    fprintf(f, "flag_gps %d\n", v.flag_gps);
    fprintf(f, "lat %.6f\n", v.lat);
    fprintf(f, "lng %.6f\n", v.lng);
    fclose(f);
}

//! nearest_multiple - Round the number <in> to the nearest multiple of the number <factor>
//! \param in Input number
//! \param factor Round to the nearest multiple of this number
//! \return Nearest multiple

int nearest_multiple(double in, int factor) {
    return (int) (round(in / factor) * factor);
}

//! frame_invert - Turn a single-channel video frame upside down, in place
//! \param buffer A character array of <len> pixels
//! \param len The number of pixels to invert

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

//! video_record - Record a period of raw video into a buffer
//! \param video_in Descriptor of the video frame to capture from
//! \param seconds The number of seconds of video to record
//! \return A buffer containing the recorded video

void *video_record(struct video_info *video_in, double seconds) {
    int i;
    const int frame_size = video_in->width * video_in->height * 3 / 2;
    const int frame_count = video_in->fps * seconds;
    const int buffer_len = sizeof(int) + 2 * sizeof(int) + frame_count * frame_size;

    void *out = malloc(buffer_len);
    if (!out) return out;

    void *ptr = out;
    *(int *) ptr = buffer_len;
    ptr += sizeof(int);
    *(int *) ptr = video_in->width;
    ptr += sizeof(int);
    *(int *) ptr = video_in->height;
    ptr += sizeof(int);

    for (i = 0; i < frame_count; i++) {
        if (uvcGrab(video_in) < 0) {
            printf("Error grabbing\n");
            break;
        }
        Pyuv422to420(video_in->frame_buffer, ptr, video_in->width, video_in->height, VIDEO_UPSIDE_DOWN);
        ptr += frame_size;
    }

    return out;
}

//! snapshot - Take a long-exposure image from an input video stream, by averaging many frames, and save to PNG
//! \param video_in Descriptor of the video frame to capture from
//! \param frame_count The number of video frames to average
//! \param zero Zero point to subtract from the input frames
//! \param exposure_compensation Multiplicative exposure compensation to apply to output image
//! \param filename The filename for the output image file (16-bit PNG file)
//! \param background_raw Optional character array containing the sky background to subtract from exposure

void snapshot(struct video_info *video_in, int frame_count, int zero, double exposure_compensation,
              const char *filename, const unsigned char *background_raw) {
    int i, j;
    const int frame_size = video_in->width * video_in->height;
    int *tmp_int = calloc(3 * frame_size * sizeof(int), 1);
    if (!tmp_int) return;

    for (j = 0; j < frame_count; j++) {
        if (j % 5 == 0) {
            printf("Fetching frame %7d / %7d\n", j, frame_count);
        }

        if (uvcGrab(video_in) < 0) {
            printf("Error grabbing\n");
            break;
        }
        Pyuv422torgbstack(video_in->frame_buffer, tmp_int, tmp_int + frame_size, tmp_int + 2 * frame_size,
                          video_in->width,
                          video_in->height, VIDEO_UPSIDE_DOWN);
    }

    image_ptr img;
    image_alloc(&img, video_in->width, video_in->height);
    for (i = 0; i < frame_size; i++) img.data_w[i] = frame_count / 256.;

    if (!background_raw) {
        for (i = 0; i < frame_size; i++)
            img.data_red[i] = (tmp_int[i] - zero * frame_count) * exposure_compensation;
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

    double sum = 0;
    for (i = 0; i < frame_size; i++) sum += img.data_grn[i];
    printf("%.1f\n", sum / frame_size);
    image_dealloc(&img);

    free(tmp_int);
}

//! estimate_noise_level - Estimate the noise level in an average pixel, by looking at the scatter in the values of
//! brightnesses of pixels in consecutive video frames.
//! \param width The width of the frames in the video buffer <buffer>
//! \param height The height of the frames in the video buffer <buffer>
//! \param buffer Buffer containing YUV colour video frames
//! \param frame_count The number of frames from which to estimate the noise level
//! \param mean_level The mean brightness of the camera field
//! \return The noise level

double estimate_noise_level(int width, int height, unsigned char *buffer, int frame_count, double *mean_level) {
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
    double mean_sum = 0;
    for (i = 0; i < study_pixel_count; i++) {
        double mean = sum_y[i] / ((double) frame_count);
        double sd = sqrt(sum_y2[i] / ((double) frame_count) - mean * mean);
        sd_sum += sd;
        mean_sum += mean;
    }

    // Clean up
    free(sum_y);
    free(sum_y2);

    // Return result
    *mean_level = mean_sum / study_pixel_count;
    return sd_sum / study_pixel_count; // Average standard deviation of the studied pixels
}

//! background_calculate - Estimate the sky background, using histograms of the past brightness of each pixel over the
//! last few minutes of observations. The sky brightness is taken as the mean brightness over those frames, which we
//! write into background_maps[background_buffer_current + 1].
//!
//! Because stars passing through pixels can skew their brightnesses to be anomalously bright for a minute or two, the
//! mean is a poor estimator of the true sky brightness. So, we hold a rolling buffer of the past
//! <background_buffer_count> background maps, held in the arrays background_maps[1...background_buffer_count]
//!
//! For each pixel, we take the lowest of these background estimates, and use that to create a master background map
//! which we store in background_maps[0], and which is relatively immune to stars brightening pixels for the few
//! minutes.
//!
//! All in all, this is a time-consuming task, and when doing real-time processing, we don't have time to process all
//! the pixels in one go. We process in pixels in <reduction_cycle_count> calls, of which this is number
//! <reduction_cycle>.
//!
//! \param width The width of the video frames
//! \param height The height of the video frames
//! \param channels The number of colour channels in use (1 for greyscale; 3 for RGB)
//! \param reduction_cycle When work is divided between multiple calls to this function, this is the number of the call
//! \param reduction_cycle_count The number of times this function will be called, to break up the work
//! \param background_workspace The workspace which contains the histograms of the recent brightnesses of pixels
//! \param background_maps The recent models of the sky background, to which we contribute
//!                        background_maps[background_buffer_current + 1]
//! \param background_buffer_count The number of background models we store in the rolling buffer in <background_maps>.
//! \param background_buffer_current The number of the background model we are currently writing

void background_calculate(const int width, const int height, const int channels, const int reduction_cycle,
                          const int reduction_cycle_count, const int *background_workspace,
                          int **background_maps,
                          const int background_buffer_count, const int background_buffer_current) {
    const int frame_size = width * height;
    int i;

    const int i_max = frame_size * channels;
    const int i_step = i_max / reduction_cycle_count + 1;
    const int i_start = i_step * reduction_cycle;
    const int i_stop = MIN(i_max, i_start + i_step);

    // Routine for sorting ints
    int compare_int(const void* a, const void* b) {
        return *((int*)a)-*((int*)b);
    }

    // Find the mean value of each cell in the background grid
#pragma omp parallel for private(i)
    for (i = i_start; i < i_stop; i++) {
        int f, j;
        const int offset = i * 256;
        int sum_x = 0, samples = 0;
        for (f = 0; f < 256; f++) {
            sum_x += f * 256 * background_workspace[offset + f];
            samples += background_workspace[offset + f];
        }

        // This is a slight under-estimate of the 16-bit background sky brightness
        int mean_brightness = (sum_x / samples) - 3*256;
        if (mean_brightness < 0) mean_brightness = 0;
        background_maps[background_buffer_current + 1][i] = mean_brightness;

        // We use the third-lowest of several recent background maps
        // * Stars can have black fringes, so the lowest background map may be bad
        // * When we switch in computing a new background map, the same pixel can be bad in two consecutive maps
        int sorted_values[background_buffer_count];
        for (j = 0; j < background_buffer_count; j++) {
            int v = background_maps[j + 1][i];
            sorted_values[j] = (v>0) ? v : mean_brightness;
        }
        qsort(sorted_values, background_buffer_count, sizeof(int), compare_int);
        background_maps[0][i] = sorted_values[2];
    }
}

//! dump_frame - Dump a single raw video frame to an 8-bit file
//! \param width The width of the frame
//! \param height The height of the frame
//! \param channels The number of colour channels to dump
//! \param buffer Array of unsigned chars representing each RGB channel in turn, size (channels * width * height)
//! \param filename The filename of the raw file we are to generate
//! \return Zero on success

int dump_frame(int width, int height, int channels, const unsigned char *buffer, char *filename) {
    FILE *outfile;
    const int frame_size = width * height;
    const int bit_width = 8;

    if ((outfile = fopen(filename, "wb")) == NULL) {
        snprintf(temp_err_string, FNAME_LENGTH, "ERROR: Cannot open output RAW image frame %s.\n", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(&bit_width, 1, sizeof(int), outfile);
    fwrite(buffer, 1, frame_size * channels, outfile);
    fclose(outfile);
    return 0;
}

//! dump_frame_from_ints - Dump a single raw video frame to a 16-bit file, from an array of ints
//! \param width The width of the frame
//! \param height The height of the frame
//! \param channels The number of colour channels to dump
//! \param buffer Array of ints representing each RGB channel in turn, size (channels * width * height)
//! \param frame_count The number of frames which have been co-added in <buffer>. We divide the pixels by this value.
//! \param target_brightness If non-zero, we attempt to renormalise the image to this mean brightness
//! \param gain_out If non-NULL, write the gain which was applied to the image.
//! \param filename The filename of the raw file we are to generate
//! \return Zero on success

int dump_frame_from_ints(int width, int height, int channels, const int *buffer, int frame_count, int target_brightness,
                         double *gain_out, char *filename) {
    FILE *out_file;
    int frame_size = width * height;
    const int bit_width = 16;

    uint16_t *tmp_frame = malloc(frame_size * channels * sizeof(uint16_t));
    if (!tmp_frame) {
        snprintf(temp_err_string, FNAME_LENGTH, "ERROR: malloc fail in dump_frame_from_ints.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    if ((out_file = fopen(filename, "wb")) == NULL) {
        snprintf(temp_err_string, FNAME_LENGTH, "ERROR: Cannot open output RAW image frame %s.\n", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    int i, d;

    // Work out what gain to apply to the image
    double gain = 1;
    if (target_brightness > 0) {
        double brightness_sum = 32;
        int brightness_points = 1;
        for (i = 0; i < frame_size; i += 199) {
            brightness_sum += buffer[i];
            brightness_points++;
        }
        gain = target_brightness / (brightness_sum / frame_count / brightness_points);
        if (gain < 1) gain = 1;
        if (gain > 30) gain = 30;
    }

    // Report the gain we are using as an output
    if (gain_out != NULL) *gain_out = gain;

    // Renormalise image data, dividing by the number of frames which have been stacked, and multiplying by gain factor
#pragma omp parallel for private(i, d)
    for (i = 0; i < frame_size * channels; i++) {
        tmp_frame[i] = CLIP65536(buffer[i] * 256 * gain / frame_count);
    }

    // Write image data to raw file
    fwrite(&width, 1, sizeof(int), out_file);
    fwrite(&height, 1, sizeof(int), out_file);
    fwrite(&channels, 1, sizeof(int), out_file);
    fwrite(&bit_width, 1, sizeof(int), out_file);
    fwrite(tmp_frame, 1, frame_size * channels * sizeof(uint16_t), out_file);
    fclose(out_file);
    free(tmp_frame);
    return 0;
}

//! dump_frame_from_int_subtraction - Dump a single raw video frame to a 16-bit file, from an array of ints. We
//! subtract the int values in buffer2 from those in buffer, which is useful for sky subtraction.
//! \param width The width of the frame
//! \param height The height of the frame
//! \param channels The number of colour channels to dump
//! \param buffer Array of ints representing each RGB channel in turn, size (channels * width * height)
//! \param frame_count The number of frames which have been co-added in <buffer>. We divide the pixels by this value.
//! \param target_brightness If non-zero, we attempt to renormalise the image to this mean brightness
//! \param gain_out If non-NULL, write the gain which was applied to the image.
//! \param buffer2 Array of ints which we subtract from the ints in buffer
//! \param filename The filename of the raw file we are to generate
//! \return Zero on success

int dump_frame_from_int_subtraction(int width, int height, int channels, const int *buffer, int frame_count,
                                    int target_brightness, double *gain_out,
                                    const int *buffer2, char *filename) {
    FILE *outfile;
    int frame_size = width * height;
    const int bit_width = 16;

    uint16_t *tmp_frame = malloc(frame_size * channels * sizeof(uint16_t));
    if (!tmp_frame) {
        snprintf(temp_err_string, FNAME_LENGTH, "ERROR: malloc fail in dump_frame_from_ints.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    if ((outfile = fopen(filename, "wb")) == NULL) {
        snprintf(temp_err_string, FNAME_LENGTH, "ERROR: Cannot open output RAW image frame %s.\n", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    int i, d;

    // Work out what gain to apply to the image
    double gain = 1;
    if (target_brightness > 0) {
        double brightness_sum = 32;
        int brightness_points = 1;
        for (i = 0; i < frame_size; i += 199) {
            double level = buffer[i] - frame_count * buffer2[i] / 256.;
            if (level < 0) level = 0;
            brightness_sum += level;
            brightness_points++;
        }
        gain = target_brightness / (brightness_sum / frame_count / brightness_points);
        if (gain < 1) gain = 1;
        if (gain > 30) gain = 30;
    }

    // Report the gain we are using as an output
    if (gain_out != NULL) *gain_out = gain;

    // Renormalise image data, dividing by the number of frames which have been stacked, and multiplying by gain factor
    // Producing 16-bit output, so amplify output by factor 256
    #pragma omp parallel for private(i, d)
    for (i = 0; i < frame_size * channels; i++) {
        tmp_frame[i] = CLIP65536((buffer[i] * 256 - frame_count * buffer2[i]) * gain / frame_count);
    }

    // Write image data to raw file
    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(&bit_width, 1, sizeof(int), outfile);
    fwrite(tmp_frame, 1, frame_size * channels * sizeof(uint16_t), outfile);
    fclose(outfile);
    free(tmp_frame);
    return 0;
}

//! dump_video_init - Open a file handle for writing a raw video to disk. Use <dump_video_frame> to write frames.
//! \param width The width of the new video
//! \param height The height of the new video
//! \param filename The filename for the new video file
//! \return File handle

FILE *dump_video_init(int width, int height, const char *filename) {

    const int buffer_len = 0;

    FILE *outfile;
    if ((outfile = fopen(filename, "wb")) == NULL) {
        snprintf(temp_err_string, FNAME_LENGTH, "ERROR: Cannot open output RAW video file %s.\n", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return NULL;
    }

    fwrite(&buffer_len, 1, sizeof(int), outfile);
    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    return outfile;
}

//! dump_video_frame - Write a single video frame to a raw video file
//! \param width The width of the new video
//! \param height The height of the new video
//! \param video_buffer The video buffer, containing YUV video, from which we should write a frame
//! \param video_buffer_frames The size of the video buffer (number of frames)
//! \param write_position The frame number within <video_buffer> that we should write. We advance this by one.
//! \param frames_written The number of frames written to the raw video file so far. We advance this by one.
//! \param write_end_position Finish writing the video file if write_position == write_end_position
//! \param output The file handle to the raw video file
//! \return Boolean flag indicating whether the raw video file is still open

int dump_video_frame(int width, int height, const unsigned char *video_buffer, const int video_buffer_frames,
                     int *write_position, int *frames_written, const int write_end_position,
                     FILE *output) {
    // Bytes per frame
    const size_t frame_size = (size_t) (width * height * 3 / 2);

    // Write one frame
    fseek(output, 3 * sizeof(int) + (*frames_written) * frame_size, SEEK_SET);

    fwrite(video_buffer + (*write_position) * frame_size, frame_size, 1, output);

    // Update frame counter
    (*frames_written)++;
    *write_position = ((*write_position) + 1) % video_buffer_frames;

    // Update file's metadata about how many frames it contains
    const int buffer_len = (*frames_written) * frame_size;
    fseek(output, 0, SEEK_SET);
    fwrite(&buffer_len, 1, sizeof(int), output);

    // Have we finished
    if (*write_position == write_end_position) {
        // Close output file
        fclose(output);
        return 0;
    }
    return 1;
}
