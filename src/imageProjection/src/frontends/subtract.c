// subtract.c
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

#include "asciidouble.h"
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
    int i, HaveFilename = 0;
    settingsIn s_in_default;
    image_ptr OutputImage;

    // Initialise sub-modules
    if (DEBUG) gnom_log("Initialising image subtractor.");

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Make help and version strings
    sprintf(version_string, "Image Subtractor %s", VERSION);

    sprintf(help_string, "Image Subtractor %s\n\
%s\n\
\n\
Usage: subtract.bin <filename1> <filename2> <output filename>\n\
  -h, --help:       Display this help.\n\
  -v, --version:    Display version number.", VERSION, StrUnderline(version_string, version_string_underline));

    // Scan commandline options for any switches
    HaveFilename = 0;
    for (i = 1; i < argc; i++) {
        if (strlen(argv[i]) == 0) continue;
        if (argv[i][0] != '-') {
            if (HaveFilename > 2) {
                sprintf(temp_err_string,
                        "subtract.bin should be provided with three filenames on the command line to act upon. Too many filenames appear to have been supplied. Type 'subtract.bin -help' for a list of available commandline options.");
                gnom_error(ERR_GENERAL, temp_err_string);
                return 1;
            }
            filename[HaveFilename] = argv[i];
            HaveFilename++;
            continue;
        }
        if ((strcmp(argv[i], "-v") == 0) || (strcmp(argv[i], "-version") == 0) || (strcmp(argv[i], "--version") == 0)) {
            gnom_report(version_string);
            return 0;
        }
        else if ((strcmp(argv[i], "-h") == 0) || (strcmp(argv[i], "-help") == 0) || (strcmp(argv[i], "--help") == 0)) {
            gnom_report(help_string);
            return 0;
        }
        else {
            sprintf(temp_err_string,
                    "Received switch '%s' which was not recognised.\nType 'subtract.bin -help' for a list of available commandline options.",
                    argv[i]);
            gnom_error(ERR_GENERAL, temp_err_string);
            return 1;
        }
    }

    // Check that we have been provided with exactly one filename on the command line
    if (HaveFilename < 3) {
        sprintf(temp_err_string,
                "subtract.bin should be provided with three filenames on the command line to act upon. Type 'subtract.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    {
        image_ptr InputImage1, InputImage2;

        // Read image
        strcpy(s_in_default.InFName, filename[0]);
        InputImage1 = image_get(filename[0]);
        if (InputImage1.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file 1");

        strcpy(s_in_default.InFName, filename[1]);
        InputImage2 = image_get(filename[1]);
        if (InputImage2.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file 2");

        if (InputImage1.xsize != InputImage2.xsize)
            gnom_fatal(__FILE__, __LINE__, "Images must have the same dimensions");
        if (InputImage1.ysize != InputImage2.ysize)
            gnom_fatal(__FILE__, __LINE__, "Images must have the same dimensions");

        // Malloc output image
        image_alloc(&OutputImage, InputImage1.xsize, InputImage1.ysize);

        // Process image
#define CLIPCHAR(color) (unsigned char)(((color)>0xFF)?0xff:(((color)<0)?0:(color)))
        for (i = 0; i < InputImage1.xsize * InputImage1.ysize; i++)
            OutputImage.data_red[i] = CLIPCHAR(InputImage1.data_red[i] - InputImage2.data_red[i] + 2);
        for (i = 0; i < InputImage1.xsize * InputImage1.ysize; i++)
            OutputImage.data_grn[i] = CLIPCHAR(InputImage1.data_grn[i] - InputImage2.data_grn[i] + 2);
        for (i = 0; i < InputImage1.xsize * InputImage1.ysize; i++)
            OutputImage.data_blu[i] = CLIPCHAR(InputImage1.data_blu[i] - InputImage2.data_blu[i] + 2);

        // Free image
        image_dealloc(&InputImage1);
        image_dealloc(&InputImage2);
    }

    // Write image
    image_put(filename[2], OutputImage);
    image_dealloc(&OutputImage);

    if (DEBUG) gnom_log("Terminating normally.");
    return 0;
}

