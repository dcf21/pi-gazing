// realtimeObserve.c
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
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>

#include "argparse/argparse.h"
#include "utils/asciiDouble.h"
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"
#include "utils/filledPoly.h"
#include "utils/julianDate.h"
#include "analyse/observe.h"

#include "str_constants.h"
#include "settings.h"
#include "settings_webcam.h"

static const char *const usage[] = {
    "realtimeObserve [options] [[--] args]",
    "realtimeObserve [options]",
    NULL,
};

extern char *analysisObstoryId;

int fetchFrame(void *videoHandle, unsigned char *tmpc, double *utc) {
    struct vdIn *videoIn = videoHandle;
    int status = uvcGrab(videoIn);
    if (status) return status;
    Pyuv422to420(videoIn->framebuffer, tmpc, videoIn->width, videoIn->height, videoIn->upsideDown);

    struct timespec spec;
    clock_gettime(CLOCK_REALTIME, &spec);
    *utc = spec.tv_sec + ((double) spec.tv_nsec) / 1e9;
    return 0;
}

int rewindVideo(void *videoHandle, double *utc) {
    return 0; // Can't rewind live video!
}

int main(int argc, const char *argv[]) {
    videoMetadata vmd;
    char mask_file[FNAME_LENGTH] = "\0";
    char obstory[FNAME_LENGTH] = "\0";
    char input_device[FNAME_LENGTH] = "\0";

    vmd.tstart = time(NULL);
    vmd.tstop = getFloat(argv[3], NULL);
    vmd.nframe = 0;
    vmd.obstoryId = obstory;
    vmd.videoDevice = input_device;
    vmd.width = 720;
    vmd.height = 480;
    vmd.fps = 24.71;
    vmd.maskFile = mask_file;
    vmd.lat = 52.2;
    vmd.lng = 0.12;
    vmd.flagGPS = 0;
    vmd.flagUpsideDown = 1;
    vmd.filename = "dummy.h264";

    struct argparse_option options[] = {
        OPT_HELP(),
        OPT_GROUP("Basic options"),
        OPT_STRING('o', "obsid", &obstory, "observatory id"),
        OPT_STRING('d', "device", &input_device, "input video device, e.g. /dev/video0"),
        OPT_STRING('m', "mask", &mask_file, "mask file"),
        OPT_FLOAT('s', "utc-stop", &vmd.tstop, "time stamp at which to end observing"),
        OPT_FLOAT('f', "fps", &vmd.fps, "frame count per second"),
        OPT_FLOAT('l', "latitude", &vmd.lat, "latitude of observatory"),
        OPT_FLOAT('L', "longitude", &vmd.lng, "longitude of observatory"),
        OPT_INTEGER('w', "width", &vmd.width, "frame width"),
        OPT_INTEGER('h', "height", &vmd.height, "frame height"),
        OPT_INTEGER('g', "flag-gps", &vmd.flagGPS, "boolean flag indicating whether position determined by GPS"),
        OPT_INTEGER('u', "flag-upside-down", &vmd.flagUpsideDown, "boolean flag indicating whether the camera is upside down"),
        OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
    "\nObserve and analyse a video stream in real time.",
    "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    const int backgroundMapUseEveryNthStack = 1, backgroundMapUseNImages = 3600, backgroundMapReductionCycles = 32;

    struct vdIn *videoIn;

    const char *videodevice = vmd.videoDevice;
    const float fps = nearestMultiple(vmd.fps, 1); // Requested frame rate
    const int format = V4L2_PIX_FMT_YUYV;
    const int grabmethod = 1;
    const int queryformats = 0;
    char *avifilename = "/tmp/foo";

    videoIn = (struct vdIn *) calloc(1, sizeof(struct vdIn));

    if (queryformats) {
        check_videoIn(videoIn, (char *) videodevice);
        free(videoIn);
        exit(1);
    }

    initLut();

    // Fetch the dimensions of the video stream as returned by V4L (which may differ from what we requested)
    if (init_videoIn(videoIn, (char *) videodevice, vmd.width, vmd.height, fps, format, grabmethod, avifilename) <
        0)
        exit(1);
    const int width = videoIn->width;
    const int height = videoIn->height;
    vmd.width = width;
    vmd.height = height;
    //writeRawVidMetaData(vmd);
    videoIn->upsideDown = vmd.flagUpsideDown;

    unsigned char *mask = malloc((size_t)(width * height));
    FILE *maskfile = fopen(vmd.maskFile, "r");
    if (!maskfile) { logging_fatal(__FILE__, __LINE__, "mask file could not be opened"); }
    fillPolygonsFromFile(maskfile, mask, width, height);
    fclose(maskfile);

    observe((void *) videoIn, vmd.obstoryId, 0, vmd.tstart, vmd.tstop, width, height, vmd.fps, "live", mask,
            Nchannels, STACK_COMPARISON_INTERVAL, TRIGGER_PREFIX_TIME, TRIGGER_SUFFIX_TIME, TRIGGER_FRAMEGROUP,
            TRIGGER_MAXRECORDLEN, TRIGGER_THROTTLE_PERIOD, TRIGGER_THROTTLE_MAXEVT, TIMELAPSE_EXPOSURE,
            TIMELAPSE_INTERVAL, STACK_TARGET_BRIGHTNESS, backgroundMapUseEveryNthStack, backgroundMapUseNImages,
            backgroundMapReductionCycles, &fetchFrame, &rewindVideo);

    return 0;
}
