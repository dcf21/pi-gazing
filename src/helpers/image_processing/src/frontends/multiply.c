// multiply.c
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
        "multiply [options] [[--] args]",
        "multiply [options]",
        NULL,
};

int main(int argc, const char **argv) {
    int i;
    settings_input s_in_default;
    image_ptr input_image;
    image_ptr output_image;

    const char *input_filename = "\0";
    const char *output_filename = "\0";
    double multiplication_factor = 1;

    // Initialise sub-modules
    if (DEBUG) logging_info("Initialising image multiply tool.");

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Scan commandline options for any switches
    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('i', "input", &input_filename, "input filename"),
            OPT_STRING('o', "output", &output_filename, "output filename"),
            OPT_FLOAT('m', "multiply", &multiplication_factor, "multiplication factor"),
            OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
                      "\nMultiply the contents of a PNG file by a fixed factor.",
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
    if (input_image.data_red == NULL) logging_fatal(__FILE__, __LINE__, "Could not read input image file 1");

    // Malloc output image
    image_alloc(&output_image, input_image.xsize, input_image.ysize);

    // Process image
#define CLIPCHAR(color) (unsigned char)(((color)>0xFF)?0xff:(((color)<0)?0:(color)))
    for (i = 0; i < input_image.xsize * input_image.ysize; i++)
        output_image.data_red[i] = CLIPCHAR(input_image.data_red[i] * multiplication_factor);
    for (i = 0; i < input_image.xsize * input_image.ysize; i++)
        output_image.data_grn[i] = CLIPCHAR(input_image.data_grn[i] * multiplication_factor);
    for (i = 0; i < input_image.xsize * input_image.ysize; i++)
        output_image.data_blu[i] = CLIPCHAR(input_image.data_blu[i] * multiplication_factor);

    // Free image
    image_dealloc(&input_image);

    // Write image
    image_put(output_filename, output_image, 0);
    image_dealloc(&output_image);

    if (DEBUG) logging_info("Terminating normally.");
    return 0;
}
