// multiply.c
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
    char *filename[3];
    int i, haveFilename = 0;
    settingsIn s_in_default;
    image_ptr outputImage;

    // Initialise sub-modules
    if (DEBUG) gnom_log("Initialising image multiplier.");

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Make help and version strings
    sprintf(version_string, "Image Pixel Value Multiplier %s", VERSION);

    sprintf(help_string, "Image Pixel Value Multiplier %s\n\
%s\n\
\n\
Usage: multiply.bin <filename1> <factor> <output filename>\n\
  -h, --help:       Display this help.\n\
  -v, --version:    Display version number.", VERSION, strUnderline(version_string, version_string_underline));

    // Scan commandline options for any switches
    haveFilename = 0;
    for (i = 1; i < argc; i++) {
        if (strlen(argv[i]) == 0) continue;
        if (argv[i][0] != '-') {
            if (haveFilename > 2) {
                sprintf(temp_err_string,
                        "multiply.bin should be called with the following commandline syntax:\n\nmultiply.bin <filename1> <factor> <output filename>\n\nToo many filenames appear to have been supplied. Type 'multiply.bin -help' for a list of available commandline options.");
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
                    "Received switch '%s' which was not recognised.\nType 'multiply.bin -help' for a list of available commandline options.",
                    argv[i]);
            gnom_error(ERR_GENERAL, temp_err_string);
            return 1;
        }
    }

    // Check that we have been provided with exactly one filename on the command line
    if (haveFilename < 3) {
        sprintf(temp_err_string,
                "multiply.bin should be called with the following commandline syntax:\n\nmultiply.bin <filename1> <factor> <output filename>\n\nToo few filenames appear to have been supplied. Type 'multiply.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    {
        image_ptr InputImage;

        // Read image
        strcpy(s_in_default.InFName, filename[0]);
        InputImage = image_get(filename[0]);
        if (InputImage.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file 1");

        double factor = getFloat(filename[1], NULL);

        // Malloc output image
        image_alloc(&outputImage, InputImage.xsize, InputImage.ysize);

        // Process image
#define CLIPCHAR(color) (unsigned char)(((color)>0xFF)?0xff:(((color)<0)?0:(color)))
        for (i = 0; i < InputImage.xsize * InputImage.ysize; i++)
            outputImage.data_red[i] = CLIPCHAR(InputImage.data_red[i] * factor);
        for (i = 0; i < InputImage.xsize * InputImage.ysize; i++)
            outputImage.data_grn[i] = CLIPCHAR(InputImage.data_grn[i] * factor);
        for (i = 0; i < InputImage.xsize * InputImage.ysize; i++)
            outputImage.data_blu[i] = CLIPCHAR(InputImage.data_blu[i] * factor);

        // Free image
        image_dealloc(&InputImage);
    }

    // Write image
    image_put(filename[2], outputImage);
    image_dealloc(&outputImage);

    if (DEBUG) gnom_log("Terminating normally.");
    return 0;
}

