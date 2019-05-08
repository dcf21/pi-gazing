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

#include "argparse/argparse.h"

#include "utils/asciiDouble.h"
#include "utils/error.h"
#include "gnomonic.h"
#include "imageProcess.h"
#include "png/image.h"
#include "readConfig.h"
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

static const char *const usage[] = {
        "stack [options] [[--] args]",
        "stack [options]",
        NULL,
};

#define IMAGES_MAX 1024

int main(int argc, const char **argv) {
    int i;
    settings s_model, *feed_s = &s_model;
    settingsIn s_in[IMAGES_MAX], s_in_default;
    int image_count = 0;
    image_ptr output_image;

    // Initialise sub-modules
    if (DEBUG) logging_info("Initialising stacker.");
    defaultSettings(feed_s, &s_in_default);

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Scan commandline options for any switches
    char config_filename[FNAME_LENGTH] = "\0";

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Scan commandline options for any switches
    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('c', "config", &config_filename, "configuration file with list of images to stack"),
            OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
                      "\nStack the contents of many PNG files together.",
                      "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    // Go through command script line by line
    if (readConfig(config_filename, feed_s, s_in, &s_in_default, &image_count)) return 1;

    // Malloc output image
    image_alloc(&output_image, feed_s->XSize, feed_s->YSize);

    // Straightforward stacking (no cloud masking)
    for (i = 0; i < image_count; i++) {
        image_ptr input_image;

        // Read image
        input_image = image_get(s_in[i].InFName);
        if (input_image.data_red == NULL) logging_fatal(__FILE__, __LINE__, "Could not read input image file");
        if (feed_s->cloudMask == 0)
            backgroundSubtract(input_image, s_in + i); // Do not do background subtraction if we're doing cloud masking

        // Process image
        StackImage(input_image, output_image, NULL, NULL, feed_s, s_in + i);

        // Free image
        image_dealloc(&input_image);
    }

    image_deweight(&output_image);

    // If requested, do stacking again with cloud masking
    if (feed_s->cloudMask != 0) {
        image_ptr cloud_mask_average = output_image;
        image_alloc(&output_image, feed_s->XSize, feed_s->YSize);

        // Stacking with mask
        for (i = 0; i < image_count; i++) {
            image_ptr input_image, cloud_mask;

            // Read image
            input_image = image_get(s_in[i].InFName);
            if (input_image.data_red == NULL) logging_fatal(__FILE__, __LINE__, "Could not read input image file");
            image_cp(&input_image, &cloud_mask);
            backgroundSubtract(input_image, s_in + i);

            // Process image
            StackImage(input_image, output_image, &cloud_mask_average, &cloud_mask, feed_s, s_in + i);

            // Free image
            image_dealloc(&input_image);
            image_dealloc(&cloud_mask);
        }

        image_deweight(&output_image);
        image_dealloc(&cloud_mask_average);
    }

    // Write image
    image_put(feed_s->OutFName, output_image, 0);
    image_dealloc(&output_image);

    if (DEBUG) logging_info("Terminating normally.");
    return 0;
}
