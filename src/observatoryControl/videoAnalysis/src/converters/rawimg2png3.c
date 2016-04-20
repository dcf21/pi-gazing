// rawimg2png3.c 
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
#include "png.h"
#include "settings.h"

int main(int argc, char *argv[]) {
    int i;

    if (argc != 8) {
        sprintf(temp_err_string,
                "ERROR: Need to specify raw image filename on commandline, followed by output frame filename, e.g. 'rawimg2png3 foo.raw frame.png produceFilesWithoutLensCorrection noiseLevel barrelA barrelB barrelC'.");
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
    if (channels != 3) {
        sprintf(temp_err_string, "ERROR: cannot generate separate RGB PNGs from a mono PNG.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    const int frameSize = width * height;
    unsigned char *imgRawR = malloc(frameSize);
    unsigned char *imgRawG = malloc(frameSize);
    unsigned char *imgRawB = malloc(frameSize);
    if ((imgRawR == NULL) || (imgRawG == NULL) || (imgRawB == NULL)) {
        sprintf(temp_err_string, "ERROR: malloc fail");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }
    i = fread(imgRawR, 1, frameSize, infile);
    i = fread(imgRawG, 1, frameSize, infile);
    i = fread(imgRawB, 1, frameSize, infile);
    fclose(infile);

    image_ptr out;
    image_alloc(&out, width, height);

    int lc, code = 0;

    for (lc = lcmin; lc < 2; lc++) {
        for (i = 0; i < 3; i++) {
            int j;
            if (code) break;

            unsigned char *imgRaw = NULL;
            if (i == 0) imgRaw = imgRawR;
            else if (i == 1) imgRaw = imgRawG;
            else imgRaw = imgRawB;

            for (j = 0; j < frameSize; j++) out.data_red[j] = imgRaw[j];
            for (j = 0; j < frameSize; j++) out.data_grn[j] = imgRaw[j];
            for (j = 0; j < frameSize; j++) out.data_blu[j] = imgRaw[j];

            char frOut[FNAME_BUFFER];
            sprintf(frOut, "%s_LC%d_%d.png", fname, lc, i);

            if (lc) {
                image_ptr CorrectedImage = lensCorrect(&out, barrelA, barrelB, barrelC);
                code = image_put(frOut, CorrectedImage, 1);
                image_dealloc(&CorrectedImage);
            }
            else {
                code = image_put(frOut, out, 1);
            }

            sprintf(frOut, "%s_LC%d_%d.txt", fname, lc, i);
            FILE *f = fopen(frOut, "w");
            if (f) {
                fprintf(f, "skyClarity %.2f\n", calculateSkyClarity(&out, noise));
                fclose(f);
            }
        }
    }

    free(imgRawR);
    free(imgRawG);
    free(imgRawB);
    return code;
}

