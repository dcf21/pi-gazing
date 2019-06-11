// imageProcess.c
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
#include <string.h>
#include <ctype.h>
#include <math.h>

#include <gsl/gsl_errno.h>
#include <gsl/gsl_math.h>

#include "utils/asciiDouble.h"
#include "error.h"
#include "gnomonic.h"
#include "png/image.h"
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

//! StackImage - Add an image to a stack, including shifting the new image into alignment with the stacked image
//! \param image_input The image to add to the stack
//! \param image_output The stacked image we are to add this image to
//! \param cloud_mask_average The background from an average of previous images.
//! \param cloud_mask_this The sky background in this particular image. If much brighter than the average, throw this
//! pixel out as cloud
//! \param s settings pertaining to the input image
//! \param si settings pertaining globally to this fitting run

void StackImage(image_ptr image_input, image_ptr image_output, image_ptr *cloud_mask_average,
        image_ptr *cloud_mask_this, settings *s, settings_input *si) {
    int j;

    // Loop over pixels
#pragma omp parallel for shared(image_input, image_output, s) private(j)
    for (j = 0; j < image_output.ysize; j++) {
        int k;
        int l = image_output.xsize * j;
        for (k = 0; k < image_output.xsize; k++, l++) {
            double x = k, y = j;
            double theta, phi;
            if (s->mode == MODE_GNOMONIC) {
                inv_gnomonic_project(&theta, &phi, s->ra0, s->dec0, s->x_size, s->y_size, s->x_scale, s->y_scale, k, j,
                                     -s->pa, 0, 0, 0);
                gnomonic_project(theta, phi, si->ra0_in, si->dec0_in, image_input.xsize, image_input.ysize,
                                 si->x_scale_in, si->y_scale_in, &x, &y, -si->rotation_in,
                                 si->barrel_a, si->barrel_b, si->barrel_c);
            }
            double x2 = x - s->x_off - image_output.xsize / 2.;
            double y2 = y - s->y_off - image_output.ysize / 2.;
            double x3 = x2 * cos(si->linear_rotation_in) + y2 * sin(si->linear_rotation_in);
            double y3 = -x2 * sin(si->linear_rotation_in) + y2 * cos(si->linear_rotation_in);
            int xf = (int)round(x3 + si->x_off_in + image_input.xsize / 2.);
            int yf = (int)round(y3 + si->y_off_in + image_input.ysize / 2.);
            if ((xf < 0) || (yf < 0) || (xf >= image_input.xsize) || (yf >= image_input.ysize)) continue;

            double w = si->weight_in * si->exposure_compensation_in * s->exposure_compensation;

            if (cloud_mask_average != NULL) {
                double maskLevel = (cloud_mask_average->data_red[l] +
                        cloud_mask_average->data_grn[l] +
                        cloud_mask_average->data_blu[l]) /
                                   si->exposure_compensation_in / s->exposure_compensation;
                double thisLevel = cloud_mask_this->data_red[xf + yf * cloud_mask_this->xsize] +
                                   cloud_mask_this->data_grn[xf + yf * cloud_mask_this->xsize] +
                                   cloud_mask_this->data_blu[xf + yf * cloud_mask_this->xsize];
                if (thisLevel > (maskLevel + 8))
                    continue; // If pixel level is above average, throw it out because it is cloud.
            }

            image_output.data_red[l] += w * (image_input.data_red[xf + yf * image_input.xsize]);
            image_output.data_grn[l] += w * (image_input.data_grn[xf + yf * image_input.xsize]);
            image_output.data_blu[l] += w * (image_input.data_blu[xf + yf * image_input.xsize]);
            image_output.data_w[l] += si->weight_in;
        }
    }
}

double image_offset(image_ptr image_input, image_ptr image_output, settings *s, settings_input *si) {
    int j;
    double offset = 0;
    double offset_count = 1e-20;

    // Loop over pixels
#pragma omp parallel for shared(image_input, image_output, s, offset, offset_count) private(j)
    for (j = 0; j < image_output.ysize / 2; j++) // Only use top half of image -- fudge to avoid trees in bottom of frame
    {
        int k;
        int l = image_output.xsize * j;
        for (k = 0; k < image_output.xsize; k++, l++) {
            double x = k, y = j;
            double theta, phi;
            if (s->mode == MODE_GNOMONIC) {
                inv_gnomonic_project(&theta, &phi, s->ra0, s->dec0, s->x_size, s->y_size, s->x_scale, s->y_scale, k, j,
                                     -s->pa, 0,
                                     0, 0);
                gnomonic_project(theta, phi, si->ra0_in, si->dec0_in, image_input.xsize, image_input.ysize,
                                 si->x_scale_in, si->y_scale_in, &x, &y, -si->rotation_in,
                                 si->barrel_a, si->barrel_b, si->barrel_c);
            }
            double x2 = x - s->x_off - image_output.xsize / 2.;
            double y2 = y - s->y_off - image_output.ysize / 2.;
            double x3 = x2 * cos(si->linear_rotation_in) + y2 * sin(si->linear_rotation_in);
            double y3 = -x2 * sin(si->linear_rotation_in) + y2 * cos(si->linear_rotation_in);
            int xf = (int)round(x3 + si->x_off_in + image_input.xsize / 2.);
            int yf = (int)round(y3 + si->y_off_in + image_input.ysize / 2.);
            if ((xf < 0) || (yf < 0) || (xf >= image_input.xsize) || (yf >= image_input.ysize)) continue;

            double w = si->weight_in * si->exposure_compensation_in * s->exposure_compensation;

#pragma omp critical (add_event)
            {
                offset += fabs(image_output.data_red[l] - w * (image_input.data_red[xf + yf * image_input.xsize]));
                offset += fabs(image_output.data_grn[l] - w * (image_input.data_grn[xf + yf * image_input.xsize]));
                offset += fabs(image_output.data_blu[l] - w * (image_input.data_blu[xf + yf * image_input.xsize]));
                offset_count += 1;
            }
        }
    }
    return offset / offset_count;
}
