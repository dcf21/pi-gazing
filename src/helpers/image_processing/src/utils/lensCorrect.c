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

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include <gsl/gsl_math.h>

#include "png/image.h"

//! lens_correct - Create a new version of the image pointed to by <image_in>, with radial barrel distortion corrected.
//! The radial distortion is assumed by be expressible as:
//! r_new = r / (Kn + K1 r^2 + K2 r^4),
//! where Kn=(1 - K1 - K2), which ensures the far edges of the image remain at fixed distance from the centre
//! \param image_in The input image
//! \param [in] barrel_k1 The barrel distortion parameter K1
//! \param [in] barrel_k2 The barrel distortion parameter K2
//! \param [in] barrel_k3 The barrel distortion parameter K3
//! \param [in] scale_x horizontal field width / radians
//! \param [in] scale_y vertical field width / radians
//! \return A pointer to an image with barrel-correction applied

image_ptr lens_correct(image_ptr *image_in, double barrel_k1, double barrel_k2, double barrel_k3,
                       double scale_x, double scale_y) {
    const int width = image_in->xsize;
    const int height = image_in->ysize;
    const double barrel_kn = 1 - barrel_k1 - barrel_k2 - barrel_k3;

    int x, y;

    image_ptr image_new;
    image_alloc(&image_new, width, height);

    for (y = 0; y < height; y++)
        for (x = 0; x < width; x++) {
            // Index of pixel in new image
            int offset_new = x + y * width;

            // Offset of pixel from center of image, expressed as position angle and radial distance
            double x2 = (x - width / 2.) / (width / 2. / tan(scale_x / 2.));
            double y2 = (y - height / 2.) / (height / 2. / tan(scale_y / 2.));
            double radius = hypot(x2, y2);
            double t = atan2(x2, y2);

            // Apply barrel correction to radial component of position
            double r = radius / tan(scale_x / 2.);
            double R = r * (barrel_kn + barrel_k1 * gsl_pow_2(r) + barrel_k2 * gsl_pow_4(r) + barrel_k3 * gsl_pow_6(r));
            radius = R * tan(scale_x / 2);

            // Calculate offset of pixel in the original (uncorrected) pixel array
            int x3 = radius * sin(t) * (width / 2. / tan(scale_x / 2.)) + width / 2.;
            int y3 = radius * cos(t) * (height / 2. / tan(scale_y / 2.)) + height / 2.;
            int offset_old = x3 + y3 * width;

            if ((x3 >= 0) && (x3 < width) && (y3 >= 0) && (y3 < height)) {
                image_new.data_red[offset_new] = image_in->data_red[offset_old];
                image_new.data_grn[offset_new] = image_in->data_grn[offset_old];
                image_new.data_blu[offset_new] = image_in->data_blu[offset_old];
                image_new.data_w[offset_new] = image_in->data_w[offset_old];
            }
        }

    return image_new;
}
