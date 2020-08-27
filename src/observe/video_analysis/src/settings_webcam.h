// settings_webcam.h
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

// The settings below define how the video capture and analysis works, when we are recording video from a webcam

#ifndef _SETTINGS_WEBCAM_H
#define _SETTINGS_WEBCAM_H 1

// Define the device from which to capture video, and the resolution and frame-rate we expect from it.
// These parameters affect test bench routines such as vidRec and snapshot. Main observe process overrides these with
// data passed on the command line.

#define VIDEO_DEV    "/dev/video0"
#define VIDEO_WIDTH  720
#define VIDEO_HEIGHT 576
#define VIDEO_FPS    24.71 /* Empirically determined */

// If this flag is set, we assume the camera is mounted upside down. Video is flipped before analysis.
#define VIDEO_UPSIDE_DOWN 0

// This is the mean pixel brightness that we aim for in output images, applying whatever automatic gain is needed to
// get there.
#define STACK_TARGET_BRIGHTNESS  24

// Throttle the number of triggers which are allowed
#define TRIGGER_THROTTLE_PERIOD 30 /* number of minutes */
#define TRIGGER_THROTTLE_MAXEVT  8 /* number of triggers allowed in that time */

// Trigger parameters
#define VIDEO_BUFFER_LENGTH  100  /* maximum period of video to buffer in ram */
#define TRIGGER_PREFIX_TIME    2  /* include N seconds of video after trigger */
#define TRIGGER_SUFFIX_TIME    4  /* include N seconds of video after trigger has gone away */

#define TRIGGER_SUFFIX_TIME_INITIAL  0.25 /* An object which has only been seen once must recur within this time */

#define TRIGGER_MIN_DETECTIONS  2 /* The minimum number of frames in which a moving object must be detected */
#define TRIGGER_MIN_PATH_LENGTH 4 /* The minimum number of pixels that the moving object must move across the frame */
#define TRIGGER_MAX_MOVEMENT_PER_FRAME 70 /* The maximum distance a moving object may move from one frame to next */

#define TRIGGER_MIN_SIGNIFICANCE 20 /* The number of standard deviations above the noise level for a moving object */
#define TRIGGER_MIN_SIGNIFICANCE_INITIAL 30 /* As above, but specifically for the initial detection of an object */


// Processing of background map
#define BACKGROUND_MAP_FRAMES 3000 /* Produce a new background map every 2 minutes */
#define BACKGROUND_MAP_SAMPLES 10 /* Pick the lowest sky brightness from the last 10 buffers */
#define BACKGROUND_MAP_REDUCTION_CYCLES 64 /* Reduce the new background map over the course of N frames */

// Compare stacked groups of frames that are N stacks apart; makes us more sensitive to slow-moving things
#define STACK_COMPARISON_INTERVAL 4

// Time-lapse
#define TIMELAPSE_EXPOSURE  60 /* Exposure length for time-lapse photography */
#define TIMELAPSE_INTERVAL 240 /* Interval between time-lapse frames */

#endif

