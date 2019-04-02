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

image_ptr lensCorrect(image_ptr *imgIn, double barrelA, double barrelB, double barrelC) {
    const int width = imgIn->xsize;
    const int height = imgIn->ysize;
    const double barrelD = 1 - barrelA - barrelB - barrelC;

    int x, y;

    image_ptr imgNew;
    image_alloc(&imgNew, width, height);

    for (y = 0; y < height; y++)
        for (x = 0; x < width; x++) {
            // Index of pixel in new image
            int oNew = x + y * width;

            // Offset of pixel from center of image, expressed as position angle and radial distance
            int x2 = x - width / 2;
            int y2 = y - height / 2;
            double r = hypot(x2, y2) / (width / 2);
            double t = atan2(x2, y2);

            // Apply barrel correction to radial component of position
            double r2 = (((barrelA * r + barrelB) * r + barrelC) * r + barrelD) * r * (width / 2);

            // Calculate offset of pixel in the original (uncorrected) pixel array
            int x3 = r2 * sin(t) + width / 2;
            int y3 = r2 * cos(t) + height / 2;
            int oOld = x3 + y3 * width;

            if ((x3 >= 0) && (x3 < width) && (y3 >= 0) && (y3 < height)) {
                imgNew.data_red[oNew] = imgIn->data_red[oOld];
                imgNew.data_grn[oNew] = imgIn->data_grn[oOld];
                imgNew.data_blu[oNew] = imgIn->data_blu[oOld];
            }
        }

    imgNew.data_w = imgIn->data_w;
    return imgNew;
}
