// lensCorrect.c 
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
#include "utils/error.h"
#include "utils/lensCorrect.h"

#include "settings.h"

static const char *const usage[] = {
    "lensCorrect [options] [[--] args]",
    "lensCorrect [options]",
    NULL,
};

int main(int argc, const char *argv[]) {
    int i;

    char rawFname[FNAME_LENGTH] = "\0";
    char fname[FNAME_LENGTH] = "\0";
    double barrelA = 0;
    double barrelB = 0;
    double barrelC = 0;

    struct argparse_option options[] = {
        OPT_HELP(),
        OPT_GROUP("Basic options"),
        OPT_STRING('i', "input", &rawFname, "input filename"),
        OPT_STRING('o', "output", &fname, "output filename"),
        OPT_FLOAT('a', "barrel-a", &barrelA, "barrel correction coefficient a"),
        OPT_FLOAT('b', "barrel-b", &barrelB, "barrel correction coefficient b"),
        OPT_FLOAT('c', "barrel-c", &barrelC, "barrel correction coefficient c"),
        OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
    "\nApply barrel correction to a PNG image.",
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
        sprintf(temp_err_string, "ERROR: Cannot open input image file <%s>.\n", rawFname);
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

    if (channels >= 3) {
        for (i = 0; i < frameSize; i++) OutputImage.data_red[i] = imgRaw[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_grn[i] = imgRaw[i + frameSize];
        for (i = 0; i < frameSize; i++) OutputImage.data_blu[i] = imgRaw[i + frameSize * 2];
        for (i = 0; i < frameSize; i++) OutputImage.data_w[i] = 1;
    } else {
        for (i = 0; i < frameSize; i++) OutputImage.data_red[i] = imgRaw[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_grn[i] = imgRaw[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_blu[i] = imgRaw[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_w[i] = 1;
    }

    char frOut[FNAME_LENGTH];
    sprintf(frOut, "%s.png", fname);

    image_ptr CorrectedImage = lensCorrect(&OutputImage, barrelA, barrelB, barrelC);
        image_put(frOut, CorrectedImage, (channels < 3));
        image_dealloc(&CorrectedImage);

    image_dealloc(&OutputImage);
    free(imgRaw);
    return 0;
}

