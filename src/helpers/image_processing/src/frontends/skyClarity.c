// skyClarity.c
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2021 Dominic Ford.

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
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "str_constants.h"
#include "argparse/argparse.h"
#include "png/image.h"
#include "utils/asciiDouble.h"
#include "utils/error.h"
#include "utils/skyClarity.h"

static const char *const usage[] = {
        "skyClarity [options] [[--] args]",
        "skyClarity [options]",
        NULL,
};

int main(int argc, const char *argv[]) {

    const char *input_filename = "\0";
    double noise_level = 0;

    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('i', "input", &input_filename, "input filename"),
            OPT_FLOAT('n', "noise", &noise_level, "noise level"),
            OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
                      "\nCalculate the sky clarity of a PNG image.",
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
    image_ptr input_image;
    input_image = image_get(input_filename);
    if (input_image.data_red == NULL) logging_fatal(__FILE__, __LINE__, "Could not read input image file");

    double sky_clarity = calculate_sky_clarity(&input_image, noise_level);
    printf("%f", sky_clarity);

    // Free image
    image_dealloc(&input_image);
    return 0;
}
