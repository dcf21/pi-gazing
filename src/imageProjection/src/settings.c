// settings.c
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

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

