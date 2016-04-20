// trigger.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// -------------------------------------------------
// Copyright 2016 Cambridge Science Centre.

// This file is part of Meteor Pi.

// Meteor Pi is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Meteor Pi is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include "str_constants.h"
#include "analyse/observe.h"
#include "analyse/trigger.h"
#include "utils/asciidouble.h"
#include "utils/tools.h"
#include "utils/error.h"
#include "utils/JulianDate.h"
#include "vidtools/color.h"

#define MIN(X, Y) (((X) < (Y)) ? (X) : (Y))
#define MAX(X, Y) (((X) > (Y)) ? (X) : (Y))

// Used by testTrigger. When blocks idOld and idNew are determined to be connected, their pixels counts are added together.
inline void triggerBlocksMerge(observeStatus *os, int idOld, int idNew) {
    while (os->triggerBlock_redirect[idOld] > 0) idOld = os->triggerBlock_redirect[idOld];
    while (os->triggerBlock_redirect[idNew] > 0) idNew = os->triggerBlock_redirect[idNew];
    if (idOld == idNew) return;
    os->triggerBlock_N[idNew] += os->triggerBlock_N[idOld];
    os->triggerBlock_top[idNew] = MIN(os->triggerBlock_top[idNew], os->triggerBlock_top[idOld]);
    os->triggerBlock_bot[idNew] = MAX(os->triggerBlock_bot[idNew], os->triggerBlock_bot[idOld]);
    os->triggerBlock_sumx[idNew] += os->triggerBlock_sumx[idOld];
    os->triggerBlock_sumy[idNew] += os->triggerBlock_sumy[idOld];
    os->triggerBlock_suml[idNew] += os->triggerBlock_suml[idOld];
    os->triggerBlock_N[idOld] = 0;
    os->triggerBlock_redirect[idOld] = idNew;
    return;
}

static inline int testPixel(observeStatus *os, const int *image1, const int *image2, const int o, const int threshold) {
    const int radius = 16; // Pixel must be brighter than test pixels this distance away
    if (image1[o] - image2[o] >
        threshold) // Search for pixels which have brightened by more than threshold since past image
    {
        int i, j, c = 0; // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels. This pixel must be brighter than 6/9 of these pixels were
        for (i = -1; i <= 1; i++)
            for (j = -1; j <= 1; j++)
                if (image1[o] - image2[o + (j + i * os->width) * radius] > threshold)c++;
        if (c > 7) {
            int i, j, c = 0; // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels. This pixel must be brighter than 6/9 of these pixels were
            for (i = -1; i <= 1; i++)
                for (j = -1; j <= 1; j++)
                    if (image1[o] - image1[o + (j + i * os->width) * radius] > threshold)c++;
            if (c > 6) return 1;
        }
    }
    return 0;
}

// Test stacked images B and A, to see if pixels have brightened in B versus A. Image arrays contain the sum of <coAddedFrames> frames.
int checkForTriggers(observeStatus *os, const int *image1, const int *image2, const int coAddedFrames) {
    int y;
    int output = 0;

    const int margin = 20; // Ignore pixels within this distance of the edge
    const int threshold_blockSize = 7; // To trigger this number of pixels connected together must have brightened
    const int threshold_intensity =
            110 * os->noiseLevel * sqrt(coAddedFrames); // Total brightness excess must be 110 standard deviations
    const int thresholdTrigger = MAX(1, 3.5 * os->noiseLevel *
                                        sqrt(coAddedFrames)); // Pixel must have brightened by at least N standard deviations to trigger
    const int thresholdMonitor = MAX(1, 2.0 * os->noiseLevel *
                                        sqrt(coAddedFrames)); // Monitor and flag pixels which brighten by this amount
    unsigned char *triggerR = os->triggerRGB;
    unsigned char *triggerG = os->triggerRGB + os->frameSize *
                                               1; // These arrays are used to produce diagnostic images when the camera triggers
    unsigned char *triggerB = os->triggerRGB + os->frameSize * 2;
    memset(os->triggerMap, 0, os->frameSize * sizeof(int));
    os->Nblocks = 0;

    static unsigned long long pastTriggerMapAverage = 1;
    unsigned int nPixelsWithinMask = 1;
    unsigned long long pastTriggerMapAverageNew = 0;

#pragma omp parallel for private(y)
    for (y = margin; y < os->height - margin; y++) {
        int x, d;
        int triggerMap_linesum = 0, nPixelsWithinMask_linesum = 0;
        for (x = margin; x < os->width - margin; x++) {
            const int o = x + y * os->width;
            triggerMap_linesum += os->pastTriggerMap[o];
            if (os->mask[o]) nPixelsWithinMask_linesum++;
            triggerR[o] = CLIP256(
                    (image1[o] - image2[o]) * 64 / thresholdTrigger); // RED channel - difference between images B and A
            triggerG[o] = CLIP256(os->pastTriggerMap[o] * 256 / (2.3 *
                                                                 pastTriggerMapAverage)); // GRN channel - map of pixels which are excluded for triggering too often
            triggerB[o] = 0;
            if ((os->mask[o]) && testPixel(os, image1, image2, o, thresholdMonitor)) {
                os->pastTriggerMap[o]++;
                if (testPixel(os, image1, image2, o,
                              thresholdTrigger)) // Search for pixels which have brightened by more than threshold since past image
                {
                    os->pastTriggerMap[o]++;
#pragma omp critical (add_trigger)
                    {
                        // Put triggering pixel on map. Wait till be have <Npixels> connected pixels.
                        triggerB[o] = (os->pastTriggerMap[o] < 3 * pastTriggerMapAverage) ? 63 : 31;
                        int blockId = 0;
                        if (os->triggerMap[o - 1]) {
                            if (!blockId) {
                                blockId = os->triggerMap[o - 1];
                            } else { triggerBlocksMerge(os, os->triggerMap[o - 1], blockId); }
                        }
                        if (os->triggerMap[o + 1 - os->width]) {
                            if (!blockId) {
                                blockId = os->triggerMap[o + 1 - os->width];
                            } else { triggerBlocksMerge(os, os->triggerMap[o + 1 - os->width], blockId); }
                        }
                        if (os->triggerMap[o - os->width]) {
                            if (!blockId) {
                                blockId = os->triggerMap[o - os->width];
                            } else { triggerBlocksMerge(os, os->triggerMap[o - os->width], blockId); }
                        }
                        if (os->triggerMap[o - 1 - os->width]) {
                            if (!blockId) {
                                blockId = os->triggerMap[o - 1 - os->width];
                            } else { triggerBlocksMerge(os, os->triggerMap[o - 1 - os->width], blockId); }
                        }
                        if (os->triggerMap[o + 1 + os->width]) {
                            if (!blockId) {
                                blockId = os->triggerMap[o + 1 + os->width];
                            } else { triggerBlocksMerge(os, os->triggerMap[o + 1 + os->width], blockId); }
                        }
                        if (os->triggerMap[o + os->width]) {
                            if (!blockId) {
                                blockId = os->triggerMap[o + os->width];
                            } else { triggerBlocksMerge(os, os->triggerMap[o + os->width], blockId); }
                        }
                        if (os->triggerMap[o - 1 + os->width]) {
                            if (!blockId) {
                                blockId = os->triggerMap[o - 1 + os->width];
                            } else { triggerBlocksMerge(os, os->triggerMap[o - 1 + os->width], blockId); }
                        }
                        while (blockId && (os->triggerBlock_redirect[blockId] > 0))
                            blockId = os->triggerBlock_redirect[blockId];
                        if (blockId == 0) {
                            if (os->Nblocks < MAX_TRIGGER_BLOCKS - 1) os->Nblocks++;
                            blockId = os->Nblocks;
                            os->triggerBlock_N[blockId] = 0;
                            os->triggerBlock_sumx[blockId] = 0;
                            os->triggerBlock_sumy[blockId] = 0;
                            os->triggerBlock_suml[blockId] = 0;
                            os->triggerBlock_top[blockId] = y;
                            os->triggerBlock_bot[blockId] = y;
                            os->triggerBlock_redirect[blockId] = 0;
                        }

                        if (os->pastTriggerMap[o] < 2.3 * pastTriggerMapAverage) {
                            os->triggerBlock_N[blockId]++;
                            os->triggerBlock_top[blockId] = MIN(os->triggerBlock_top[blockId], y);
                            os->triggerBlock_bot[blockId] = MAX(os->triggerBlock_bot[blockId], y);
                            os->triggerBlock_sumx[blockId] += x;
                            os->triggerBlock_sumy[blockId] += y;
                            os->triggerBlock_suml[blockId] += image1[o] - image2[o];
                        }
                        os->triggerMap[o] = blockId;
                    }
                }
            }
        }
#pragma omp critical (trigger_cleanup)
        {
            pastTriggerMapAverageNew += triggerMap_linesum;
            nPixelsWithinMask += nPixelsWithinMask_linesum;
        }
    }

    // Loop over blocks of pixels which have brightened and see if any are large enough to be interesting
    int i;
    for (i = 1; i <= os->Nblocks; i++) {
        if (i == MAX_TRIGGER_BLOCKS - 1) break;
        if ((os->triggerBlock_suml[i] > threshold_intensity) &&
            (os->triggerBlock_N[i] > threshold_blockSize) &&
            (os->triggerBlock_bot[i] - os->triggerBlock_top[i] >= 2)
                ) {
            const int n = os->triggerBlock_N[i];
            const int x = (os->triggerBlock_sumx[i] / n); // average x position of moving object
            const int y = (os->triggerBlock_sumy[i] / n); // average y position of moving object
            const int l = os->triggerBlock_suml[i] / coAddedFrames; // total excess brightness
            output = 1; // We have triggered!
            registerTrigger(os, i, x, y, n, l, image1, image2, coAddedFrames);
        }
    }
    pastTriggerMapAverage = pastTriggerMapAverageNew / nPixelsWithinMask + 1;
    return output;
}

