// backgroundSub.c
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

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include "asciiDouble.h"
#include "error.h"
#include "gnomonic.h"
#include "image.h"
#include "settings.h"
#include "str_constants.h"

#define GRIDSIZE 8
#define FRACTION 0.99

void backgroundSubtract(image_ptr img, settingsIn *si) {
    int histogram[GRIDSIZE][GRIDSIZE][3][256];
    int mode[GRIDSIZE][GRIDSIZE][3];
    int i, j, k, l;

    if (si->backSub == 0) return;

    for (i = 0; i < GRIDSIZE; i++)
        for (j = 0; j < GRIDSIZE; j++)
            for (k = 0; k < 3; k++)
                for (l = 0; l < 256; l++)histogram[i][j][k][l] = 0;

    for (j = 0; j < img.ysize; j++) {
        int k;
        int l = img.xsize * j;
        int jbin = j * GRIDSIZE / img.ysize;
        for (k = 0; k < img.xsize; k++, l++) {
            int kbin = k * GRIDSIZE / img.xsize;
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

    for (i = 0; i < GRIDSIZE; i++)
        for (j = 0; j < GRIDSIZE; j++)
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

    for (j = 0; j < img.ysize; j++) {
        int k;
        int l = img.xsize * j;
        double jbin = j * ((double) GRIDSIZE) / img.ysize - 0.5;
        int jbin0 = (int) floor(jbin);
        double jbin0w = 1 - (jbin - jbin0);
        if (jbin0 < 0) {
            jbin0 = 0;
            jbin0w = 1;
        }
        int jbin1 = jbin0 + 1;
        if (jbin1 >= GRIDSIZE) jbin1 = GRIDSIZE - 1;
        double jbin1w = 1 - jbin0w;
        for (k = 0; k < img.xsize; k++, l++) {
            double kbin = k * ((double) GRIDSIZE) / img.xsize - 0.5;
            int kbin0 = (int) floor(kbin);
            double kbin0w = 1 - (kbin - kbin0);
            if (kbin0 < 0) {
                kbin0 = 0;
                kbin0w = 1;
            }
            int kbin1 = kbin0 + 1;
            if (kbin1 >= GRIDSIZE) kbin1 = GRIDSIZE - 1;
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

            if (si->backSub == 1) {
                if (img.data_red[l] > backr) img.data_red[l] -= backr; else img.data_red[l] = 0;
                if (img.data_grn[l] > backg) img.data_grn[l] -= backg; else img.data_grn[l] = 0;
                if (img.data_blu[l] > backb) img.data_blu[l] -= backb; else img.data_blu[l] = 0;
            } else if (si->backSub == 2) {
                img.data_red[l] = backr;
                img.data_grn[l] = backg;
                img.data_blu[l] = backb;
            }
        }
    }

    return;
}

