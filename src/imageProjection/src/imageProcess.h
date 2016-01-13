// imageProcess.h
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

#ifndef IMAGEPROCESS_H
#define IMAGEPROCESS_H 1

#include <stdlib.h>

#include "image.h"
#include "settings.h"

void   StackImage (image_ptr InputImage, image_ptr OutputImage, image_ptr *CloudMaskAvg, image_ptr *CloudMaskThis, settings *s, settingsIn *si);
double ImageOffset(image_ptr InputImage, image_ptr OutputImage, settings *s, settingsIn *si);

#endif
