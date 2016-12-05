// settings_webcam.h
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

#ifndef _SETTINGS2_H
#define _SETTINGS2_H 1

// Define the device from which to capture video, and the resolution and frame-rate we expect from it
// These parameters affect test bench routines such as vidRec and snapshot. Main observe process overrides these with data passed on the command line

#define VIDEO_DEV    "/dev/video0"
#define VIDEO_WIDTH  720
#define VIDEO_HEIGHT 480
#define VIDEO_FPS    24.71 /* Empirically determined */
#define VIDEO_UPSIDE_DOWN 0 /* If this flag is set, we assume the camera is mounted upside down. Video is flipped before analysis. */

#define Nchannels ( ALLDATAMONO ? 1 : 3 ) /* Number of colour channels to process. *Much* faster to process only one */

// This is the mean pixel brightness that we aim for in output images, applying whatever automatic gain is needed to get there

#define STACK_TARGET_BRIGHTNESS  32

// Throttle the number of triggers which are allowed
#define TRIGGER_THROTTLE_PERIOD 30 /* number of minutes */
#define TRIGGER_THROTTLE_MAXEVT  5 /* number of triggers allowed in that time */

// Trigger parameters
#define TRIGGER_MAXRECORDLEN 25  /* maximum length of video to record after trigger */
#define TRIGGER_PREFIX_TIME   2  /* include N seconds of video after trigger */
#define TRIGGER_SUFFIX_TIME   3  /* include N seconds of video after trigger has gone away */
#define TRIGGER_FRAMEGROUP    4  /* triggering is calculated on the basis of stacked groups of frames of this length */

#define STACK_COMPARISON_INTERVAL 3 /* Compare stacked groups of frames that are two stacks apart; makes us more sensitive to slow-moving things */

// Timelapse
#define TIMELAPSE_EXPOSURE 28 /* Exposure length for timelapse photography */
#define TIMELAPSE_INTERVAL 30 /* Interval between timelapse frames */

#endif

