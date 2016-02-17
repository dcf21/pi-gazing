// tools.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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

void snapshot(struct vdIn *videoIn, int nfr, int zero, double expComp, char *fname, unsigned char *medianRaw) {
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
    img.data_w = nfr;

    if (!medianRaw) {
        for (i = 0; i < frameSize; i++) img.data_red[i] = (tmpi[i] - zero * nfr) * expComp;
        for (i = 0; i < frameSize; i++) img.data_grn[i] = (tmpi[i + frameSize] - zero * nfr) * expComp;
        for (i = 0; i < frameSize; i++) img.data_blu[i] = (tmpi[i + 2 * frameSize] - zero * nfr) * expComp;
    } else {
        for (i = 0; i < frameSize; i++) img.data_red[i] = (tmpi[i] - (zero - medianRaw[i]) * nfr) * expComp;
        for (i = 0; i < frameSize; i++)
            img.data_grn[i] = (tmpi[i + frameSize] - (zero - medianRaw[i + frameSize]) * nfr) * expComp;
        for (i = 0; i < frameSize; i++)
            img.data_blu[i] = (tmpi[i + 2 * frameSize] - (zero - medianRaw[i + 2 * frameSize]) * nfr) * expComp;
    }

    image_deweight(&img);
    image_put(fname, img, ALLDATAMONO);
    image_dealloc(&img);

    free(tmpi);
    return;
}

double calculateSkyClarity(image_ptr *img, double noiseLevel) {
    int i, j, score = 0;
    const int gridsize = 10;
    const int search_distance = 4;

    // To be counted as a star-like source, must be this much brighter than surroundings
    const int threshold = MAX(12, noiseLevel * 4);
    const int stride = img->xsize;
#pragma omp parallel for private(i,j)
    for (i = 1; i < gridsize; i++)
        for (j = 1; j < gridsize; j++) {
            const int xmin = img->xsize * j / (gridsize + 1);
            const int ymin = img->ysize * i / (gridsize + 1);
            const int xmax = img->xsize * (j + 1) / (gridsize + 1);
            const int ymax = img->ysize * (i + 1) / (gridsize + 1);
            int x, y, n_bright_pixels = 0, n_stars = 0;
            const int n_pixels = (xmax-xmin)*(ymax-ymin);
            for (y = ymin; y < ymax; y++)
                for (x = xmin; x < xmax; x++) {
                    double pixel_value = img->data_red[y * stride + x];
                    if (pixel_value > 128) n_bright_pixels++;
                    int k, counter = 0;
                    for (k=-search_distance; k<=search_distance; k+=2)
                        if (pixel_value - threshold <= img->data_red[(y + search_distance) * stride + (x + k)] )
                            counter++;
                    for (k=-search_distance; k<=search_distance; k+=2)
                        if (pixel_value - threshold <= img->data_red[(y - search_distance) * stride + (x + k)] )
                            counter++;
                    for (k=-search_distance; k<=search_distance; k+=2)
                        if (pixel_value - threshold <= img->data_red[(y + k) * stride + (x + search_distance)] )
                            counter++;
                    for (k=-search_distance; k<=search_distance; k+=2)
                        if (pixel_value - threshold <= img->data_red[(y + k) * stride + (x - search_distance)] )
                            counter++;

                    if (counter <= 1) n_stars++;
                }
            if ((n_stars >= 4)&&(n_bright_pixels<n_pixels*0.1)) {
#pragma omp critical (count_stars)
              { score++; }
             }
        }
    return (100. * score) / pow(gridsize - 1, 2);
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

void medianCalculate(const int width, const int height, const int channels, const int reductionCycle,
                     const int NreductionCycles, int *medianWorkspace, unsigned char *medianMap) {
    const int frameSize = width * height;
    int i;

    const int i_max = frameSize * channels;
    const int i_step = i_max / NreductionCycles + 1;
    const int i_start = i_step * reductionCycle;
    const int i_stop = MIN(i_max, i_start + i_step);

    // Find the modal value of each cell in the median grid
#pragma omp parallel for private(i)
    for (i = i_start; i < i_stop; i++) {
        int f, d;
        const int offset = i * 256;
        int mode = 0, modeSamples = 0;
        for (f = 4; f < 256; f++) {
            const int v = 4 * medianWorkspace[offset + f - 4] + 8 * medianWorkspace[offset + f - 3] +
                          10 * medianWorkspace[offset + f - 2] + 8 * medianWorkspace[offset + f - 1] +
                          4 * medianWorkspace[offset + f - 0];
            if (v > modeSamples) {
                mode = f;
                modeSamples = v;
            }
        }
        // This is a slight over-estimate of the background sky brightness, but images look less noisy that way.
        medianMap[i] = CLIP256(mode + 1);
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

int dumpFrameFromInts(int width, int height, int channels, const int *buffer, int nfr, int gain, char *fName) {
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
#pragma omp parallel for private(i,d)
    for (i = 0; i < frameSize * channels; i++) tmpc[i] = CLIP256(buffer[i] * gain / nfr);

    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(tmpc, 1, frameSize * channels, outfile);
    fclose(outfile);
    free(tmpc);
    return 0;
}

int dumpFrameFromISub(int width, int height, int channels, const int *buffer, int nfr, int gain,
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
#pragma omp parallel for private(i,d)
    for (i = 0; i < frameSize * channels; i++) tmpc[i] = CLIP256((buffer[i] - nfr * buffer2[i]) * gain / nfr);

    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(&channels, 1, sizeof(int), outfile);
    fwrite(tmpc, 1, frameSize * channels, outfile);
    fclose(outfile);
    free(tmpc);
    return 0;
}


int dumpVideo(int width, int height, const unsigned char *buffer1, int buffer1frames, const unsigned char *buffer2,
              int buffer2frames, char *fName) {
    const int frameSize = width * height * 1.5;
    const int blen = sizeof(int) + 2 * sizeof(int) + (buffer1frames + buffer2frames) * frameSize;

    FILE *outfile;
    if ((outfile = fopen(fName, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW video file %s.\n", fName);
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    fwrite(&blen, 1, sizeof(int), outfile);
    fwrite(&width, 1, sizeof(int), outfile);
    fwrite(&height, 1, sizeof(int), outfile);
    fwrite(buffer1, 1, frameSize * buffer1frames, outfile);
    fwrite(buffer2, 1, frameSize * buffer2frames, outfile);
    fclose(outfile);
    return 0;
}

