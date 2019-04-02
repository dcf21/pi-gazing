// stack.c
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

#define IMAGES_MAX 1024

int main(int argc, char **argv) {
    char help_string[LSTR_LENGTH], version_string[FNAME_LENGTH], version_string_underline[FNAME_LENGTH];
    char *filename = NULL;
    int i, haveFilename = 0;
    settings s_model, *feed_s = &s_model;
    settingsIn s_in[IMAGES_MAX], s_in_default;
    int nImages = 0;
    image_ptr outputImage;

    // Initialise sub-modules
    if (DEBUG) gnom_log("Initialising stacker.");
    defaultSettings(feed_s, &s_in_default);

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Make help and version strings
    sprintf(version_string, "Stacker %s", VERSION);

    sprintf(help_string, "Stacker %s\n\
%s\n\
\n\
Usage: stack.bin <filename>\n\
  -h, --help:       Display this help.\n\
  -v, --version:    Display version number.", VERSION, strUnderline(version_string, version_string_underline));

    // Scan commandline options for any switches
    haveFilename = 0;
    for (i = 1; i < argc; i++) {
        if (strlen(argv[i]) == 0) continue;
        if (argv[i][0] != '-') {
            haveFilename++;
            filename = argv[i];
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
                    "Received switch '%s' which was not recognised.\nType 'stack.bin -help' for a list of available commandline options.",
                    argv[i]);
            gnom_error(ERR_GENERAL, temp_err_string);
            return 1;
        }
    }

    // Check that we have been provided with exactly one filename on the command line
    if (haveFilename < 1) {
        sprintf(temp_err_string,
                "stack.bin should be provided with a filename on the command line to act upon. Type 'stack.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    } else if (haveFilename > 1) {
        sprintf(temp_err_string,
                "stack.bin should be provided with only one filename on the command line to act upon. Multiple filenames appear to have been supplied. Type 'stack.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    // Go through command script line by line
    if (readConfig(filename, feed_s, s_in, &s_in_default, &nImages)) return 1;

    // Malloc output image
    image_alloc(&outputImage, feed_s->XSize, feed_s->YSize);

    // Straightforward stacking (no cloud masking)
    for (i = 0; i < nImages; i++) {
        image_ptr InputImage;

        // Read image
        InputImage = image_get(s_in[i].InFName);
        if (InputImage.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file");
        if (feed_s->cloudMask == 0)
            backgroundSubtract(InputImage, s_in +
                                           i); // Do not do background subtraction if we're doing cloud masking

        // Process image
        StackImage(InputImage, outputImage, NULL, NULL, feed_s, s_in + i);

        // Free image
        image_dealloc(&InputImage);
    }

    image_deweight(&outputImage);

    // If requested, do stacking again with cloud masking
    if (feed_s->cloudMask != 0) {
        image_ptr CloudMaskAvg = outputImage;
        image_alloc(&outputImage, feed_s->XSize, feed_s->YSize);

        // Stacking with mask
        for (i = 0; i < nImages; i++) {
            image_ptr InputImage, CloudMaskThis;

            // Read image
            InputImage = image_get(s_in[i].InFName);
            if (InputImage.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file");
            image_cp(&InputImage, &CloudMaskThis);
            backgroundSubtract(InputImage, s_in + i);

            // Process image
            StackImage(InputImage, outputImage, &CloudMaskAvg, &CloudMaskThis, feed_s, s_in + i);

            // Free image
            image_dealloc(&InputImage);
            image_dealloc(&CloudMaskThis);
        }

        image_deweight(&outputImage);
        image_dealloc(&CloudMaskAvg);
    }

    // Write image
    image_put(feed_s->OutFName, outputImage);
    image_dealloc(&outputImage);

    if (DEBUG) gnom_log("Terminating normally.");
    return 0;
}

