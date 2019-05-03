// imageProcess.h
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

#ifndef IMAGEPROCESS_H
#define IMAGEPROCESS_H 1

#include <stdlib.h>

#include "image.h"
#include "settings.h"

void StackImage(image_ptr InputImage, image_ptr OutputImage, image_ptr *CloudMaskAvg, image_ptr *CloudMaskThis,
                settings *s, settingsIn *si);

double ImageOffset(image_ptr InputImage, image_ptr OutputImage, settings *s, settingsIn *si);

#endif
