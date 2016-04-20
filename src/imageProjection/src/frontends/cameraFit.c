// cameraFit.c
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
#include <gsl/gsl_multimin.h>
#include <gsl/gsl_vector.h>

#include "asciidouble.h"
#include "error.h"
#include "gnomonic.h"
#include "imageProcess.h"
#include "image.h"
#include "readConfig.h"
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

#define IMAGES_MAX 1024

settings s_model, *feed_s = &s_model;
settingsIn s_in[IMAGES_MAX], s_in_default;
int nImages = 0;
image_ptr OutputImage;
image_ptr InputImage[IMAGES_MAX];

double fitSlave(const gsl_vector *x, void *params) {
    int i;
    static int framecount = 0;
    double offset = 0;

    // Malloc output image
    image_alloc(&OutputImage, feed_s->XSize, feed_s->YSize);

    for (i = 0; i < nImages; i++) {
        s_in[i].barrel_a = gsl_vector_get(x, 0);
        s_in[i].barrel_b = gsl_vector_get(x, 1);
        s_in[i].barrel_c = gsl_vector_get(x, 2);

        // Process image
        StackImage(InputImage[i], OutputImage, NULL, NULL, feed_s, s_in + i);
    }

    // Normalise image
    image_deweight(&OutputImage);

    for (i = 0; i < nImages; i++) {
        // Process image
        offset += ImageOffset(InputImage[i], OutputImage, feed_s, s_in + i);
    }

    // End
    {
        char fname[1024];
        sprintf(fname, "/tmp/camfit_fr%06d.jpg", framecount);
        image_put(fname, OutputImage);
        framecount++;
    }
    image_dealloc(&OutputImage);
    printf("Tried (%9.5f,%9.5f,%9.5f) -- offset %e\n", gsl_vector_get(x, 0), gsl_vector_get(x, 1), gsl_vector_get(x, 2),
           offset);
    return offset;
}

int main(int argc, char **argv) {
    char help_string[LSTR_LENGTH], version_string[FNAME_LENGTH], version_string_underline[FNAME_LENGTH];
    char *filename = NULL;
    int i, HaveFilename = 0;

    // Initialise sub-modules
    if (DEBUG) gnom_log("Initialising camfit.");
    DefaultSettings(feed_s, &s_in_default);

    // Turn off GSL's automatic error handler
    gsl_set_error_handler_off();

    // Make help and version strings
    sprintf(version_string, "Camera Lens Distortion Fitter %s", VERSION);

    sprintf(help_string, "Camera Lens Distortion Fitter %s\n\
%s\n\
\n\
Usage: camfit.bin <filename>\n\
  -h, --help:       Display this help.\n\
  -v, --version:    Display version number.", VERSION, StrUnderline(version_string, version_string_underline));

    // Scan commandline options for any switches
    HaveFilename = 0;
    for (i = 1; i < argc; i++) {
        if (strlen(argv[i]) == 0) continue;
        if (argv[i][0] != '-') {
            HaveFilename++;
            filename = argv[i];
            continue;
        }
        if ((strcmp(argv[i], "-v") == 0) || (strcmp(argv[i], "-version") == 0) || (strcmp(argv[i], "--version") == 0)) {
            gnom_report(version_string);
            return 0;
        }
        else if ((strcmp(argv[i], "-h") == 0) || (strcmp(argv[i], "-help") == 0) || (strcmp(argv[i], "--help") == 0)) {
            gnom_report(help_string);
            return 0;
        }
        else {
            sprintf(temp_err_string,
                    "Received switch '%s' which was not recognised.\nType 'camfit.bin -help' for a list of available commandline options.",
                    argv[i]);
            gnom_error(ERR_GENERAL, temp_err_string);
            return 1;
        }
    }

    // Check that we have been provided with exactly one filename on the command line
    if (HaveFilename < 1) {
        sprintf(temp_err_string,
                "camfit.bin should be provided with a filename on the command line to act upon. Type 'camfit.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }
    else if (HaveFilename > 1) {
        sprintf(temp_err_string,
                "camfit.bin should be provided with only one filename on the command line to act upon. Multiple filenames appear to have been supplied. Type 'camfit.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }

    // Go through command script line by line
    if (readConfig(filename, feed_s, s_in, &s_in_default, &nImages)) return 1;

    // Read images
    for (i = 0; i < nImages; i++) {
        // Read image
        InputImage[i] = image_get(s_in[i].InFName);
        if (InputImage[i].data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file");
        backgroundSubtract(InputImage[i], s_in + i);
    }

    {
        int iter = 0, i = 0, j = 0, status = 0;
        gsl_vector *x = gsl_vector_alloc(3), *ss = gsl_vector_alloc(3);

        const gsl_multimin_fminimizer_type *T = gsl_multimin_fminimizer_nmsimplex;
        gsl_multimin_fminimizer *s;
        gsl_multimin_function fn;

        fn.n = 3;
        fn.params = NULL;
        fn.f = fitSlave;

        gsl_vector_set(x, 0, s_in_default.barrel_a);
        gsl_vector_set(ss, 0, 0.01);
        gsl_vector_set(x, 1, s_in_default.barrel_b);
        gsl_vector_set(ss, 1, 0.01);
        gsl_vector_set(x, 2, s_in_default.barrel_c);
        gsl_vector_set(ss, 2, 0.01);

        s = gsl_multimin_fminimizer_alloc(T, fn.n);
        gsl_multimin_fminimizer_set(s, &fn, x, ss);

        for (j = 0; j < 10; j++) {
            iter++;
            for (i = 0; i < 10; i++) {
                status = gsl_multimin_fminimizer_iterate(s);
                if (status) break;
            }
        }
    }

    // Free images
    for (i = 0; i < nImages; i++) {
        image_dealloc(InputImage + i);
    }


    if (DEBUG) gnom_log("Terminating normally.");
    return 0;
}

