// imageProcess.c
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

// -------------------------------------------------
// Copyright 2016 Cambridge Science Centre.

// This file is part of Meteor Pi.

// Meteor Pi is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Meteor Pi is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include <gsl/gsl_errno.h>
#include <gsl/gsl_math.h>

#include "asciiDouble.h"
#include "error.h"
#include "gnomonic.h"
#include "image.h"
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

void StackImage(image_ptr InputImage, image_ptr OutputImage, image_ptr *CloudMaskAvg, image_ptr *CloudMaskThis,
                settings *s, settingsIn *si) {
    int j;

    // Loop over pixels
#pragma omp parallel for shared(InputImage, OutputImage, s) private(j)
    for (j = 0; j < OutputImage.ysize; j++) {
        int k;
        int l = OutputImage.xsize * j;
        for (k = 0; k < OutputImage.xsize; k++, l++) {
            double x = k, y = j;
            double theta, phi;
            if (s->mode == MODE_GNOMONIC) {
                InvGnomProject(&theta, &phi, s->RA0, s->Dec0, s->XSize, s->YSize, s->XScale, s->YScale, k, j, -s->PA, 0,
                               0, 0);
                GnomonicProject(theta, phi, si->InRA0, si->InDec0, InputImage.xsize, InputImage.ysize, si->InXScale,
                                si->InYScale, &x, &y, -si->InRotation, si->barrel_a, si->barrel_b, si->barrel_c);
            }
            double x2 = x - s->XOff - OutputImage.xsize / 2.;
            double y2 = y - s->YOff - OutputImage.ysize / 2.;
            double x3 = x2 * cos(si->InLinearRotation) + y2 * sin(si->InLinearRotation);
            double y3 = -x2 * sin(si->InLinearRotation) + y2 * cos(si->InLinearRotation);
            int xf = round(x3 + si->InXOff + InputImage.xsize / 2.);
            int yf = round(y3 + si->InYOff + InputImage.ysize / 2.);
            if ((xf < 0) || (yf < 0) || (xf >= InputImage.xsize) || (yf >= InputImage.ysize)) continue;

            double w = si->InWeight * si->InExpComp * s->ExpComp;

            if (CloudMaskAvg != NULL) {
                double maskLevel = (CloudMaskAvg->data_red[l] + CloudMaskAvg->data_grn[l] + CloudMaskAvg->data_blu[l]) /
                                   si->InExpComp / s->ExpComp;
                double thisLevel = CloudMaskThis->data_red[xf + yf * CloudMaskThis->xsize] +
                                   CloudMaskThis->data_grn[xf + yf * CloudMaskThis->xsize] +
                                   CloudMaskThis->data_blu[xf + yf * CloudMaskThis->xsize];
                if (thisLevel > (maskLevel + 8))
                    continue; // If pixel level is above average, throw it out because it is cloud.
            }

            OutputImage.data_red[l] += w * (InputImage.data_red[xf + yf * InputImage.xsize]);
            OutputImage.data_grn[l] += w * (InputImage.data_grn[xf + yf * InputImage.xsize]);
            OutputImage.data_blu[l] += w * (InputImage.data_blu[xf + yf * InputImage.xsize]);
            OutputImage.data_w[l] += si->InWeight;
        }
    }
    return;
}

double ImageOffset(image_ptr InputImage, image_ptr OutputImage, settings *s, settingsIn *si) {
    int j;
    double offset = 0;
    double offset_count = 1e-20;

    // Loop over pixels
#pragma omp parallel for shared(InputImage, OutputImage, s, offset, offset_count) private(j)
    for (j = 0; j < OutputImage.ysize / 2; j++) // Only use top half of image -- fudge to avoid trees in bottom of frame
    {
        int k;
        int l = OutputImage.xsize * j;
        for (k = 0; k < OutputImage.xsize; k++, l++) {
            double x = k, y = j;
            double theta, phi;
            if (s->mode == MODE_GNOMONIC) {
                InvGnomProject(&theta, &phi, s->RA0, s->Dec0, s->XSize, s->YSize, s->XScale, s->YScale, k, j, -s->PA, 0,
                               0, 0);
                GnomonicProject(theta, phi, si->InRA0, si->InDec0, InputImage.xsize, InputImage.ysize, si->InXScale,
                                si->InYScale, &x, &y, -si->InRotation, si->barrel_a, si->barrel_b, si->barrel_c);
            }
            double x2 = x - s->XOff - OutputImage.xsize / 2.;
            double y2 = y - s->YOff - OutputImage.ysize / 2.;
            double x3 = x2 * cos(si->InLinearRotation) + y2 * sin(si->InLinearRotation);
            double y3 = -x2 * sin(si->InLinearRotation) + y2 * cos(si->InLinearRotation);
            int xf = round(x3 + si->InXOff + InputImage.xsize / 2.);
            int yf = round(y3 + si->InYOff + InputImage.ysize / 2.);
            if ((xf < 0) || (yf < 0) || (xf >= InputImage.xsize) || (yf >= InputImage.ysize)) continue;

            double w = si->InWeight * si->InExpComp * s->ExpComp;

#pragma omp critical (add_event)
            {
                offset += fabs(OutputImage.data_red[l] - w * (InputImage.data_red[xf + yf * InputImage.xsize]));
                offset += fabs(OutputImage.data_grn[l] - w * (InputImage.data_grn[xf + yf * InputImage.xsize]));
                offset += fabs(OutputImage.data_blu[l] - w * (InputImage.data_blu[xf + yf * InputImage.xsize]));
                offset_count += 1;
            }
        }
    }
    return offset / offset_count;
}

