// resize.c
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
    char *filename[3];
    int i, j, haveFilename = 0;
    settingsIn s_in_default;
    image_ptr outputImage;

    // Initialise sub-modules
    if (DEBUG) gnom_log("Initialising image resizer.");

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Make help and version strings
    sprintf(version_string, "Image Resizer %s", VERSION);

    sprintf(help_string, "Image Resizer %s\n\
%s\n\
\n\
Usage: resize.bin <filename1> <new width> <output filename>\n\
  -h, --help:       Display this help.\n\
  -v, --version:    Display version number.", VERSION, strUnderline(version_string, version_string_underline));

    // Scan commandline options for any switches
    haveFilename = 0;
    for (i = 1; i < argc; i++) {
        if (strlen(argv[i]) == 0) continue;
        if (argv[i][0] != '-') {
            if (haveFilename > 2) {
                sprintf(temp_err_string,
                        "resize.bin should be called with the following commandline syntax:\n\nresize.bin <filename1> <new width> <output filename>\n\nToo many filenames appear to have been supplied. Type 'resize.bin -help' for a list of available commandline options.");
                gnom_error(ERR_GENERAL, temp_err_string);
                return 1;
            }
            filename[haveFilename] = argv[i];
            haveFilename++;
            continue;
        }
        if ((strcmp(argv[i], "-v") == 0) || (strcmp(argv[i], "-version") == 0) || (strcmp(argv[i], "--version") == 0)) {
            gnom_report(version_string);
            return 0;
        } else if ((strcmp(argv[i], "-h") == 0) || (strcmp(argv[i], "-help") == 0) ||
                   (strcmp(argv[i], "--help") == 0)) {
            gnom_report(help_string);
            return 0;
        } else {
            sprintf(temp_err_string,
                    "Received switch '%s' which was not recognised.\nType 'resize.bin -help' for a list of available commandline options.",
                    argv[i]);
            gnom_error(ERR_GENERAL, temp_err_string);
            return 1;
        }
    }

    // Check that we have been provided with exactly one filename on the command line
    if (haveFilename < 3) {
        sprintf(temp_err_string,
                "resize.bin should be called with the following commandline syntax:\n\nresize.bin <filename1> <new width> <output filename>\n\nToo few filenames appear to have been supplied. Type 'resize.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    {
        image_ptr InputImage;

        // Read image
        strcpy(s_in_default.InFName, filename[0]);
        InputImage = image_get(filename[0]);
        if (InputImage.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file 1");

        int new_width = (int) getFloat(filename[1], NULL);
        double scaling = InputImage.xsize / ((double)new_width);
        int new_height = InputImage.ysize / scaling;

        // Malloc output image
        image_alloc(&outputImage, new_width, new_height);

        // Process image
        for (j = 0; j < new_height; j++)
            for (i = 0; i < new_width; i++) {
                int x_in = i * scaling;
                int y_in = j * scaling;
                outputImage.data_red[j * outputImage.xsize + i] = InputImage.data_red[y_in * InputImage.xsize + x_in];
                outputImage.data_grn[j * outputImage.xsize + i] = InputImage.data_grn[y_in * InputImage.xsize + x_in];
                outputImage.data_blu[j * outputImage.xsize + i] = InputImage.data_blu[y_in * InputImage.xsize + x_in];
            }

        // Free image
        image_dealloc(&InputImage);
    }

    // Write image
    image_put(filename[2], outputImage);
    image_dealloc(&outputImage);

    if (DEBUG) gnom_log("Terminating normally.");
    return 0;
}

