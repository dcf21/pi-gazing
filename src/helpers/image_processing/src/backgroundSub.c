// backgroundSub.c
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

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include "utils/asciiDouble.h"
#include "error.h"
#include "gnomonic.h"
#include "png/image.h"
#include "settings.h"
#include "str_constants.h"

#define GRID_SIZE 8
#define FRACTION 0.99

//! background_subtract - A simple tool for subtracting the sky background from an image, in place. The sky background
//! is estimated as the mode sky brightness in each of a grid of 8x8 cells covering the image. Pi gazing itself uses
//! a more sophisticated background subtraction algorithm which estimates the time-integrated average brightness of
//! individual pixels.
//! \param img - The image to operate upon
//! \param si - Pi gazing settings

void background_subtract(image_ptr img, settings_input *si) {
    int histogram[GRID_SIZE][GRID_SIZE][3][256];
    int mode[GRID_SIZE][GRID_SIZE][3];
    int i, j, k, l;

    // If the background subtraction setting is set to zero, do nothing
    if (si->background_subtract == 0) return;

    // Zero the histograms we compute of the brightness within each pixel in each cell
    for (i = 0; i < GRID_SIZE; i++)
        for (j = 0; j < GRID_SIZE; j++)
            for (k = 0; k < 3; k++)
                for (l = 0; l < 256; l++)histogram[i][j][k][l] = 0;

    // Populate histograms of the pixel brightnesses within each cell
    for (j = 0; j < img.ysize; j++) {
        int k;
        int l = img.xsize * j;
        int jbin = j * GRID_SIZE / img.ysize;
        for (k = 0; k < img.xsize; k++, l++) {
            int kbin = k * GRID_SIZE / img.xsize;
            int level;
            level = (int) img.data_red[l];
            if (level < 0) level = 0;
            if (level > 255) level = 255;
            histogram[jbin][kbin][0][level]++;
            level = (int) img.data_grn[l];
            if (level < 0) level = 0;
            if (level > 255) level = 255;
            histogram[jbin][kbin][1][level]++;
            level = (int) img.data_blu[l];
            if (level < 0) level = 0;
            if (level > 255) level = 255;
            histogram[jbin][kbin][2][level]++;
        }
    }

    // Work out the most common sky brightness within each cell
    for (i = 0; i < GRID_SIZE; i++)
        for (j = 0; j < GRID_SIZE; j++)
            for (k = 0; k < 3; k++) {
                int mostPopular = 0;
                int mostVotes = 0;
                for (l = 0; l < 256; l++) {
                    if (histogram[i][j][k][l] > mostVotes) {
                        mostVotes = histogram[i][j][k][l];
                        mostPopular = l;
                    }
                }
                mode[i][j][k] = mostPopular;
            }

    // Linearly interpolate the 8x8 pixel map we have of the sky background
    for (j = 0; j < img.ysize; j++) {
        int k;
        int l = img.xsize * j;
        double jbin = j * ((double) GRID_SIZE) / img.ysize - 0.5;
        int jbin0 = (int) floor(jbin);
        double jbin0w = 1 - (jbin - jbin0);
        if (jbin0 < 0) {
            jbin0 = 0;
            jbin0w = 1;
        }
        int jbin1 = jbin0 + 1;
        if (jbin1 >= GRID_SIZE) jbin1 = GRID_SIZE - 1;
        double jbin1w = 1 - jbin0w;
        for (k = 0; k < img.xsize; k++, l++) {
            double kbin = k * ((double) GRID_SIZE) / img.xsize - 0.5;
            int kbin0 = (int) floor(kbin);
            double kbin0w = 1 - (kbin - kbin0);
            if (kbin0 < 0) {
                kbin0 = 0;
                kbin0w = 1;
            }
            int kbin1 = kbin0 + 1;
            if (kbin1 >= GRID_SIZE) kbin1 = GRID_SIZE - 1;
            double kbin1w = 1 - kbin0w;

            double backr = FRACTION *
                           (mode[jbin0][kbin0][0] * jbin0w * kbin0w + mode[jbin0][kbin1][0] * jbin0w * kbin1w +
                            mode[jbin1][kbin0][0] * jbin1w * kbin0w + mode[jbin1][kbin1][0] * jbin1w * kbin1w);
            double backg = FRACTION *
                           (mode[jbin0][kbin0][1] * jbin0w * kbin0w + mode[jbin0][kbin1][1] * jbin0w * kbin1w +
                            mode[jbin1][kbin0][1] * jbin1w * kbin0w + mode[jbin1][kbin1][1] * jbin1w * kbin1w);
            double backb = FRACTION *
                           (mode[jbin0][kbin0][2] * jbin0w * kbin0w + mode[jbin0][kbin1][2] * jbin0w * kbin1w +
                            mode[jbin1][kbin0][2] * jbin1w * kbin0w + mode[jbin1][kbin1][2] * jbin1w * kbin1w);

            // If the setting <background_subtract> is 1, then subtract the sky background
            if (si->background_subtract == 1) {
                if (img.data_red[l] > backr) img.data_red[l] -= backr; else img.data_red[l] = 0;
                if (img.data_grn[l] > backg) img.data_grn[l] -= backg; else img.data_grn[l] = 0;
                if (img.data_blu[l] > backb) img.data_blu[l] -= backb; else img.data_blu[l] = 0;

            // If the setting <background_subtract> is 2, then we return the sky background model
            } else if (si->background_subtract == 2) {
                img.data_red[l] = backr;
                img.data_grn[l] = backg;
                img.data_blu[l] = backb;
            }
        }
    }
}
