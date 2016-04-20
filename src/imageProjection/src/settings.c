// settings.c
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

#include "asciidouble.h"
#include "error.h"
#include "settings.h"
#include "str_constants.h"

void DefaultSettings(settings *s, settingsIn *si) {
    s->mode = MODE_FLAT;
    s->ExpComp = si->InWeight = si->InExpComp = 1;
    s->RA0 = s->Dec0 = s->PA = s->LinearRot = si->InRA0 = si->InDec0 = si->InRotation = si->InLinearRotation = 0;
    s->XScale = s->YScale = si->InXScale = si->InYScale = 10 * M_PI / 180;
    s->XSize = s->YSize = 100;
    s->XOff = s->YOff = si->InXOff = si->InYOff = 0;
    s->cloudMask = 0;

    si->barrel_a = si->barrel_b = si->barrel_c = 0;
    si->backSub = 0;
    return;
}

