// makeBackgroundMap.c
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
#include <time.h>
#include <unistd.h>

#include "argparse/argparse.h"
#include "utils/asciiDouble.h"
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"

#include "settings.h"
#include "settings_webcam.h"

#define backgroundMapUseEveryNthStack     1
#define backgroundMapUseNImages         100

static const char *const usage[] = {
    "makeBackgroundMap [options] [[--] args]",
    "makeBackgroundMap [options]",
    NULL,
};

int main(int argc, const char *argv[]) {
    char line[FNAME_BUFFER];
    char output_filename[FNAME_BUFFER];

    struct argparse_option options[] = {
        OPT_HELP(),
        OPT_GROUP("Basic options"),
        OPT_STRING('o', "output", &output_filename, "output filename"),
        OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
    "\nMake a map of the sky background.",
    "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        gnom_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    struct vdIn *videoIn;

    const char *videodevice = VIDEO_DEV;
    float fps = nearestMultiple(VIDEO_FPS, 1);       // Requested frame rate
    int format = V4L2_PIX_FMT_YUYV;
    int grabmethod = 1;
    int queryformats = 0;
    char *stub = output_filename;

    char rawfname[FNAME_BUFFER], frOut[FNAME_BUFFER];
    sprintf(rawfname, "%s.rgb", stub);
    sprintf(frOut, "%s.png", stub);

    videoIn = (struct vdIn *) calloc(1, sizeof(struct vdIn));

    if (queryformats) {
        check_videoIn(videoIn, (char *) videodevice);
        free(videoIn);
        exit(1);
    }

    if (init_videoIn(videoIn, (char *) videodevice, VIDEO_WIDTH, VIDEO_HEIGHT, fps, format, grabmethod, rawfname) <
        0)
        exit(1);
    const int width = videoIn->width;
    const int height = videoIn->height;
    const int frameSize = width * height;

    initLut();

    int tstart = time(NULL);
    if (DEBUG) {
        sprintf(line, "Commencing makeBackgroundMap at %s.", friendlyTimestring(tstart));
        gnom_log(line);
    }

    unsigned char *tmpc = malloc(frameSize * 1.5);
    if (!tmpc) {
        sprintf(temp_err_string, "ERROR: malloc fail in makeBackgroundMap.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }
    int *tmpi = malloc(frameSize * 3 * sizeof(int));
    if (!tmpi) {
        sprintf(temp_err_string, "ERROR: malloc fail in makeBackgroundMap.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int *backgroundWorkspace = calloc(1, frameSize * 3 * 256 * sizeof(int));
    unsigned char *backgroundMap = calloc(1, 3 * frameSize);
    if ((!backgroundWorkspace) || (!backgroundMap)) {
        sprintf(temp_err_string, "ERROR: malloc fail in makeBackgroundMap.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int f, i;

    const int totalRequiredStacks = backgroundMapUseEveryNthStack * backgroundMapUseNImages;
    for (f = 0; f < totalRequiredStacks; f++) {
        const int nfr = 12; // Stack 12 frames
        int j;
        memset(tmpi, 0, 3 * frameSize * sizeof(int));

        // Make a stack of nfr frames
        for (j = 0; j < nfr; j++) {
            if (uvcGrab(videoIn) < 0) {
                printf("Error grabbing\n");
                break;
            }
            Pyuv422torgbstack(videoIn->framebuffer, tmpi, tmpi + frameSize, tmpi + frameSize * 2, videoIn->width,
                              videoIn->height, VIDEO_UPSIDE_DOWN);
        }

        if ((f % backgroundMapUseEveryNthStack) != 0) continue;

        // Add stacked image into background map
#pragma omp parallel for private(j)
        for (j = 0; j < Nchannels * frameSize; j++) {
            int d;
            int pixelVal = CLIP256(tmpi[j] / nfr);
            backgroundWorkspace[j * 256 + pixelVal]++;
        }
    }

    // Calculate background map
    backgroundCalculate(width, height, Nchannels, 0, 1, backgroundWorkspace, backgroundMap);
    dumpFrame(width, height, Nchannels, backgroundMap, rawfname);

    // Make a PNG version for diagnostic use
    image_ptr OutputImage;
    image_alloc(&OutputImage, width, height);

    for (i = 0; i < frameSize; i++) OutputImage.data_w[i] = 1;

    if (Nchannels >= 3) {
        for (i = 0; i < frameSize; i++) OutputImage.data_red[i] = backgroundMap[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_grn[i] = backgroundMap[i + frameSize];
        for (i = 0; i < frameSize; i++) OutputImage.data_blu[i] = backgroundMap[i + frameSize * 2];
    } else {
        for (i = 0; i < frameSize; i++) OutputImage.data_red[i] = backgroundMap[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_grn[i] = backgroundMap[i];
        for (i = 0; i < frameSize; i++) OutputImage.data_blu[i] = backgroundMap[i];
    }

    image_put(frOut, OutputImage, ALLDATAMONO);

    // Clean up
    free(backgroundWorkspace);
    free(backgroundMap);

    int tstop = time(NULL);
    if (DEBUG) {
        sprintf(line, "Finishing making background map at %s.", friendlyTimestring(tstop));
        gnom_log(line);
    }

    return 0;
}
