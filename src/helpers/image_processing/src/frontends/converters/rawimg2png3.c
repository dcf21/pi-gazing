// rawimg2png3.c 
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
#include <unistd.h>

#include "argparse/argparse.h"
#include "png/image.h"
#include "utils/asciiDouble.h"
#include "utils/error.h"
#include "utils/skyClarity.h"
#include "png.h"
#include "settings.h"

static const char *const usage[] = {
    "rawimg2png3 [options] [[--] args]",
    "rawimg2png3 [options]",
    NULL,
};

int main(int argc, const char *argv[]) {
    int i;

    char rawFname[FNAME_LENGTH] = "\0";
    char fname[FNAME_LENGTH] = "\0";
    double noise = 0;

    struct argparse_option options[] = {
        OPT_HELP(),
        OPT_GROUP("Basic options"),
        OPT_STRING('i', "input", &rawFname, "input filename"),
        OPT_STRING('o', "output", &fname, "output filename"),
        OPT_FLOAT('n', "noise", &noise, "noise level"),
        OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
    "\nConvert raw image files into PNG format.",
    "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        gnom_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

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

    int code = 0;

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

        char frOut[FNAME_LENGTH];
        sprintf(frOut, "%s_%d.png", fname, i);

        code = image_put(frOut, out, 1);

        sprintf(frOut, "%s_%d.txt", fname, i);
        FILE *f = fopen(frOut, "w");
        if (f) {
            fprintf(f, "skyClarity %.2f\n", calculateSkyClarity(&out, noise));
            fclose(f);
        }
    }

    free(imgRawR);
    free(imgRawG);
    free(imgRawB);
    return code;
}

