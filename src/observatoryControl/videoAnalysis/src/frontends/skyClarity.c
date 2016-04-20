// skyClarity.c
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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "png/image.h"
#include "utils/tools.h"
#include "utils/asciidouble.h"
#include "utils/error.h"

int main(int argc, char *argv[]) {
    if (argc != 3) {
        sprintf(temp_err_string,
                "ERROR: Need to specify input filename and noise level on the commandline, e.g. 'skyClarity tmp.png 3.45'.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    double noiseLevel = GetFloat(argv[2], NULL);

    // Read image
    image_ptr InputImage;
    InputImage = image_get(argv[1]);
    if (InputImage.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file 1");

    double skyClarity = calculateSkyClarity(&InputImage, noiseLevel);
    printf("%f", skyClarity);

    // Free image
    image_dealloc(&InputImage);
    return 0;
}
