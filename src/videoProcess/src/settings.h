// settings.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// The settings below define how the video capture and analysis works

#ifndef _SETTINGS_H
#define _SETTINGS_H 1

// Define the device from which to capture video, and the resolution and frame-rate we expect from it

#define VIDEO_DEV    "/dev/video0"
#define VIDEO_WIDTH  720
#define VIDEO_HEIGHT 480
#define VIDEO_FPS    24.71 // Empirically determined

// If this flag is set, we assume the camera is mounted upside down. Video is flipped before analysis.

#define VIDEO_UPSIDE_DOWN 1

// This is the directory into which we dump output video and image files
// Create a symlink in the meteor-pi root directory to where images should be stored, e.g.:
// dcf21@ganymede:~/camsci/meteor-pi$ ln -s /mnt/harddisk/pi/meteorCam datadir

#define OUTPUT_PATH  SRCDIR "/../../../datadir"

// This is the gain that we apply to stacked images taken as a time-lapse sequence through the night

#define STACK_GAIN 4

// Throttle the number of triggers which are allowed
#define TRIGGER_THROTTLE_PERIOD 10 /* number of minutes */
#define TRIGGER_THROTTLE_MAXEVT  5 /* number of triggers allowed in that time */

#define TRIGGER_RECORDLEN  9   /* second of video to record after trigger */
#define TRIGGER_COMPARELEN 0.5 /* triggering is calculated on the basis of comparing buffers of this length */

// Timelapse
#define TIMELAPSE_EXPOSURE 29 /* Exposure length for timelapse photography */
#define TIMELAPSE_INTERVAL 30 /* Interval between timelapse frames */

// Size of buffer used for storing filenames
#define FNAME_BUFFER 4096

#endif

