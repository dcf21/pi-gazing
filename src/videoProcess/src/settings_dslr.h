// settings_dslr.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// The settings below define how the video capture and analysis works

#ifndef _SETTINGS2_H
#define _SETTINGS2_H 1

// Define the device from which to capture video, and the resolution and frame-rate we expect from it
// These parameters affect test bench routines such as vidRec and snapshot. Main observe process overrides these with data passed on the command line

#define VIDEO_WIDTH  1024
#define VIDEO_HEIGHT 768
#define VIDEO_FPS    0.125
#define VIDEO_UPSIDE_DOWN 0 /* If this flag is set, we assume the camera is mounted upside down. Video is flipped before analysis. */

#define Nchannels ( ALLDATAMONO ? 1 : 3 ) /* Number of colour channels to process. *Much* faster to process only one */

// This is the gain that we apply to background-subtracted images taken as a time-lapse sequence through the night

#define STACK_GAIN 5

// Throttle the number of triggers which are allowed
#define TRIGGER_THROTTLE_PERIOD 10 /* number of minutes */
#define TRIGGER_THROTTLE_MAXEVT  4 /* number of triggers allowed in that time */

// Trigger parameters
#define TRIGGER_MAXRECORDLEN 200  /* maximum length of video to record after trigger */
#define TRIGGER_PREFIX_TIME   16  /* include N seconds of video after trigger */
#define TRIGGER_SUFFIX_TIME   16  /* include N seconds of video after trigger has gone away */
#define TRIGGER_FRAMEGROUP     1  /* triggering is calculated on the basis of stacked groups of frames of this length */

#define STACK_COMPARISON_INTERVAL 1 /* Compare stacked groups of frames that are two stacks apart; makes us more sensitive to slow-moving things */

// Timelapse
#define TIMELAPSE_EXPOSURE 32 /* Exposure length for timelapse photography */
#define TIMELAPSE_INTERVAL 40 /* Interval between timelapse frames */

#endif

