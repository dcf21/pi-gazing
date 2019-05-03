// observe.h
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

#ifndef OBSERVE_H
#define OBSERVE_H 1

#define MAX_DETECTIONS 1024 /* Maximum detections of a single event; about 40 seconds of frames */
#define MAX_EVENTS        3 /* Number of simultaneous events */

#define MAX_TRIGGER_BLOCKS 65536

#include "str_constants.h"

typedef struct detection {
    int frameCount;
    int x, y, npixels, amplitude;
    double utc;
} detection;

typedef struct event {
    int active;
    int Ndetections;
    char filenameStub[FNAME_LENGTH]; // When testTrigger detects a meteor, this string is set to a filename stub with time stamp of the time when the camera triggered
    int *stackedImage; // Stacked image, averaged over whole duration of event
    int *maxStack; // Maximum pixel values over whole duration of event
    detection detections[MAX_DETECTIONS];
} event;

typedef struct videoOutput {
    int active;
    int width;
    int height;
    unsigned char *buffer1;
    int buffer1frames;
    unsigned char *buffer2;
    int buffer2frames;
    char fName[FNAME_LENGTH];
    FILE *fileHandle;
    int framesWritten;
} videoOutput;

typedef struct observeStatus {
    // Trigger settings
    int Nchannels;
    int STACK_COMPARISON_INTERVAL;
    int TRIGGER_PREFIX_TIME;
    int TRIGGER_SUFFIX_TIME;
    int TRIGGER_FRAMEGROUP;
    int TRIGGER_MAXRECORDLEN;
    int TRIGGER_THROTTLE_PERIOD;
    int TRIGGER_THROTTLE_MAXEVT;
    int TIMELAPSE_EXPOSURE;
    int TIMELAPSE_INTERVAL;
    int STACK_TARGET_BRIGHTNESS;

    // backgroundMap is a structure used to keep track of the average brightness of each pixel in the frame. This is subtracted from stacked image to remove the sky background and hot pixels
    // A histogram is constructed of the brightnesses of each pixel in successive groups of frames.
    int backgroundMapUseEveryNthStack;
    /* Add every Nth stacked group of frames of histogram. Increase this to reduce CPU load */
    int backgroundMapUseNImages;
    /* Stack this many groups of frames before generating a sky brightness map from histograms. */
    int backgroundMapReductionCycles; /* Reducing histograms to brightness map is time consuming, so we'll miss frames if we do it all at once. Do it in this many chunks after successive frames. */

    // Video parameters
    void *videoHandle;
    int width, height;
    const unsigned char *mask;
    const char *label;

    int (*fetchFrame)(void *, unsigned char *, double *);

    float fps;
    int frameSize;
    const char *obstoryId;

    double utc;
    int triggeringAllowed;
    double noiseLevel;

    // Trigger buffers. These are used to store 1 second of video for comparison with the next
    int buffNGroups;
    int buffGroupBytes;
    int buffNFrames;
    int bufflen;
    unsigned char *buffer;
    int *stack[256];
    int triggerPrefixNGroups;
    int triggerSuffixNGroups;

    // Timelapse buffers
    double timelapseUTCStart;
    int framesTimelapse;
    int *stackT;

    // Background maps are used for background subtraction. Maps A and B are used alternately and contain the background value of each pixel.
    unsigned char *backgroundMap;
    int *backgroundWorkspace;

    // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
    int *pastTriggerMap;

    // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
    int Nblocks;
    int *triggerMap;
    int *triggerBlock_N, *triggerBlock_top, *triggerBlock_bot, *triggerBlock_sumx, *triggerBlock_sumy, *triggerBlock_suml, *triggerBlock_redirect;
    unsigned char *triggerRGB;

    int groupNum; // Flag for whether we're feeding images into stackA or stackB
    int backgroundCount; // Count how many frames we've fed into the brightness histograms in backgroundWorkspace
    int timelapseCount; // Count how many frames have been stacked into the timelapse buffer (stackT)
    int frameCounter;
    int runInCountdown; // Let the camera run for a period before triggering, as it takes this long to make first background map

    int triggerThrottlePeriod; // Reset trigger throttle counter after this many frame groups have been processed
    int triggerThrottleTimer;
    int triggerThrottleCounter;

    event eventList[MAX_EVENTS];
    videoOutput videoOutputs[MAX_EVENTS];
} observeStatus;

char *fNameGenerate(char *output, const char *obstoryId, double utc, char *tag, const char *dirname, const char *label);

int readFrameGroup(observeStatus *os, unsigned char *buffer, int *stack1, int *stack2);

int observe(void *videoHandle, const char *obstoryId, const int utcoffset, const int tstart, const int tstop,
            const int width, const int height, const double fps, const char *label, const unsigned char *mask,
            const int Nchannels, const int STACK_COMPARISON_INTERVAL, const int TRIGGER_PREFIX_TIME,
            const int TRIGGER_SUFFIX_TIME, const int TRIGGER_FRAMEGROUP, const int TRIGGER_MAXRECORDLEN,
            const int TRIGGER_THROTTLE_PERIOD, const int TRIGGER_THROTTLE_MAXEVT, const int TIMELAPSE_EXPOSURE,
            const int TIMELAPSE_INTERVAL, const int STACK_TARGET_BRIGHTNESS,
            const int backgroundMapUseEveryNthStack, const int backgroundMapUseNImages, const int backgroundMapReductionCycles,
            int (*fetchFrame)(void *, unsigned char *, double *), int (*rewindVideo)(void *, double *));

void registerTrigger(observeStatus *os, const int blockId, const int xpos, const int ypos, const int npixels,
                     const int amplitude, const int *image1, const int *image2, const int coAddedFrames);

void registerTriggerEnds(observeStatus *os);

#endif

