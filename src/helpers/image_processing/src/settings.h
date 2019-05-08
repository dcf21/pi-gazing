// settings.h
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
    char OutFName[FNAME_LENGTH];
    double ExpComp, RA0, Dec0, PA, XScale, YScale, LinearRot;
    int XSize, YSize, XOff, YOff;
    int cloudMask;
} settings;

typedef struct settingsIn {
    char InFName[FNAME_LENGTH];
    int InXSize, InYSize;
    double InExpComp, InRA0, InDec0, InXScale, InYScale, InRotation, InWeight, InXOff, InYOff, InLinearRotation;
    double barrel_a, barrel_b, barrel_c;
    int backSub;
} settingsIn;

void defaultSettings(settings *s, settingsIn *si);

#endif
