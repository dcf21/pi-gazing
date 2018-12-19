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
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include "utils/asciiDouble.h"
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"
#include "utils/filledPoly.h"
#include "utils/julianDate.h"
#include "analyse/observe.h"

#include "settings.h"
#include "settings_webcam.h"

extern char *analysisObstoryId;

int utcoffset;

int fetchFrame(void *videoHandle, unsigned char *tmpc, double *utc) {
    struct vdIn *videoIn = videoHandle;
    int status = uvcGrab(videoIn);
    if (status) return status;
    Pyuv422to420(videoIn->framebuffer, tmpc, videoIn->width, videoIn->height, videoIn->upsideDown);

    struct timespec spec;
    clock_gettime(CLOCK_REALTIME, &spec);
    *utc = spec.tv_sec + ((double) spec.tv_nsec) / 1e9 + utcoffset;
    return 0;
}

int rewindVideo(void *videoHandle, double *utc) {
    return 0; // Can't rewind live video!
}

int main(int argc, char *argv[]) {
    // Initialise video capture process
    if (argc != 15) {
        sprintf(temp_err_string,
                "ERROR: Command line syntax is:\n\n observe <UTC clock offset> <UTC start> <UTC stop> <obstoryId> <video device> <width> <height> <fps> <mask> <lat> <long> <flagGPS> <flagUpsideDown> <output filename>\n\ne.g.:\n\n observe 0 1428162067 1428165667 1 /dev/video0 720 480 24.71 mask.txt 52.2 0.12 0 1 output.h264\n");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    videoMetadata vmd;

    const double utcoffset = getFloat(argv[1], NULL);
    UTC_OFFSET = utcoffset;
    vmd.tstart = getFloat(argv[2], NULL);
    vmd.tstop = getFloat(argv[3], NULL);
    vmd.nframe = 0;
    vmd.obstoryId = argv[4];
    vmd.videoDevice = argv[5];
    vmd.width = (int) getFloat(argv[6], NULL);
    vmd.height = (int) getFloat(argv[7], NULL);
    vmd.fps = getFloat(argv[8], NULL);
    vmd.maskFile = argv[9];
    vmd.lat = getFloat(argv[10], NULL);
    vmd.lng = getFloat(argv[11], NULL);
    vmd.flagGPS = getFloat(argv[12], NULL) ? 1 : 0;
    vmd.flagUpsideDown = getFloat(argv[13], NULL) ? 1 : 0;
    vmd.filename = argv[14];

    const int medianMapUseEveryNthStack = 1, medianMapUseNImages = 3600, medianMapReductionCycles = 32;

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
    if (!maskfile) { gnom_fatal(__FILE__, __LINE__, "mask file could not be opened"); }
    fillPolygonsFromFile(maskfile, mask, width, height);
    fclose(maskfile);

    observe((void *) videoIn, vmd.obstoryId, utcoffset, vmd.tstart, vmd.tstop, width, height, vmd.fps, "live", mask,
            Nchannels, STACK_COMPARISON_INTERVAL, TRIGGER_PREFIX_TIME, TRIGGER_SUFFIX_TIME, TRIGGER_FRAMEGROUP,
            TRIGGER_MAXRECORDLEN, TRIGGER_THROTTLE_PERIOD, TRIGGER_THROTTLE_MAXEVT, TIMELAPSE_EXPOSURE,
            TIMELAPSE_INTERVAL, STACK_TARGET_BRIGHTNESS, medianMapUseEveryNthStack, medianMapUseNImages,
            medianMapReductionCycles, &fetchFrame, &rewindVideo);

    return 0;
}
