// observe.c
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

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include "str_constants.h"
#include "analyse/observe.h"
#include "analyse/trigger.h"
#include "utils/asciiDouble.h"
#include "utils/tools.h"
#include "utils/error.h"
#include "utils/julianDate.h"
#include "vidtools/color.h"

#include "settings.h"

#define YUV420  3/2 /* Each pixel is 1.5 bytes in YUV420 stream */

// Generate a filename stub with a timestamp
char *fNameGenerate(char *output, const char *obstoryId, double utc, char *tag, const char *dirname,
                    const char *label) {
    char path[FNAME_LENGTH];
    const double JD = utc / 86400.0 + 2440587.5;
    int year, month, day, hour, min, status;
    double sec;
    invJulianDay(JD - 0.5, &year, &month, &day, &hour, &min, &sec, &status,
                 output); // Subtract 0.5 from Julian Day as we want days to start at noon, not midnight

    sprintf(path, "%s/%s_%s", OUTPUT_PATH, dirname, label);
    status = mkdir(path, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    if (status && (errno != EEXIST)) {
        sprintf(temp_err_string, "ERROR: Could not create directory <%s>. Returned error code %d. errno %d. %s.", path,
                status, errno, strerror(errno));
        gnom_log(temp_err_string);
    }

    const int i = (int)strlen(path);
    sprintf(path + i, "/%04d%02d%02d", year, month, day);
    status = mkdir(path, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    if (status && (errno != EEXIST)) {
        sprintf(temp_err_string, "ERROR: Could not create directory <%s>. Returned error code %d. errno %d. %s.", path,
                status, errno, strerror(errno));
        gnom_log(temp_err_string);
    }

    invJulianDay(JD, &year, &month, &day, &hour, &min, &sec, &status, output);
    sprintf(output, "%s/%04d%02d%02d%02d%02d%02d_%s_%s", path, year, month, day, hour, min, (int) sec, obstoryId, tag);
    return output;
}

// Record metadata to accompany a file. fname must be writable.
void writeMetaData(char *fname, char *itemTypes, ...) {
    // Change file extension to .txt
    int flen = (int)strlen(fname);
    int i = flen - 1;
    while ((i > 0) && (fname[i] != '.')) i--;
    sprintf(fname + i, ".txt");

    // Write metadata
    FILE *f = fopen(fname, "w");
    if (!f) return;
    va_list ap;
    va_start(ap, itemTypes);
    for (i = 0; itemTypes[i] != '\0'; i++) {
        char *x = va_arg(ap, char*);
        switch (itemTypes[i]) {
            case 's': {
                char *y = va_arg(ap, char*);
                fprintf(f, "%s %s\n", x, y);
                break;
            }
            case 'd': {
                double y = va_arg(ap, double);
                fprintf(f, "%s %.15e\n", x, y);
                break;
            }
            case 'i': {
                int y = va_arg(ap, int);
                fprintf(f, "%s %d\n", x, y);
                break;
            }
            default: {
                sprintf(temp_err_string, "ERROR: Unrecognised data type character '%c'.", itemTypes[i]);
                gnom_fatal(__FILE__, __LINE__, temp_err_string);
            }
        }
    }
    va_end(ap);
    fclose(f);
}

// Read enough video (1 second) to create the stacks used to test for triggers
int readFrameGroup(observeStatus *os, unsigned char *buffer, int *stack1, int *stack2) {
    int i, j;
    memset(stack1, 0,
           os->frameSize * os->Nchannels * sizeof(int)); // Stack1 is wiped prior to each call to this function

    unsigned char *tmprgb;
    if (!ALLDATAMONO) tmprgb = malloc((size_t)(os->Nchannels * os->frameSize));

    for (j = 0; j < os->TRIGGER_FRAMEGROUP; j++) {
        unsigned char *tmpc = buffer + j * os->frameSize * YUV420;
        if (ALLDATAMONO) tmprgb = tmpc;
        if ((*os->fetchFrame)(os->videoHandle, tmpc, &os->utc) != 0) {
            if (DEBUG) gnom_log("Error grabbing");
            return 1;
        }
        if (!ALLDATAMONO)
            Pyuv420torgb(tmpc, tmpc + os->frameSize, tmpc + os->frameSize * 5 / 4, tmprgb, tmprgb + os->frameSize,
                         tmprgb + os->frameSize * 2, os->width, os->height);
#pragma omp parallel for private(i)
        for (i = 0; i < os->frameSize * os->Nchannels; i++) stack1[i] += tmprgb[i];
    }

    if (stack2) {
#pragma omp parallel for private(i)
        for (i = 0; i < os->frameSize * os->Nchannels; i++)
            stack2[i] += stack1[i]; // Stack2 can stack output of many calls to this function
    }

    // Add the pixel values in this stack into the histogram in medianWorkspace
    const int includeInMedianHistograms = ((os->medianCount % os->medianMapUseEveryNthStack) == 0) &&
                                          (os->medianCount < os->medianMapUseNImages * os->medianMapUseEveryNthStack);
    if (includeInMedianHistograms) {
#pragma omp parallel for private(j)
        for (j = 0; j < os->frameSize * os->Nchannels; j++) {
            int d;
            int pixelVal = CLIP256(stack1[j] / os->TRIGGER_FRAMEGROUP);
            os->medianWorkspace[j * 256 + pixelVal]++;
        }
    }
    if (!ALLDATAMONO) free(tmprgb);
    return 0;
}

int observe(void *videoHandle, const char *obstoryId, const int utcoffset, const int tstart, const int tstop,
            const int width, const int height, const double fps, const char *label, const unsigned char *mask,
            const int Nchannels, const int STACK_COMPARISON_INTERVAL, const int TRIGGER_PREFIX_TIME,
            const int TRIGGER_SUFFIX_TIME, const int TRIGGER_FRAMEGROUP, const int TRIGGER_MAXRECORDLEN,
            const int TRIGGER_THROTTLE_PERIOD, const int TRIGGER_THROTTLE_MAXEVT, const int TIMELAPSE_EXPOSURE,
            const int TIMELAPSE_INTERVAL, const int STACK_TARGET_BRIGHTNESS,
            const int medianMapUseEveryNthStack, const int medianMapUseNImages, const int medianMapReductionCycles,
            int (*fetchFrame)(void *, unsigned char *, double *), int (*rewindVideo)(void *, double *)) {
    int i;
    char line[FNAME_LENGTH], line2[FNAME_LENGTH], line3[FNAME_LENGTH];

    if (DEBUG) {
        sprintf(line, "Starting observing run at %s; observing run will end at %s.",
                strStrip(friendlyTimestring(tstart), line2), strStrip(friendlyTimestring(tstop), line3));
        gnom_log(line);
    }

    observeStatus *os = calloc(1, sizeof(observeStatus));
    if (os == NULL) {
        sprintf(temp_err_string, "ERROR: malloc fail in observe.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
        exit(1);
    }

    os->videoHandle = videoHandle;
    os->width = width;
    os->height = height;
    os->label = label;
    os->obstoryId = obstoryId;
    os->mask = mask;
    os->fetchFrame = fetchFrame;
    os->fps = (float)fps;       // Requested frame rate
    os->frameSize = width * height;
    os->Nchannels = Nchannels;

    os->STACK_COMPARISON_INTERVAL = STACK_COMPARISON_INTERVAL;
    os->TRIGGER_PREFIX_TIME = TRIGGER_PREFIX_TIME;
    os->TRIGGER_SUFFIX_TIME = TRIGGER_SUFFIX_TIME;
    os->TRIGGER_FRAMEGROUP = TRIGGER_FRAMEGROUP;
    os->TRIGGER_MAXRECORDLEN = TRIGGER_MAXRECORDLEN;
    os->TRIGGER_THROTTLE_PERIOD = TRIGGER_THROTTLE_PERIOD;
    os->TRIGGER_THROTTLE_MAXEVT = TRIGGER_THROTTLE_MAXEVT;
    os->TIMELAPSE_EXPOSURE = TIMELAPSE_EXPOSURE;
    os->TIMELAPSE_INTERVAL = TIMELAPSE_INTERVAL;
    os->STACK_TARGET_BRIGHTNESS = STACK_TARGET_BRIGHTNESS;

    os->medianMapUseEveryNthStack = medianMapUseEveryNthStack;
    os->medianMapUseNImages = medianMapUseNImages;
    os->medianMapReductionCycles = medianMapReductionCycles;

    // Trigger buffers. These are used to store 1 second of video for comparison with the next
    os->buffNGroups = (int)(os->fps * os->TRIGGER_MAXRECORDLEN / os->TRIGGER_FRAMEGROUP);
    os->buffGroupBytes = os->TRIGGER_FRAMEGROUP * os->frameSize * YUV420;
    os->buffNFrames = os->buffNGroups * os->TRIGGER_FRAMEGROUP;
    os->bufflen = os->buffNGroups * os->buffGroupBytes;
    os->buffer = malloc((size_t)os->bufflen);
    for (i = 0; i <= os->STACK_COMPARISON_INTERVAL; i++) {
        os->stack[i] = malloc(os->frameSize * sizeof(int) *
                              os->Nchannels); // A stacked version of the current and preceding frame group; used to form a difference image
        if (!os->stack[i]) {
            sprintf(temp_err_string, "ERROR: malloc fail in observe.");
            gnom_fatal(__FILE__, __LINE__, temp_err_string);
        }
    }

    os->triggerPrefixNGroups = (int)(os->TRIGGER_PREFIX_TIME * os->fps / os->TRIGGER_FRAMEGROUP);
    os->triggerSuffixNGroups = (int)(os->TRIGGER_SUFFIX_TIME * os->fps / os->TRIGGER_FRAMEGROUP);

    // Timelapse buffers
    os->utc = 0;
    os->timelapseUTCStart = 1e40; // Store timelapse exposures at set intervals. This is UTC of next frame, but we don't start until we've done a run-in period
    os->framesTimelapse = (int)(os->fps * os->TIMELAPSE_EXPOSURE);
    os->stackT = malloc(os->frameSize * sizeof(int) * os->Nchannels);

    // Median maps are used for background subtraction. Maps A and B are used alternately and contain the median value of each pixel.
    // Holds the median value of each pixel, sampled over 255 stacked images
    os->medianMap = calloc(1, (size_t)(os->frameSize * os->Nchannels));

    // Workspace which counts the number of times any given pixel has a particular value
    os->medianWorkspace = calloc(1, (size_t)(os->frameSize * os->Nchannels * 256 * sizeof(int)));

    // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
    os->pastTriggerMap = calloc(1, os->frameSize * sizeof(int));

    // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
    os->triggerMap = calloc(1, os->frameSize *
                               sizeof(int)); // 2D array of ints used to mark out pixels which have brightened suspiciously.
    os->triggerRGB = calloc(1, (size_t)(os->frameSize * 3));

    os->triggerBlock_N = calloc(1, MAX_TRIGGER_BLOCKS *
                                   sizeof(int)); // Count of how many pixels are in each numbered connected block
    os->triggerBlock_top = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->triggerBlock_bot = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->triggerBlock_sumx = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->triggerBlock_sumy = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->triggerBlock_suml = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->triggerBlock_redirect = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));

    if ((!os->buffer) ||
        (!os->stackT) ||
        (!os->medianMap) || (!os->medianWorkspace) || (!os->pastTriggerMap) ||
        (!os->triggerMap) || (!os->triggerRGB) ||
        (!os->triggerBlock_N) || (!os->triggerBlock_top) || (!os->triggerBlock_bot) || (!os->triggerBlock_sumx) ||
        (!os->triggerBlock_sumy) || (!os->triggerBlock_suml) || (!os->triggerBlock_redirect)
            ) {
        sprintf(temp_err_string, "ERROR: malloc fail in observe.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    for (i = 0; i < MAX_EVENTS; i++) {
        os->eventList[i].stackedImage = malloc(os->frameSize * os->Nchannels * sizeof(int));
        os->eventList[i].maxStack = malloc(os->frameSize * os->Nchannels * sizeof(int));
        if ((!os->eventList[i].stackedImage) || (!os->eventList[i].maxStack)) {
            sprintf(temp_err_string, "ERROR: malloc fail in observe.");
            gnom_fatal(__FILE__, __LINE__, temp_err_string);
        }
    }

    for (i = 0; i < MAX_EVENTS; i++) {
        os->videoOutputs[i].active = 0;
    }

    os->groupNum = 0; // Flag for whether we're feeding images into stackA or stackB
    os->medianCount = 0; // Count how many frames we've fed into the brightness histograms in medianWorkspace
    os->timelapseCount = -1; // Count how many frames have been stacked into the timelapse buffer (stackT)
    os->frameCounter = 0;
    os->runInCountdown = 8 + os->medianMapReductionCycles + os->medianMapUseEveryNthStack *
                                                            os->medianMapUseNImages; // Let the camera run for a period before triggering, as it takes this long to make first median map
    os->noiseLevel = 128;

    // Trigger throttling
    os->triggerThrottleTimer = 0;
    os->triggerThrottleCounter = 0;

    // Reset trigger throttle counter after this many frame groups have been processed
    os->triggerThrottlePeriod = (int)(os->TRIGGER_THROTTLE_PERIOD * 60. * os->fps / os->TRIGGER_FRAMEGROUP);

    // Processing loop
    while (1) {
        int t = (int)(time(NULL) + utcoffset);
        if (t >= tstop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!

        // Once we've done initial run-in period, rewind the tape to the beginning if we can
        if (os->runInCountdown && !--os->runInCountdown) {
            if (DEBUG) {
                sprintf(line, "Run-in period completed.");
                gnom_log(line);
            }
            (*rewindVideo)(os->videoHandle, &os->utc);
            os->timelapseUTCStart = ceil(os->utc / 60) * 60 + 0.5; // Start making timelapse video
        }

        // Work out where we're going to read next second of video to. Either bufferA / bufferB, or the long buffer if we're recording
        unsigned char *bufferPos = os->buffer + (os->frameCounter % os->buffNGroups) * os->buffGroupBytes;

        // Once on each cycle through the video buffer, estimate the thermal noise of the camera
        if (bufferPos == os->buffer) os->noiseLevel = estimateNoiseLevel(os->width, os->height, os->buffer, 16);

        // Read the next second of video
        int status = readFrameGroup(os, bufferPos, os->stack[os->frameCounter % (os->STACK_COMPARISON_INTERVAL + 1)],
                                    (os->timelapseCount >= 0) ? os->stackT : NULL);
        if (status) break; // We've run out of video

        // If we've stacked enough frames since we last made a median map, make a new median map
        os->medianCount++;
        if (os->medianCount >= os->medianMapUseNImages * os->medianMapUseEveryNthStack) {
            const int reductionCycle = os->medianCount - os->medianMapUseNImages * os->medianMapUseEveryNthStack;
            medianCalculate(os->width, os->height, os->Nchannels, reductionCycle, os->medianMapReductionCycles,
                            os->medianWorkspace, os->medianMap);
            if (reductionCycle >= os->medianMapReductionCycles) {
                os->medianCount = 0;
                memset(os->medianWorkspace, 0, os->frameSize * os->Nchannels * 256 * sizeof(int));
            }
        }

        // Periodically, dump a stacked timelapse exposure lasting for <secondsTimelapseBuff> seconds
        if (os->timelapseCount >= 0) { os->timelapseCount++; }
        else if (os->utc > os->timelapseUTCStart) {
            memset(os->stackT, 0, os->frameSize * os->Nchannels * sizeof(int));
            os->timelapseCount = 0;
        }

        // If timelapse exposure is finished, dump it
        if ((os->timelapseCount >= os->framesTimelapse / os->TRIGGER_FRAMEGROUP) ||
            (os->utc > os->timelapseUTCStart + os->TIMELAPSE_INTERVAL - 1)) {
            const int Nframes = os->timelapseCount * os->TRIGGER_FRAMEGROUP;
            char fstub[FNAME_LENGTH], fname[FNAME_LENGTH];
            int gainFactor;
            fNameGenerate(fstub, os->obstoryId, os->timelapseUTCStart, "frame_", "timelapse_raw", os->label);
            sprintf(fname, "%s%s", fstub, "BS0.rgb");
            dumpFrameFromInts(os->width, os->height, os->Nchannels, os->stackT, Nframes, os->STACK_TARGET_BRIGHTNESS, &gainFactor, fname);
            writeMetaData(fname, "sddii",
                          "obstoryId", os->obstoryId,
                          "inputNoiseLevel", os->noiseLevel,
                          "stackNoiseLevel", os->noiseLevel / sqrt(Nframes) * gainFactor,
                          "gainFactor", gainFactor,
                          "stackedFrames", Nframes);
            sprintf(fname, "%s%s", fstub, "BS1.rgb");
            dumpFrameFromISub(os->width, os->height, os->Nchannels, os->stackT, Nframes, os->STACK_TARGET_BRIGHTNESS, &gainFactor,
                              os->medianMap, fname);
            writeMetaData(fname, "sddii",
                          "obstoryId", os->obstoryId,
                          "inputNoiseLevel", os->noiseLevel,
                          "stackNoiseLevel", os->noiseLevel / sqrt(Nframes) * gainFactor,
                          "gainFactor", gainFactor,
                          "stackedFrames", Nframes);
            if (floor(fmod(os->timelapseUTCStart, 900)) ==
                0) // Every 15 minutes, dump an image of the sky background map for diagnostic purposes
            {
                sprintf(fname, "%s%s", fstub, "skyBackground.rgb");
                dumpFrame(os->width, os->height, os->Nchannels, os->medianMap, fname);
                writeMetaData(fname, "sddi", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel,
                              "stackNoiseLevel", os->noiseLevel, "stackedFrames", ((int) os->medianMapUseNImages));
            }
            os->timelapseUTCStart += os->TIMELAPSE_INTERVAL;
            os->timelapseCount = -1;
        }

        // Update counters for trigger throttling
        os->triggerThrottleTimer++;
        const int triggerThrottleCycles = (int)(os->TRIGGER_THROTTLE_PERIOD * 60 * os->fps / os->TRIGGER_FRAMEGROUP);
        if (os->triggerThrottleTimer >= triggerThrottleCycles) {
            os->triggerThrottleTimer = 0;
            os->triggerThrottleCounter = 0;
        }

        // Test whether motion sensor has triggered
        os->triggeringAllowed = ((!os->runInCountdown) && (os->triggerThrottleCounter < os->TRIGGER_THROTTLE_MAXEVT));
        registerTriggerEnds(os);
        int *imageNew = os->stack[os->frameCounter % (os->STACK_COMPARISON_INTERVAL + 1)];
        int *imageOld = os->stack[(os->frameCounter + os->STACK_COMPARISON_INTERVAL) %
                                  (os->STACK_COMPARISON_INTERVAL + 1)];
        checkForTriggers(os, imageNew, imageOld, os->TRIGGER_FRAMEGROUP);

        os->frameCounter++;
        os->groupNum = !os->groupNum;
    }

    for (i = 0; i <= os->STACK_COMPARISON_INTERVAL; i++) free(os->stack[i]);
    for (i = 0; i < MAX_EVENTS; i++) {
        free(os->eventList[i].stackedImage);
        free(os->eventList[i].maxStack);
    }
    free(os->triggerMap);
    free(os->triggerBlock_N);
    free(os->triggerBlock_sumx);
    free(os->triggerBlock_sumy);
    free(os->triggerBlock_suml);
    free(os->triggerBlock_redirect);
    free(os->triggerRGB);
    free(os->buffer);
    free(os->stackT);
    free(os->medianMap);
    free(os->medianWorkspace);
    free(os->pastTriggerMap);
    free(os);
    return 0;
}

// Register a new trigger event
void registerTrigger(observeStatus *os, const int blockId, const int xpos, const int ypos, const int npixels,
                     const int amplitude, const int *image1, const int *image2, const int coAddedFrames) {
    int i, closestTrigger = -1, closestTriggerDist = 9999;
    if (!os->triggeringAllowed) return;

    // Cycle through objects we are tracking to find nearest one
    for (i = 0; i < MAX_EVENTS; i++)
        if (os->eventList[i].active) {
            const int N = os->eventList[i].Ndetections - 1;
            const int dist = (int)hypot(xpos - os->eventList[i].detections[N].x,
                                        ypos - os->eventList[i].detections[N].y);
            if (dist < closestTriggerDist) {
                closestTriggerDist = dist;
                closestTrigger = i;
            }
        }

    // If it's relatively close, assume this detection is of that object
    if (closestTriggerDist < 70) {
        const int i = closestTrigger;
        const int N = os->eventList[i].Ndetections - 1;
        if (os->eventList[i].detections[N].frameCount ==
            os->frameCounter) // Has this object already been seen in this frame?
        {
            // If so, take position of object as average position of multiple amplitude peaks
            detection *d = &os->eventList[i].detections[N];
            d->x = (d->x * d->amplitude + xpos * amplitude) / (d->amplitude + amplitude);
            d->y = (d->y * d->amplitude + ypos * amplitude) / (d->amplitude + amplitude);
            d->amplitude += amplitude;
            d->npixels += npixels;
        } else
        {
            // Otherwise add new detection to list
            os->eventList[i].Ndetections++;
            detection *d = &os->eventList[i].detections[N + 1];
            d->frameCount = os->frameCounter;
            d->x = xpos;
            d->y = ypos;
            d->utc = os->utc;
            d->npixels = npixels;
            d->amplitude = amplitude;
        }
        return;
    }

    // We have detected a new object. Create new event descriptor.
    if (DEBUG) {
        int year, month, day, hour, min, status;
        double sec;
        double JD = (os->utc / 86400.0) + 2440587.5;
        invJulianDay(JD, &year, &month, &day, &hour, &min, &sec, &status, temp_err_string);
        sprintf(temp_err_string, "Camera has triggered at (%04d/%02d/%02d %02d:%02d:%02d -- x=%d,y=%d).", year, month,
                day, hour, min, (int) sec, xpos, ypos);
        gnom_log(temp_err_string);
    }

    for (i = 0; i < MAX_EVENTS; i++) if (!os->eventList[i].active) break;
    if (i >= MAX_EVENTS) {
        gnom_log("Ignoring trigger; no event descriptors available.");
        return;
    } // No free event storage space

    // Colour in block of pixels which have triggered in schematic trigger map
    int k;
    for (k = 1; k <= os->Nblocks; k++) {
        int k2 = k;
        while (os->triggerBlock_redirect[k2] > 0) k2 = os->triggerBlock_redirect[k2];
        if (k2 == blockId) {
            unsigned char *triggerB = os->triggerRGB + os->frameSize * 2;
            int j;
#pragma omp parallel for private(j)
            for (j = 0; j < os->frameSize; j++) if (os->triggerMap[j] == k2) triggerB[j] *= 4;
        }
    }

    // Register event in events table
    os->eventList[i].active = 1;
    os->eventList[i].Ndetections = 1;
    detection *d = &os->eventList[i].detections[0];
    d->frameCount = os->frameCounter;
    d->x = xpos;
    d->y = ypos;
    d->utc = os->utc;
    d->npixels = npixels;
    d->amplitude = amplitude;

    char fname[FNAME_LENGTH];
    fNameGenerate(os->eventList[i].filenameStub, os->obstoryId, os->utc, "event", "triggers_raw", os->label);
    sprintf(fname, "%s%s", os->eventList[i].filenameStub, "_mapDifference.rgb");
    dumpFrame(os->width, os->height, 1, os->triggerRGB + 0 * os->frameSize, fname);
    writeMetaData(fname, "sddi", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel",
                  os->noiseLevel, "stackedFrames", 1);
    sprintf(fname, "%s%s", os->eventList[i].filenameStub, "_mapExcludedPixels.rgb");
    dumpFrame(os->width, os->height, 1, os->triggerRGB + 1 * os->frameSize, fname);
    writeMetaData(fname, "sddi", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel",
                  os->noiseLevel, "stackedFrames", 1);
    sprintf(fname, "%s%s", os->eventList[i].filenameStub, "_mapTrigger.rgb");
    dumpFrame(os->width, os->height, 1, os->triggerRGB + 2 * os->frameSize, fname);
    writeMetaData(fname, "sddi", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel",
                  os->noiseLevel, "stackedFrames", 1);

    sprintf(fname, "%s%s", os->eventList[i].filenameStub, "_triggerFrame.rgb");
    dumpFrameFromInts(os->width, os->height, os->Nchannels, image1, coAddedFrames, 0, NULL, fname);
    writeMetaData(fname, "sddi", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel",
                  os->noiseLevel / sqrt(coAddedFrames), "stackedFrames", coAddedFrames);
    sprintf(fname, "%s%s", os->eventList[i].filenameStub, "_previousFrame.rgb");
    dumpFrameFromInts(os->width, os->height, os->Nchannels, image2, coAddedFrames, 0, NULL, fname);
    writeMetaData(fname, "sddi", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel",
                  os->noiseLevel / sqrt(coAddedFrames), "stackedFrames", coAddedFrames);
    memcpy(os->eventList[i].stackedImage, image1, os->frameSize * os->Nchannels * sizeof(int));
    int j;
#pragma omp parallel for private(j)
    for (j = 0; j < os->frameSize * os->Nchannels; j++) os->eventList[i].maxStack[j] = image1[j];
}

// Check through list of events we are currently tracking.
// Weed out any which haven't been seen for a long time, or are exceeding maximum allowed recording time.
void registerTriggerEnds(observeStatus *os) {
    int i;
    int *stackbuf = os->stack[os->frameCounter % (os->STACK_COMPARISON_INTERVAL + 1)];
    for (i = 0; i < MAX_EVENTS; i++)
        if (os->eventList[i].active) {
            int j;
            const int N0 = 0;
            const int N1 = os->eventList[i].Ndetections / 2;
            const int N2 = os->eventList[i].Ndetections - 1;
#pragma omp parallel for private(j)
            for (j = 0; j < os->frameSize * os->Nchannels; j++) os->eventList[i].stackedImage[j] += stackbuf[j];
#pragma omp parallel for private(j)
            for (j = 0; j < os->frameSize * os->Nchannels; j++) {
                const int x = stackbuf[j];
                if (x > os->eventList[i].maxStack[j]) os->eventList[i].maxStack[j] = x;
            }

            if ((os->eventList[i].detections[N0].frameCount <=
                 (os->frameCounter - (os->buffNGroups - os->triggerPrefixNGroups))) ||
                // Event is exceeding TRIGGER_MAXRECORDLEN?
                (os->eventList[i].detections[N2].frameCount <= (os->frameCounter -
                                                                os->triggerSuffixNGroups))) // ... or event hasn't been seen for TRIGGER_SUFFIXTIME?
            {
                os->eventList[i].active = 0;

                // If event was seen in fewer than two frames, reject it
                if (os->eventList[i].Ndetections < 2) continue;

                // Work out duration of event
                double duration = os->eventList[i].detections[N2].utc - os->eventList[i].detections[N0].utc;
                double pixel_tracklen = hypot(os->eventList[i].detections[N0].x - os->eventList[i].detections[N2].x,
                                              os->eventList[i].detections[N0].y - os->eventList[i].detections[N2].y);

                if (pixel_tracklen < 4) continue; // Reject events that don't move much -- probably a twinkling star

                // Update counter for trigger rate throttling
                os->triggerThrottleCounter++;

                // Dump stacked images of entire duration of event
                int coAddedFrames =
                        (os->frameCounter - os->eventList[i].detections[0].frameCount) * os->TRIGGER_FRAMEGROUP;
                char fname[FNAME_LENGTH], pathJSON[LSTR_LENGTH], pathBezier[FNAME_LENGTH];
                sprintf(fname, "%s%s", os->eventList[i].filenameStub, "_timeAverage.rgb");
                dumpFrameFromInts(os->width, os->height, os->Nchannels, os->eventList[i].stackedImage, coAddedFrames, 0, NULL,
                                  fname);
                writeMetaData(fname, "sddi", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel,
                              "stackNoiseLevel", os->noiseLevel / sqrt(coAddedFrames), "stackedFrames", coAddedFrames);
                sprintf(fname, "%s%s", os->eventList[i].filenameStub, "_maxBrightness.rgb");
                dumpFrameFromInts(os->width, os->height, os->Nchannels, os->eventList[i].maxStack,
                                  os->TRIGGER_FRAMEGROUP, 0, NULL, fname);
                writeMetaData(fname, "sddi", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel,
                              "stackNoiseLevel", os->noiseLevel / sqrt(coAddedFrames), "stackedFrames", coAddedFrames);

                // Dump a video of the meteor from our video buffer
                int videoFrames =
                        (os->frameCounter - os->eventList[i].detections[N0].frameCount + os->triggerPrefixNGroups) *
                        os->TRIGGER_FRAMEGROUP;
                unsigned char *bufferPos = os->buffer + (os->frameCounter % os->buffNGroups) * os->buffGroupBytes;
                unsigned char *video1 = NULL;
                int video1frs = 0;
                unsigned char *video2 = bufferPos - videoFrames * os->frameSize * YUV420;
                int video2frs = videoFrames;

                // Video spans a buffer wrap-around, so need to include two chunks of video data
                if (video2 < os->buffer) {
                    video2frs = (bufferPos - os->buffer) / (os->frameSize * YUV420);
                    video1frs = videoFrames - video2frs;
                    video1 = video2 + os->bufflen;
                    video2 = os->buffer;
                }

                // Write path of event as JSON string
                int amplitudePeak = 0, amplitudeTimeIntegrated = 0;
                {
                    int j = 0, k = 0;
                    sprintf(pathJSON + k, "[");
                    k += strlen(pathJSON + k);
                    for (j = 0; j < os->eventList[i].Ndetections; j++) {
                        const detection *d = &os->eventList[i].detections[j];
                        sprintf(pathJSON + k, "%s[%d,%d,%d,%.3f]", j ? "," : "", d->x, d->y, d->amplitude, d->utc);
                        k += strlen(pathJSON + k);
                        amplitudeTimeIntegrated += d->amplitude;
                        if (d->amplitude > amplitudePeak) amplitudePeak = d->amplitude;
                    }
                    sprintf(pathJSON + k, "]");
                    k += strlen(pathJSON + k);
                }

                // Write path of event as a three-point Bezier curve
                {
                    int k = 0;
                    sprintf(pathBezier + k, "[");
                    k += strlen(pathBezier + k);
                    sprintf(pathBezier + k, "[%d,%d,%.3f],", os->eventList[i].detections[N0].x,
                            os->eventList[i].detections[N0].y, os->eventList[i].detections[N0].utc);
                    k += strlen(pathBezier + k);
                    sprintf(pathBezier + k, "[%d,%d,%.3f],", os->eventList[i].detections[N1].x,
                            os->eventList[i].detections[N1].y, os->eventList[i].detections[N1].utc);
                    k += strlen(pathBezier + k);
                    sprintf(pathBezier + k, "[%d,%d,%.3f]", os->eventList[i].detections[N2].x,
                            os->eventList[i].detections[N2].y, os->eventList[i].detections[N2].utc);
                    k += strlen(pathBezier + k);
                    sprintf(pathBezier + k, "]");
                    k += strlen(pathBezier + k);
                }

                // Start process of exporting video of this event
                {
                    int k = 0;
                    for (k = 0; k < MAX_EVENTS; k++) if (!os->videoOutputs[k].active) break;
                    if (k >= MAX_EVENTS) {
                        gnom_log("Ignoring video; already writing too many video files at once.");
                    } // No free event storage space
                    else {
                        sprintf(fname, "%s%s", os->eventList[i].filenameStub, ".vid");
                        os->videoOutputs[k].width = os->width;
                        os->videoOutputs[k].height = os->height;
                        os->videoOutputs[k].buffer1 = video1;
                        os->videoOutputs[k].buffer1frames = video1frs;
                        os->videoOutputs[k].buffer2 = video2;
                        os->videoOutputs[k].buffer2frames = video2frs;
                        strcpy(os->videoOutputs[k].fName, fname);
                        os->videoOutputs[k].framesWritten = 0;
                        os->videoOutputs[k].active = 1;

                        os->videoOutputs[k].fileHandle = dumpVideoInit(os->width, os->height, video1, video1frs,
                                                                       video2, video2frs, fname);

                        writeMetaData(fname, "sdsdiiis", "obstoryId", os->obstoryId, "inputNoiseLevel", os->noiseLevel,
                                      "path", pathJSON, "duration", duration,
                                      "detectionCount", os->eventList[i].Ndetections,
                                      "amplitudeTimeIntegrated", amplitudeTimeIntegrated,
                                      "amplitudePeak", amplitudePeak,
                                      "pathBezier", pathBezier
                        );
                    }
                }
            }
        }

    for (i = 0; i < MAX_EVENTS; i++)
        if (os->videoOutputs[i].active) {
            os->videoOutputs[i].active =
                    dumpVideoFrame(os->videoOutputs[i].width, os->videoOutputs[i].height,
                                   os->videoOutputs[i].buffer1, os->videoOutputs[i].buffer1frames,
                                   os->videoOutputs[i].buffer2, os->videoOutputs[i].buffer2frames,
                                   os->videoOutputs[i].fileHandle, &os->videoOutputs[i].framesWritten);
        }
}
