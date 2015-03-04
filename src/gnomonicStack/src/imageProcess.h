// imageProcess.h
// $Id: imageProcess.h 1137 2014-11-24 22:18:14Z pyxplot $

#ifndef IMAGEPROCESS_H
#define IMAGEPROCESS_H 1

#include <stdlib.h>

#include "jpeg.h"
#include "settings.h"

void   StackImage (image_ptr InputImage, image_ptr OutputImage, image_ptr *CloudMaskAvg, image_ptr *CloudMaskThis, settings *s, settingsIn *si);
double ImageOffset(image_ptr InputImage, image_ptr OutputImage, settings *s, settingsIn *si);

#endif
