// image_out.c
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

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <zlib.h>

#include "png/image.h"
#include <png.h>
#include "str_constants.h"

//! image_put - Save an image from an image_ptr to a 16-bit PNG file
//! \param [in] output_filename The filename of the PNG file we are to write
//! \param [in] image The image_ptr structure containing the pixel data that we are to write
//! \param [in] grayscale Boolean flag indicating whether this image is greyscale (true) or full RGB (false)
//! \return Zero on success

int image_put(const char *output_filename, image_ptr image, int grayscale) {
    int code = 0;

    const int width = image.xsize;
    const int height = image.ysize;

    FILE *fp;
    png_structp png_ptr = NULL;
    png_infop info_ptr = NULL;
    png_bytep row = NULL;

    // Open file for writing (binary mode)
    fp = fopen(output_filename, "wb");
    if (fp == NULL) {
        fprintf(stderr, "Could not open file %s for writing\n", output_filename);
        code = 1;
        goto finalise;
    }

    // Initialize write structure
    png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    if (png_ptr == NULL) {
        fprintf(stderr, "Could not allocate write struct\n");
        code = 1;
        goto finalise;
    }

    // Initialize info structure
    info_ptr = png_create_info_struct(png_ptr);
    if (info_ptr == NULL) {
        fprintf(stderr, "Could not allocate info struct\n");
        code = 1;
        goto finalise;
    }

    // Setup Exception handling
    if (setjmp(png_jmpbuf(png_ptr))) {
        fprintf(stderr, "Error during png creation\n");
        code = 1;
        goto finalise;
    }

    png_init_io(png_ptr, fp);

    // Write header (16 bit colour depth)
    png_set_compression_level(png_ptr, Z_BEST_COMPRESSION);
    png_set_IHDR(png_ptr, info_ptr, width, height,
                 16, grayscale ? PNG_COLOR_TYPE_GRAY : PNG_COLOR_TYPE_RGB, PNG_INTERLACE_NONE,
                 PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);

    // Set title
    char title_buffer[FNAME_LENGTH];
    strcpy(title_buffer, output_filename);
    png_text title_text;
    title_text.compression = PNG_TEXT_COMPRESSION_NONE;
    title_text.key = "Title";
    title_text.text = title_buffer;
    png_set_text(png_ptr, info_ptr, &title_text, 1);

    png_write_info(png_ptr, info_ptr);

    // Allocate memory for one row (6 bytes per pixel - RGB)
    row = (png_bytep) malloc(6 * width * sizeof(png_byte));

    // Write image data
    int x, y;
    int p = 0;
    for (y = 0; y < height; y++) {
        for (x = 0; x < width; x++) {
            if (grayscale) {
                png_save_uint_16(&row[x * 2], (unsigned int) image.data_red[p]);
            } else {
                png_save_uint_16(&row[x * 6 + 0], (unsigned int) image.data_red[p]);
                png_save_uint_16(&row[x * 6 + 2], (unsigned int) image.data_grn[p]);
                png_save_uint_16(&row[x * 6 + 4], (unsigned int) image.data_blu[p]);
            }
            p++;
        }
        png_write_row(png_ptr, row);
    }

    // End write
    png_write_end(png_ptr, NULL);
    finalise:
    if (fp != NULL) fclose(fp);
    if (info_ptr != NULL) png_free_data(png_ptr, info_ptr, PNG_FREE_ALL, -1);
    if (png_ptr != NULL) png_destroy_write_struct(&png_ptr, (png_infopp) NULL);
    if (row != NULL) free(row);

    return code;
}
