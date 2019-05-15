// rawimg2png3.c 
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

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>

#include "argparse/argparse.h"
#include "png/image.h"
#include "utils/asciiDouble.h"
#include "utils/error.h"
#include "utils/skyClarity.h"
#include "png.h"
#include "settings.h"

static const char *const usage[] = {
        "rawimg2png3 [options] [[--] args]",
        "rawimg2png3 [options]",
        NULL,
};

int main(int argc, const char *argv[]) {
    int i;

    const char *input_filename = "\0";
    const char *output_filename = "\0";
    double noise_level = 0;

    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('i', "input", &input_filename, "input filename"),
            OPT_STRING('o', "output", &output_filename, "output filename"),
            OPT_FLOAT('n', "noise", &noise_level, "noise level"),
            OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
                      "\nConvert raw image files into PNG format.",
                      "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    FILE *infile;
    if ((infile = fopen(input_filename, "rb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output raw image file %s.\n", input_filename);
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int width, height, channels, bit_width;
    i = fread(&width, sizeof(int), 1, infile);
    i = fread(&height, sizeof(int), 1, infile);
    i = fread(&channels, sizeof(int), 1, infile);
    i = fread(&bit_width, sizeof(int), 1, infile);

    if (channels != 3) {
        sprintf(temp_err_string, "ERROR: cannot generate separate RGB PNGs from a mono PNG.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    const int frame_size = width * height;
    const int bytes_per_pixel = bit_width / 8;
    const double weight = (bytes_per_pixel > 1) ? 256 : 1;

    unsigned char *img_raw_r = malloc(frame_size * bytes_per_pixel);
    unsigned char *img_raw_g = malloc(frame_size * bytes_per_pixel);
    unsigned char *img_raw_b = malloc(frame_size * bytes_per_pixel);

    if ((img_raw_r == NULL) || (img_raw_g == NULL) || (img_raw_b == NULL)) {
        sprintf(temp_err_string, "ERROR: malloc fail");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    i = fread(img_raw_r, 1, frame_size * bytes_per_pixel, infile);
    i = fread(img_raw_g, 1, frame_size * bytes_per_pixel, infile);
    i = fread(img_raw_b, 1, frame_size * bytes_per_pixel, infile);

    fclose(infile);

    image_ptr out;
    image_alloc(&out, width, height);

    int code = 0;

    for (i = 0; i < 3; i++) {
        int j;
        if (code) break;

        unsigned char *img_raw_data = NULL;
        if (i == 0) img_raw_data = img_raw_r;
        else if (i == 1) img_raw_data = img_raw_g;
        else img_raw_data = img_raw_b;


        if (bytes_per_pixel == 1) {
            uint8_t *image_raw = (uint8_t *)img_raw_data;

            for (j = 0; j < frame_size; j++) out.data_red[j] = image_raw[j];
            for (j = 0; j < frame_size; j++) out.data_grn[j] = image_raw[j];
            for (j = 0; j < frame_size; j++) out.data_blu[j] = image_raw[j];
            for (i = 0; i < frame_size; i++) out.data_w[i] = weight;
        } else {
            uint16_t *image_raw = (uint16_t *)img_raw_data;

            for (j = 0; j < frame_size; j++) out.data_red[j] = image_raw[j];
            for (j = 0; j < frame_size; j++) out.data_grn[j] = image_raw[j];
            for (j = 0; j < frame_size; j++) out.data_blu[j] = image_raw[j];
            for (i = 0; i < frame_size; i++) out.data_w[i] = weight;
        }

        char product_filename[FNAME_LENGTH];
        sprintf(product_filename, "%s_%d.png", output_filename, i);

        code = image_put(product_filename, out, 1);

        sprintf(product_filename, "%s_%d.txt", output_filename, i);
        FILE *f = fopen(product_filename, "w");
        if (f) {
            fprintf(f, "skyClarity %.2f\n", calculate_sky_clarity(&out, noise_level));
            fclose(f);
        }
    }

    free(img_raw_r);
    free(img_raw_g);
    free(img_raw_b);
    return code;
}

