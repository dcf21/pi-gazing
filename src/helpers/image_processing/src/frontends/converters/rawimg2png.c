// rawimg2png.c 
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
#include "utils/lensCorrect.h"
#include "utils/skyClarity.h"

#include "settings.h"

static const char *const usage[] = {
        "rawimg2png [options] [[--] args]",
        "rawimg2png [options]",
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
        sprintf(temp_err_string, "ERROR: Cannot open input raw image file <%s>.\n", input_filename);
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int width, height, channels, bit_width;
    i = fread(&width, sizeof(int), 1, infile);
    i = fread(&height, sizeof(int), 1, infile);
    i = fread(&channels, sizeof(int), 1, infile);
    i = fread(&bit_width, sizeof(int), 1, infile);

    const int frame_size = width * height;
    const int bytes_per_pixel = bit_width / 8;
    const double weight = (bytes_per_pixel > 1) ? 256 : 1;

    unsigned char *image_data_raw = malloc(channels * frame_size * bytes_per_pixel);

    if (image_data_raw == NULL) {
        sprintf(temp_err_string, "ERROR: malloc fail");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    i = fread(image_data_raw, 1, channels * frame_size * bytes_per_pixel, infile);

    fclose(infile);

    image_ptr output_image;
    image_alloc(&output_image, width, height);

    if (bytes_per_pixel == 1) {
        uint8_t *image_raw = (uint8_t *)image_data_raw;
        if (channels >= 3) {
            for (i = 0; i < frame_size; i++) output_image.data_red[i] = image_raw[i];
            for (i = 0; i < frame_size; i++) output_image.data_grn[i] = image_raw[i + frame_size];
            for (i = 0; i < frame_size; i++) output_image.data_blu[i] = image_raw[i + frame_size * 2];
            for (i = 0; i < frame_size; i++) output_image.data_w[i] = weight;
        } else {
            for (i = 0; i < frame_size; i++) output_image.data_red[i] = image_raw[i];
            for (i = 0; i < frame_size; i++) output_image.data_grn[i] = image_raw[i];
            for (i = 0; i < frame_size; i++) output_image.data_blu[i] = image_raw[i];
            for (i = 0; i < frame_size; i++) output_image.data_w[i] = weight;
        }
    } else {
        uint16_t *image_raw = (uint16_t *)image_data_raw;
        if (channels >= 3) {
            for (i = 0; i < frame_size; i++) output_image.data_red[i] = image_raw[i];
            for (i = 0; i < frame_size; i++) output_image.data_grn[i] = image_raw[i + frame_size];
            for (i = 0; i < frame_size; i++) output_image.data_blu[i] = image_raw[i + frame_size * 2];
            for (i = 0; i < frame_size; i++) output_image.data_w[i] = weight;
        } else {
            for (i = 0; i < frame_size; i++) output_image.data_red[i] = image_raw[i];
            for (i = 0; i < frame_size; i++) output_image.data_grn[i] = image_raw[i];
            for (i = 0; i < frame_size; i++) output_image.data_blu[i] = image_raw[i];
            for (i = 0; i < frame_size; i++) output_image.data_w[i] = weight;
        }
    }

    char product_filename[FNAME_LENGTH];
    sprintf(product_filename, "%s.png", output_filename);

    image_put(product_filename, output_image, (channels < 3));

    sprintf(product_filename, "%s.txt", output_filename);
    FILE *f = fopen(product_filename, "w");
    if (f) {
        fprintf(f, "skyClarity %.2f\n", calculate_sky_clarity(&output_image, noise_level));
        fclose(f);
    }

    image_dealloc(&output_image);
    free(image_data_raw);
    return 0;
}
