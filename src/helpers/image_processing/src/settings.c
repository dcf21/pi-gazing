// settings.c
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

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include "utils/asciiDouble.h"
#include "utils/error.h"
#include "settings.h"
#include "str_constants.h"

void default_settings(settings *s, settings_input *si) {
    s->mode = MODE_FLAT;
    s->exposure_compensation = si->weight_in = si->exposure_compensation_in = 1;
    s->ra0 = s->dec0 = s->pa = s->linear_rotation = si->ra0_in = si->dec0_in = si->rotation_in = si->linear_rotation_in = 0;
    s->x_scale = s->y_scale = si->x_scale_in = si->y_scale_in = 10 * M_PI / 180;
    s->x_size = s->y_size = 100;
    s->x_off = s->y_off = 0;
    si->x_off_in = si->y_off_in = 0;
    s->cloud_mask = 0;

    si->barrel_k1 = si->barrel_k2 = si->barrel_k3 = 0;
    si->background_subtract = 0;
}

