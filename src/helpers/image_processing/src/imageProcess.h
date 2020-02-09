// imageProcess.h
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

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

void StackImage(image_ptr image_input, image_ptr image_output, image_ptr *cloud_mask_average, image_ptr *cloud_mask_this,
                settings *s, settings_input *si);

double image_offset(image_ptr image_input, image_ptr image_output, settings *s, settings_input *si);

#endif
