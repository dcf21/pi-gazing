// barrel.c
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

#include <gsl/gsl_errno.h>
#include <gsl/gsl_math.h>

#include "asciiDouble.h"
#include "error.h"
#include "gnomonic.h"
#include "imageProcess.h"
#include "image.h"
#include "readConfig.h"
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

int main(int argc, char **argv) {
    char help_string[LSTR_LENGTH], version_string[FNAME_LENGTH], version_string_underline[FNAME_LENGTH];
    char *filename[6];
    int i, haveFilename = 0;
    settings s_model, *feed_s = &s_model;
    settingsIn s_in_default;
    image_ptr outputImage;

    // Initialise sub-modules
    if (DEBUG) gnom_log("Initialising barrel-distortion correction tool.");
    defaultSettings(feed_s, &s_in_default);

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Make help and version strings
    sprintf(version_string, "Barrel Distortion Corrector %s", VERSION);

    sprintf(help_string, "Barrel Distortion Corrector %s\n\
%s\n\
\n\
Usage: barrel.bin <filename> <barrel_a> <barrel_b> <barrel_c> <output filename>\n\
  -h, --help:       Display this help.\n\
  -v, --version:    Display version number.", VERSION, strUnderline(version_string, version_string_underline));

    // Scan commandline options for any switches
    haveFilename = 0;
    for (i = 1; i < argc; i++) {
        if (strlen(argv[i]) == 0) continue;
        if ((strcmp(argv[i], "-v") == 0) || (strcmp(argv[i], "-version") == 0) || (strcmp(argv[i], "--version") == 0)) {
            gnom_report(version_string);
            return 0;
        } else if ((strcmp(argv[i], "-h") == 0) || (strcmp(argv[i], "-help") == 0) ||
                   (strcmp(argv[i], "--help") == 0)) {
            gnom_report(help_string);
            return 0;
        }
        if (haveFilename > 4) {
            sprintf(temp_err_string,
                    "barrel.bin should be provided with three barrel-distortion coefficients, and two filenames on the command line. Too many filenames appear to have been supplied. Type 'barrel.bin -help' for a list of available commandline options.");
            gnom_error(ERR_GENERAL, temp_err_string);
            return 1;
        }
        filename[haveFilename] = argv[i];
        haveFilename++;
        continue;
    }

    // Check that we have been provided with exactly one filename on the command line
    if (haveFilename < 5) {
        sprintf(temp_err_string,
                "barrel.bin should be provided with three barrel-distortion coefficients, and two filenames on the command line. Type 'barrel.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    // Read barrel-distortion coefficients
    {
        char *cp;
        cp = filename[1];
        if (!validFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read barrel_a");
        s_in_default.barrel_a = getFloat(cp, NULL);
        //sprintf(temp_err_string, "barrel_a = %f", s_in_default.barrel_a); gnom_report(temp_err_string);
        cp = filename[2];
        if (!validFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read barrel_b");
        s_in_default.barrel_b = getFloat(cp, NULL);
        //sprintf(temp_err_string, "barrel_b = %f", s_in_default.barrel_b); gnom_report(temp_err_string);
        cp = filename[3];
        if (!validFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read barrel_c");
        s_in_default.barrel_c = getFloat(cp, NULL);
        //sprintf(temp_err_string, "barrel_c = %f", s_in_default.barrel_c); gnom_report(temp_err_string);
    }


    {
        image_ptr InputImage;

        // Read image
        strcpy(s_in_default.InFName, filename[0]);
        InputImage = image_get(filename[0]);
        if (InputImage.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file");

        feed_s->mode = MODE_GNOMONIC;
        feed_s->XSize = InputImage.xsize;
        feed_s->YSize = InputImage.ysize;
        feed_s->YScale *= ((double) InputImage.ysize) /
                          InputImage.xsize; // Make sure that we treat image with correct aspect ratio
        strcpy(feed_s->OutFName, filename[4]);
        s_in_default.InXSize = InputImage.xsize;
        s_in_default.InYSize = InputImage.ysize;
        s_in_default.InYScale *= ((double) InputImage.ysize) / InputImage.xsize;

        // Malloc output image
        image_alloc(&outputImage, feed_s->XSize, feed_s->YSize);

        // Process image
        StackImage(InputImage, outputImage, NULL, NULL, feed_s, &s_in_default);

        // Free image
        image_dealloc(&InputImage);
    }

    // Write image
    image_deweight(&outputImage);
    image_put(feed_s->OutFName, outputImage);
    image_dealloc(&outputImage);

    if (DEBUG) gnom_log("Terminating normally.");
    return 0;
}

