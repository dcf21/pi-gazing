// lensCorrect.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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
