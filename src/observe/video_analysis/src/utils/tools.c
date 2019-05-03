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

#include "settings.h"
#include "settings_webcam.h"

#define MIN(X, Y) (((X) < (Y)) ? (X) : (Y))
#define MAX(X, Y) (((X) > (Y)) ? (X) : (Y))

void writeRawVidMetaData(videoMetadata v) {
    char fname[FNAME_BUFFER];
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

int nearestMultiple(double in, int factor) {
    return (int) (round(in / factor) * factor);
}

void frameInvert(unsigned char *buffer, int len) {
    int i;
    int imax = len / 2;
#pragma omp parallel for private(i)
    for (i = 0; i < imax; i++) {
        int j = len - 1 - i;
        unsigned char tmp = buffer[i];
        buffer[i] = buffer[j];
        buffer[j] = tmp;
    }
    return;
}

void *videoRecord(struct vdIn *videoIn, double seconds) {
    int i;
    const int frameSize = videoIn->width * videoIn->height * 3 / 2;
    const int nfr = videoIn->fps * seconds;
    const int blen = sizeof(int) + 2 * sizeof(int) + nfr * frameSize;
    void *out = malloc(blen);
    if (!out) return out;
    void *ptr = out;
    *(int *) ptr = blen;
    ptr += sizeof(int);
    *(int *) ptr = videoIn->width;
    ptr += sizeof(int);
    *(int *) ptr = videoIn->height;
    ptr += sizeof(int);

    for (i = 0; i < nfr; i++) {
        if (uvcGrab(videoIn) < 0) {
            printf("Error grabbing\n");
            break;
        }
        Pyuv422to420(videoIn->framebuffer, ptr, videoIn->width, videoIn->height, VIDEO_UPSIDE_DOWN);
        ptr += frameSize;
    }

    return out;
}

void snapshot(struct vdIn *videoIn, int nfr, int zero, double expComp, char *fname, unsigned char *backgroundRaw) {
    int i, j;
    const int frameSize = videoIn->width * videoIn->height;
    int *tmpi = calloc(3 * frameSize * sizeof(int), 1);
    if (!tmpi) return;

    for (j = 0; j < nfr; j++) {
        if (uvcGrab(videoIn) < 0) {
            printf("Error grabbing\n");
            break;
        }
        Pyuv422torgbstack(videoIn->framebuffer, tmpi, tmpi + frameSize, tmpi + 2 * frameSize, videoIn->width,
                          videoIn->height, VIDEO_UPSIDE_DOWN);
    }

    image_ptr img;
    image_alloc(&img, videoIn->width, videoIn->height);
    for (i = 0; i < frameSize; i++) img.data_w[i] = nfr;

    if (!backgroundRaw) {
        for (i = 0; i < frameSize; i++) img.data_red[i] = (tmpi[i] - zero * nfr) * expComp;
        for (i = 0; i < frameSize; i++) img.data_grn[i] = (tmpi[i + frameSize] - zero * nfr) * expComp;
        for (i = 0; i < frameSize; i++) img.data_blu[i] = (tmpi[i + 2 * frameSize] - zero * nfr) * expComp;
    } else {
        for (i = 0; i < frameSize; i++) img.data_red[i] = (tmpi[i] - (zero - backgroundRaw[i]) * nfr) * expComp;
        for (i = 0; i < frameSize; i++)
            img.data_grn[i] = (tmpi[i + frameSize] - (zero - backgroundRaw[i + frameSize]) * nfr) * expComp;
        for (i = 0; i < frameSize; i++)
            img.data_blu[i] = (tmpi[i + 2 * frameSize] - (zero - backgroundRaw[i + 2 * frameSize]) * nfr) * expComp;
    }

    image_deweight(&img);
    image_put(fname, img, ALLDATAMONO);
    image_dealloc(&img);

    free(tmpi);
    return;
}

double estimateNoiseLevel(int width, int height, unsigned char *buffer, int Nframes) {
    const int frameSize = width * height;
    const int frameStride = 3 * frameSize / 2;
    const int pixelStride = 499; // Only study every 499th pixel
    const int NStudyPixels = frameSize / pixelStride;
    int *sum_y = calloc(NStudyPixels, sizeof(int));
    int *sum_y2 = calloc(NStudyPixels, sizeof(int));
    if ((!sum_y) || (!sum_y2)) return -1;

    int frame, i;
    for (frame = 0; frame < Nframes; frame++) {
        for (i = 0; i < NStudyPixels; i++) {
            const int pixelVal = buffer[frame * frameStride + i * pixelStride];
            sum_y[i] += pixelVal;
            sum_y2[i] += pixelVal * pixelVal;
        }
    }

    double sd_sum = 0;
    for (i = 0; i < NStudyPixels; i++) {
        double mean = sum_y[i] / ((double) NStudyPixels);
        double sd = sqrt(sum_y2[i] / ((double) NStudyPixels) - mean * mean);
        sd_sum += sd;
    }

    free(sum_y);
    free(sum_y2);
    return sd_sum / NStudyPixels; // Average standard deviation of the studied pixels
}

void backgroundCalculate(const int width, const int height, const int channels, const int reductionCycle,
                     const int NreductionCycles, int *backgroundWorkspace, unsigned char *backgroundMap) {
    const int frameSize = width * height;
    int i;

    const int i_max = frameSize * channels;
    const int i_step = i_max / NreductionCycles + 1;
    const int i_start = i_step * reductionCycle;
    const int i_stop = MIN(i_max, i_start + i_step);

    // Find the modal value of each cell in the background grid
#pragma omp parallel for private(i)
    for (i = i_start; i < i_stop; i++) {
        int f, d;
        const int offset = i * 256;
        int mode = 0, modeSamples = 0;
        for (f = 4; f < 256; f++) {
            const int v = 4 * backgroundWorkspace[offset + f - 4] + 8 * backgroundWorkspace[offset + f - 3] +
                          10 * backgroundWorkspace[offset + f - 2] + 8 * backgroundWorkspace[offset + f - 1] +
                          4 * backgroundWorkspace[offset + f - 0];
            if (v > modeSamples) {
                mode = f;
                modeSamples = v;
            }
        }
        // This is a slight over-estimate of the background sky brightness, but images look less noisy that way.
        backgroundMap[i] = CLIP256(mode - 1);
    }
    return;
}

int dumpFrame(int width, int height, int channels, const unsigned char *buffer, char *fName) {
    FILE *outfile;
    const int frameSize = width * height;
    if ((outfile = fopen(fName, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", fName);
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(buffer, 1, frameSize * channels, outfile);
    fclose(outfile);
    return 0;
}

int dumpFrameFromInts(int width, int height, int channels, const int *buffer, int nfr, int targetBrightness, int *gainOut, char *fName) {
    FILE *outfile;
    int frameSize = width * height;
    unsigned char *tmpc = malloc(frameSize * channels);
    if (!tmpc) {
        sprintf(temp_err_string, "ERROR: malloc fail in dumpFrameFromInts.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    if ((outfile = fopen(fName, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", fName);
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    int i, d;

    // Work out what gain to apply to the image
    int gain = 1;
    if (targetBrightness > 0) {
        double brightness_sum=32;
        int brightness_points=1;
        for (i = 0; i < frameSize; i+=199) {
            brightness_sum += buffer[i];
            brightness_points++;
        }
        gain = (int)(targetBrightness / (brightness_sum / nfr / brightness_points));
        if (gain<1) gain=1;
        if (gain>30) gain=30;
    }

    // Report the gain we are using as an output
    if (gainOut != NULL) *gainOut = gain;

    // Renormalise image data, dividing by the number of frames which have been stacked, and multiplying by gain factor
#pragma omp parallel for private(i,d)
    for (i = 0; i < frameSize * channels; i++) tmpc[i] = CLIP256(buffer[i] * gain / nfr);

    // Write image data to raw file
    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(tmpc, 1, frameSize * channels, outfile);
    fclose(outfile);
    free(tmpc);
    return 0;
}

int dumpFrameFromISub(int width, int height, int channels, const int *buffer, int nfr, int targetBrightness, int *gainOut,
                      const unsigned char *buffer2, char *fName) {
    FILE *outfile;
    int frameSize = width * height;
    unsigned char *tmpc = malloc(frameSize * channels);
    if (!tmpc) {
        sprintf(temp_err_string, "ERROR: malloc fail in dumpFrameFromInts.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    if ((outfile = fopen(fName, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", fName);
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    int i, d;

    // Work out what gain to apply to the image
    int gain = 1;
    if (targetBrightness > 0) {
        double brightness_sum=32;
        int brightness_points=1;
        for (i = 0; i < frameSize; i+=199) {
            int level = buffer[i] - nfr * buffer2[i];
            if (level<0) level=0;
            brightness_sum += level;
            brightness_points++;
        }
        gain = (int)(targetBrightness / (brightness_sum / nfr / brightness_points));
        if (gain<1) gain=1;
        if (gain>30) gain=30;
    }

    // Report the gain we are using as an output
    if (gainOut != NULL) *gainOut = gain;

    // Renormalise image data, dividing by the number of frames which have been stacked, and multiplying by gain factor
#pragma omp parallel for private(i,d)
    for (i = 0; i < frameSize * channels; i++) tmpc[i] = CLIP256((buffer[i] - nfr * buffer2[i]) * gain / nfr);

    // Write image data to raw file
    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(tmpc, 1, frameSize * channels, outfile);
    fclose(outfile);
    free(tmpc);
    return 0;
}


FILE *dumpVideoInit(int width, int height, const unsigned char *buffer1, int buffer1frames,
                    const unsigned char *buffer2, int buffer2frames, char *fName) {
    const size_t frameSize = (size_t) (width * height * 3 / 2);
    const int blen = (int) (sizeof(int) + 2 * sizeof(int) + (buffer1frames + buffer2frames) * frameSize);

    FILE *outfile;
    if ((outfile = fopen(fName, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW video file %s.\n", fName);
        gnom_error(ERR_GENERAL, temp_err_string);
        return NULL;
    }

    fwrite(&blen, 1, sizeof(int), outfile);
    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    return outfile;
}


int dumpVideoFrame(int width, int height, const unsigned char *buffer1, int buffer1frames, const unsigned char *buffer2,
                   int buffer2frames, FILE *outfile, int *framesWritten) {
    const size_t frameSize = (size_t) (width * height * 3 / 2);

    const int totalFrames = buffer1frames + buffer2frames;
    const int framesToWrite = MIN(totalFrames - *framesWritten, TRIGGER_FRAMEGROUP);
    int i;

    for (i = 0; i < framesToWrite; i++) {
        if (*framesWritten < buffer1frames)
            fwrite(buffer1 + (*framesWritten) * frameSize, frameSize, 1, outfile);
        else
            fwrite(buffer2 + (*framesWritten - buffer1frames) * frameSize, frameSize, 1, outfile);
        (*framesWritten)++;
    }
    if (*framesWritten >= totalFrames) {
        fclose(outfile);
        return 0;
    }
    return 1;
}

