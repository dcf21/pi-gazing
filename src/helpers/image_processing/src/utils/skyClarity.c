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

#define MIN(X, Y) (((X) < (Y)) ? (X) : (Y))
#define MAX(X, Y) (((X) > (Y)) ? (X) : (Y))

double calculate_sky_clarity(image_ptr *image, double noise_level) {
    int i, j, score = 0;
    const int grid_size = 10;
    const int search_distance = 4;

    // To be counted as a star-like source, must be this much brighter than surroundings
    const int threshold = MAX(12, noise_level * 4);
    const int stride = image->xsize;
#pragma omp parallel for private(i, j)
    for (i = 1; i < grid_size; i++)
        for (j = 1; j < grid_size; j++) {
            const int xmin = image->xsize * j / (grid_size + 1);
            const int ymin = image->ysize * i / (grid_size + 1);
            const int xmax = image->xsize * (j + 1) / (grid_size + 1);
            const int ymax = image->ysize * (i + 1) / (grid_size + 1);
            int x, y, n_bright_pixels = 0, n_stars = 0;
            const int n_pixels = (xmax - xmin) * (ymax - ymin);
            for (y = ymin; y < ymax; y++)
                for (x = xmin; x < xmax; x++) {
                    double pixel_value = image->data_red[y * stride + x];
                    if (pixel_value > 128) n_bright_pixels++;
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

                    if (!reject) n_stars++;
                }
            if ((n_stars >= 4) && (n_bright_pixels < n_pixels * 0.05)) {
#pragma omp critical (count_stars)
                { score++; }
            }
        }
    return (100. * score) / pow(grid_size - 1, 2);
}
