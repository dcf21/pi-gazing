// resize.c
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

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
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

static const char *const usage[] = {
        "resize [options] [[--] args]",
        "resize [options]",
        NULL,
};

int main(int argc, const char **argv) {
    int i, j;
    settings_input s_in_default;
    image_ptr input_image;
    image_ptr output_image;

    // Initialise sub-modules
    if (DEBUG) logging_info("Initialising image resize tool.");

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Scan commandline options for any switches
    const char *input_filename = "\0";
    const char *output_filename = "\0";
    int new_width = 1;

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Scan commandline options for any switches
    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('i', "input", &input_filename, "input filename"),
            OPT_STRING('o', "output", &output_filename, "output filename"),
            OPT_INTEGER('w', "width", &new_width, "new width"),
            OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
                      "\nResize the contents of a PNG file to a new width.",
                      "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    // Read image
    strcpy(s_in_default.input_filename, input_filename);
    input_image = image_get(input_filename);
    if (input_image.data_red == NULL) logging_fatal(__FILE__, __LINE__, "Could not read input image file");

    double scaling = input_image.xsize / ((double) new_width);
    int new_height = (int)(input_image.ysize / scaling);

    // Malloc output image
    image_alloc(&output_image, new_width, new_height);

    // Process image
    for (j = 0; j < new_height; j++)
        for (i = 0; i < new_width; i++) {
            int x_in = (int)(i * scaling);
            int y_in = (int)(j * scaling);
            output_image.data_red[j * output_image.xsize + i] = input_image.data_red[y_in * input_image.xsize + x_in];
            output_image.data_grn[j * output_image.xsize + i] = input_image.data_grn[y_in * input_image.xsize + x_in];
            output_image.data_blu[j * output_image.xsize + i] = input_image.data_blu[y_in * input_image.xsize + x_in];
        }

    // Free image
    image_dealloc(&input_image);

    // Write image
    image_put(output_filename, output_image, 0);
    image_dealloc(&output_image);

    if (DEBUG) logging_info("Terminating normally.");
    return 0;
}
