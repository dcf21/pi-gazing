// lensCorrect.c
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
#include <math.h>

#include "png/image.h"

image_ptr lens_correct(image_ptr *image_in, double barrel_a, double barrel_b, double barrel_c) {
    const int width = image_in->xsize;
    const int height = image_in->ysize;
    const double barrelD = 1 - barrel_a - barrel_b - barrel_c;

    int x, y;

    image_ptr image_new;
    image_alloc(&image_new, width, height);

    for (y = 0; y < height; y++)
        for (x = 0; x < width; x++) {
            // Index of pixel in new image
            int offset_new = x + y * width;

            // Offset of pixel from center of image, expressed as position angle and radial distance
            int x2 = x - width / 2;
            int y2 = y - height / 2;
            double r = hypot(x2, y2) / (width / 2);
            double t = atan2(x2, y2);

            // Apply barrel correction to radial component of position
            double r2 = (((barrel_a * r + barrel_b) * r + barrel_c) * r + barrelD) * r * (width / 2);

            // Calculate offset of pixel in the original (uncorrected) pixel array
            int x3 = r2 * sin(t) + width / 2;
            int y3 = r2 * cos(t) + height / 2;
            int offset_old = x3 + y3 * width;

            if ((x3 >= 0) && (x3 < width) && (y3 >= 0) && (y3 < height)) {
                image_new.data_red[offset_new] = image_in->data_red[offset_old];
                image_new.data_grn[offset_new] = image_in->data_grn[offset_old];
                image_new.data_blu[offset_new] = image_in->data_blu[offset_old];
            }
        }

    image_new.data_w = image_in->data_w;
    return image_new;
}
