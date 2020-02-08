// skyClarity.c
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
#include <math.h>
#include <unistd.h>
#include "png/image.h"
#include "utils/skyClarity.h"

#define MAX(X, Y) (((X) > (Y)) ? (X) : (Y))

//! calculate_sky_clarity - Calculate a measure of the sky clarity within an image of the night sky, by estimating
//! the number of stars visible.
//! \param [in] image The image from which to estimate the sky clarity
//! \param [in] noise_level The random noise level in an average pixel of the image
//! \return A sky clarity metric

double calculate_sky_clarity(image_ptr *image, double noise_level) {
    int x, y, score = 0;
    const int search_distance = 4;

    // To be counted as a star-like source, must be this much brighter than surroundings
    const int threshold = MAX(20, noise_level * 4) * 256;
    const int stride = image->xsize;
#pragma omp parallel for private(x, y)
    for (y = search_distance; y < image->ysize - search_distance; y++)
        for (x = search_distance; x < image->xsize - search_distance; x++) {
            double pixel_value = image->data_red[y * stride + x];
            int k, reject = 0;
            for (k = -search_distance; (k <= search_distance) && (!reject); k += 2)
                if (pixel_value - threshold <= image->data_red[(y + search_distance) * stride + (x + k)])
                    reject = 1;
            for (k = -search_distance; (k <= search_distance) && (!reject); k += 2)
                if (pixel_value - threshold <= image->data_red[(y - search_distance) * stride + (x + k)])
                    reject = 1;
            for (k = -search_distance; (k <= search_distance) && (!reject); k += 2)
                if (pixel_value - threshold <= image->data_red[(y + k) * stride + (x + search_distance)])
                    reject = 1;
            for (k = -search_distance; (k <= search_distance) && (!reject); k += 2)
                if (pixel_value - threshold <= image->data_red[(y + k) * stride + (x - search_distance)])
                    reject = 1;

            if (!reject) {
#pragma omp critical (count_stars)
                { score++; }
            }
        }
    return score;
}
