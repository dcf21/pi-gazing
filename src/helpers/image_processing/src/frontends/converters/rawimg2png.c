// rawimg2png.c 
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

// Convert a raw image into PNG format.

// Due to the tight constraints on data processing when analysing video in real time, we dump images to disk in
// uncompressed format. This converter is called during the day time to convert the raw image data into a compressed
// PNG file.

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <unistd.h>

#include "argparse/argparse.h"
#include "png/image.h"
#include "utils/error.h"
#include "utils/skyClarity.h"

#include "settings.h"

static const char *const usage[] = {
        "rawimg2png [options] [[--] args]",
        "rawimg2png [options]",
        NULL,
};

//! Convert a raw image into PNG format.
//! Due to the tight constraints on data processing when analysing video in real time, we dump images to disk in
//! uncompressed format. This converter is called during the day time to convert the raw image data into a compressed
//! PNG file.
//! \param argc Command-line arguments
//! \param argv Command-line arguments
//! \return None

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
        for (int i = 0; i < argc; i++) {
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
    fread(&width, sizeof(int), 1, infile);
    fread(&height, sizeof(int), 1, infile);
    fread(&channels, sizeof(int), 1, infile);
    fread(&bit_width, sizeof(int), 1, infile);

    const int frame_size = width * height;
    const int bytes_per_pixel = bit_width / 8;
    const double weight = (bytes_per_pixel > 1) ? 1 : (1./256);

    unsigned char *image_data_raw = malloc(channels * frame_size * bytes_per_pixel);

    if (image_data_raw == NULL) {
        sprintf(temp_err_string, "ERROR: malloc fail");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    fread(image_data_raw, 1, channels * frame_size * bytes_per_pixel, infile);

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

    // Rescale all pixels to range 0-65535
    image_deweight(&output_image);

    // Remove superfluous noise bits
    const double noise_level_16bit = noise_level * 256;
    const int noise_level_log2 = (int)(log(noise_level_16bit) / log(2));

    int truncate_at = noise_level_log2 - 3;
    if (truncate_at < 0) truncate_at = 0;
    if (truncate_at > 15) truncate_at = 15;

    const int inverse_mask = (1 << truncate_at) - 1;
    const int mask = (1 << 16) - 1 - inverse_mask;

    for (i = 0; i < frame_size; i++) {
        output_image.data_red[i] = ((unsigned int)output_image.data_red[i]) & mask;
        output_image.data_grn[i] = ((unsigned int)output_image.data_grn[i]) & mask;
        output_image.data_blu[i] = ((unsigned int)output_image.data_blu[i]) & mask;
    }

    // Write PNG file to disk
    image_put(product_filename, output_image, (channels < 3));

    // Add metadata about the sky clarity of this image
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
