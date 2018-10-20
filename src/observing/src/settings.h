// settings.h
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

// The settings below define how the video capture and analysis works

#ifndef _SETTINGS_H
#define _SETTINGS_H 1

// This is the directory into which we dump output video and image files
// Create a symlink in the meteor-pi root directory to where images should be stored, e.g.:
// dcf21@ganymede:~/camsci/meteor-pi$ ln -s /mnt/harddisk/pi/meteorCam datadir

#define OUTPUT_PATH  SRCDIR "/../../../../datadir"

// Size of buffer used for storing filenames
#define FNAME_BUFFER 4096

#endif

