// observe_dslr.c
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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include <sys/stat.h>
#include "utils/asciiDouble.h"
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"
#include "utils/filledPoly.h"
#include "utils/julianDate.h"
#include "analyse/observe.h"

#include "jpeg/jpeg.h"

#include "settings.h"
#include "settings_dslr.h"

extern char *analysisObstoryId;

int utcoffset;

int fetchFrame(void *videoHandle, unsigned char *tmpc, double *utc) {
    const videoMetadata *vmd = videoHandle;
    const int frameSize = vmd->width * vmd->height;

    // Assuming we want to keep a regular number of FPS, when should we deliver this frame by?
    double utc_exit = (*utc) + 1.0 / vmd->fps;
    double utc_start = time(NULL) + utcoffset;
    if (utc_exit < utc_start) utc_exit = utc_start;

    // Use gphoto2 to capture an image
    int status = system(
            "cd /tmp ; gphoto2 --force-overwrite --capture-image-and-download --filename '/tmp/dslr_image.jpg'");
    if (status) { goto FAIL; }

    // Check image is new
    struct stat statbuf;
    if (stat("/tmp/dslr_image.jpg", &statbuf) == -1) goto FAIL;
    if (statbuf.st_mtime + utcoffset < utc_start) goto FAIL;

    // Load image
    jpeg_ptr img = jpeg_get("/tmp/dslr_image.jpg");

    // Work out mean brightness of red channel
    int i = 0, N = 0;
    double sum = 1;
    int nPixels = img.xsize * img.ysize;
    int skip = nPixels / 2000;
    for (i = 0; i < nPixels; i += skip) {
        sum += img.data_red[i];
        N++;
    }
    double brightness = sum / N;

    // Work out gain to apply to put sky brightness at 64, but don't allow gains outside 1-10.
    double gain = 64 / brightness;
    if (gain < 1) gain = 1;
    if (gain > 10) gain = 10;

    // Work out geometry for downsizing DSLR frame to the size we want
    double hscale = img.xsize / vmd->width;
    double vscale = img.ysize / vmd->height;
    int scale = floor((hscale < vscale) ? hscale : vscale);
    int marginx = (img.xsize - scale * vmd->width) / 2;
    int marginy = (img.ysize - scale * vmd->height) / 2;

    // Downsample image, and convert to YUV
    int x, y;
#pragma omp parallel for private(x,y)
    for (y = 0; y < vmd->height; y++)
        for (x = 0; x < vmd->width; x++) {
            int i, j;
            int r = 0, g = 0, b = 0;
            for (i = 0; i < scale; i++)
                for (j = 0; j < scale; j++) {
                    r += img.data_red[(i + marginx + x * scale) + (j + marginy + y * scale) * img.xsize];
                    g += img.data_grn[(i + marginx + x * scale) + (j + marginy + y * scale) * img.xsize];
                    b += img.data_blu[(i + marginx + x * scale) + (j + marginy + y * scale) * img.xsize];
                }
            r *= gain / scale / scale;
            g *= gain / scale / scale;
            b *= gain / scale / scale;

            unsigned char Y = RGB24_TO_Y(r, g, b);
            unsigned char V = YR_TO_V(r, Y);
            unsigned char U = YB_TO_U(b, Y);

            tmpc[x + y * vmd->width] = Y;
            tmpc[(x / 2) + (y / 2) * (vmd->width / 2) + frameSize] = U;
            tmpc[(x / 2) + (y / 2) * (vmd->width / 2) + frameSize * 5 / 4] = V;
        }

    // Clean up
    jpeg_dealloc(&img);
    goto EXIT;

    FAIL:
    memset(tmpc, 0, frameSize);
    memset(tmpc + frameSize, 128, frameSize / 2); // Black frame

    EXIT:
    while (time(NULL) + utcoffset < utc_exit) sleep(1);
    *utc = utc_exit;
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

    const int medianMapUseEveryNthStack = 1, medianMapUseNImages = 120, medianMapReductionCycles = 1;

    initLut();

    // Fetch the dimensions of the video stream as returned by V4L (which may differ from what we requested)
    unsigned char *mask = malloc(vmd.width * vmd.height);
    FILE *maskfile = fopen(vmd.maskFile, "r");
    if (!maskfile) { gnom_fatal(__FILE__, __LINE__, "mask file could not be opened"); }
    fillPolygonsFromFile(maskfile, mask, vmd.width, vmd.height);
    fclose(maskfile);

    observe((void *) &vmd, vmd.obstoryId, utcoffset, vmd.tstart, vmd.tstop, vmd.width, vmd.height, vmd.fps, "live",
            mask, Nchannels, STACK_COMPARISON_INTERVAL, TRIGGER_PREFIX_TIME, TRIGGER_SUFFIX_TIME, TRIGGER_FRAMEGROUP,
            TRIGGER_MAXRECORDLEN, TRIGGER_THROTTLE_PERIOD, TRIGGER_THROTTLE_MAXEVT, TIMELAPSE_EXPOSURE,
            TIMELAPSE_INTERVAL, STACK_GAIN_BGSUB, STACK_GAIN_NOBGSUB, medianMapUseEveryNthStack, medianMapUseNImages,
            medianMapReductionCycles, &fetchFrame, &rewindVideo);

    return 0;
}
