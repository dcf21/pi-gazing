// image.h
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

#ifndef IMAGE_H
#define IMAGE_H 1

/* Variable format used to store images */

typedef struct {
    int xsize;
    int ysize;
    double *data_w;
    double *data_red;
    double *data_grn;
    double *data_blu;
} image_ptr;

/* Variable format used to image pixels */

typedef struct {
    double red;
    double grn;
    double blu;
} pixel;

/* Functions defined in image_in.c */
void image_alloc(image_ptr *out, int x, int y);

void image_dealloc(image_ptr *in);

void image_cp(image_ptr *in, image_ptr *out);

void image_deweight(image_ptr *out);

image_ptr image_get(const char *filename);

/* Functions defined in image_out.c */
int image_put(const char *output_filename, image_ptr image, int greyscale);

#endif

