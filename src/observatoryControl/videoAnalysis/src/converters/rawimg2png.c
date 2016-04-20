// rawimg2png.c 
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
#include <unistd.h>
#include "utils/tools.h"
#include "png/image.h"
#include "utils/asciidouble.h"
#include "utils/error.h"
#include "utils/lensCorrect.h"
#include "utils/tools.h"

#include "settings.h"

int main(int argc, char *argv[]) {
    int i;

    if (argc != 8) {
        sprintf(temp_err_string,
                "ERROR: Need to specify raw image filename on commandline, followed by output frame filename, e.g. 'rawimg2png foo.raw frame.png produceFilesWithoutLensCorrection noiseLevel barrelA barrelB barrelC'.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    char *rawFname = argv[1];
    char *fname = argv[2];
    int lcmin = GetFloat(argv[3], NULL) ? 0 : 1;
    double noise = GetFloat(argv[4], NULL);
    double barrelA = GetFloat(argv[5], NULL);
    double barrelB = GetFloat(argv[6], NULL);
    double barrelC = GetFloat(argv[7], NULL);

    FILE *infile;
    if ((infile = fopen(rawFname, "rb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output raw image file %s.\n", rawFname);
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int width, height, channels;
    i = fread(&width, sizeof(int), 1, infile);
    i = fread(&height, sizeof(int), 1, infile);
    i = fread(&channels, sizeof(int), 1, infile);

    const int frameSize = width * height;
    unsigned char *imgRaw = malloc(channels * frameSize);
    if (imgRaw == NULL) {
        sprintf(temp_err_string, "ERROR: malloc fail");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }
    i = fread(imgRaw, 1, channels * frameSize, infile);
    fclose(infile);

    image_ptr OutputImage;
    image_alloc(&OutputImage, width, height);
    OutputImage.data_w = 1;

    if (channels >= 3) {
        for (i = 0; i < frameSize; i++) OutputImage.data_red[i] = imgRaw[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_grn[i] = imgRaw[i + frameSize];
        for (i = 0; i < frameSize; i++) OutputImage.data_blu[i] = imgRaw[i + frameSize * 2];
    } else {
        for (i = 0; i < frameSize; i++) OutputImage.data_red[i] = imgRaw[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_grn[i] = imgRaw[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_blu[i] = imgRaw[i];
    }

    int lc;
    for (lc = lcmin; lc < 2; lc++) {
        char frOut[FNAME_BUFFER];
        sprintf(frOut, "%s_LC%d.png", fname, lc);

        if (lc) {
            image_ptr CorrectedImage = lensCorrect(&OutputImage, barrelA, barrelB, barrelC);
            image_put(frOut, CorrectedImage, (channels < 3));
            image_dealloc(&CorrectedImage);
        }
        else {
            image_put(frOut, OutputImage, (channels < 3));
        }

        sprintf(frOut, "%s_LC%d.txt", fname, lc);
        FILE *f = fopen(frOut, "w");
        if (f) {
            fprintf(f, "skyClarity %.2f\n", calculateSkyClarity(&OutputImage, noise));
            fclose(f);
        }
    }

    image_dealloc(&OutputImage);
    free(imgRaw);
    return 0;
}

