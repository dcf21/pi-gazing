// lensCorrect.c 
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

    const char *input_filename = "\0";
    const char *output_filename = "\0";
    double barrel_a = 0;
    double barrel_b = 0;
    double barrel_c = 0;

    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('i', "input", &input_filename, "input filename"),
            OPT_STRING('o', "output", &output_filename, "output filename"),
            OPT_FLOAT('a', "barrel-a", &barrel_a, "barrel correction coefficient a"),
            OPT_FLOAT('b', "barrel-b", &barrel_b, "barrel correction coefficient b"),
            OPT_FLOAT('c', "barrel-c", &barrel_c, "barrel correction coefficient c"),
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
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    // Read image
    image_ptr input_image;
    input_image = image_get(input_filename);
    if (input_image.data_red == NULL) logging_fatal(__FILE__, __LINE__, "Could not read input image file");

    char product_filename[FNAME_LENGTH];
    sprintf(product_filename, "%s.png", output_filename);

    image_ptr image_corrected = lens_correct(&input_image, barrel_a, barrel_b, barrel_c);
    image_put(product_filename, image_corrected, 0);
    image_dealloc(&image_corrected);

    image_dealloc(&input_image);
    return 0;
}
