// settings.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

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

