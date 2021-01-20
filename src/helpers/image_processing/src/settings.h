// settings.h
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2021 Dominic Ford.

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

#ifndef SETTINGS_H
#define SETTINGS_H 1

#include <stdlib.h>
#include "str_constants.h"

// This is the directory into which we dump output video and image files
#define OUTPUT_PATH  SRCDIR "/../../../../datadir"
#define GREYSCALE_IMAGING 1

#define MODE_FLAT     1000
#define MODE_GNOMONIC 1001

typedef struct settings {
    int mode;
    char output_filename[FNAME_LENGTH];
    double exposure_compensation, ra0, dec0, pa, x_scale, y_scale, linear_rotation;
    int x_size, y_size, x_off, y_off;
    int cloud_mask;
} settings;

typedef struct settings_input {
    char input_filename[FNAME_LENGTH];
    int x_size_in, y_size_in;
    double exposure_compensation_in, ra0_in, dec0_in, x_scale_in, y_scale_in, rotation_in, weight_in;
    double x_off_in, y_off_in, linear_rotation_in;
    double barrel_k1, barrel_k2, barrel_k3;
    int background_subtract;
} settings_input;

void default_settings(settings *s, settings_input *si);

#endif
