// settings.h
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

#ifndef SETTINGS_H
#define SETTINGS_H 1

#include <stdlib.h>
#include "str_constants.h"

#define MODE_FLAT     1000
#define MODE_GNOMONIC 1001

typedef struct settings
 {
  int    mode;
  char   OutFName[FNAME_LENGTH];
  double ExpComp, RA0, Dec0, PA, XScale, YScale, LinearRot;
  int    XSize, YSize, XOff, YOff;
  int    cloudMask;
 } settings;

typedef struct settingsIn
 {
  char   InFName[FNAME_LENGTH];
  int    InXSize, InYSize;
  double InExpComp, InRA0, InDec0, InXScale, InYScale, InRotation, InWeight, InXOff, InYOff, InLinearRotation;
  double barrel_a, barrel_b, barrel_c;
  int    backSub;
 } settingsIn;

void DefaultSettings(settings *s, settingsIn *si);

#endif
