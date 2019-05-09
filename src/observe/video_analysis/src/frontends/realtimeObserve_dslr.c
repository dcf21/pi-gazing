// realtimeObserve_dslr.c
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
#include <sys/stat.h>

#include "argparse/argparse.h"
#include "utils/asciiDouble.h"
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"
#include "utils/filledPoly.h"
#include "utils/julianDate.h"
#include "analyse/observe.h"

#include "jpeg/jpeg.h"

#include "str_constants.h"
#include "settings.h"
#include "settings_dslr.h"

static const char *const usage[] = {
    "realtimeObserve_dslr [options] [[--] args]",
    "realtimeObserve_dslr [options]",
    NULL,
};

int fetch_frame(void *videoHandle, unsigned char *tmpc, double *utc) {
    const video_metadata *vmd = videoHandle;
    const int frameSize = vmd->width * vmd->height;

    // Assuming we want to keep a regular number of fps, when should we deliver this frame by?
    double utc_exit = (*utc) + 1.0 / vmd->fps;
    double utc_start = time(NULL);
    if (utc_exit < utc_start) utc_exit = utc_start;

    // Use gphoto2 to capture an image
    int status = system(
            "cd /tmp ; gphoto2 --force-overwrite --capture-image-and-download --filename '/tmp/dslr_image.jpg'");
    if (status) { goto FAIL; }

    // Check image is new
    struct stat statbuf;
    if (stat("/tmp/dslr_image.jpg", &statbuf) == -1) goto FAIL;
    if (statbuf.st_mtime < utc_start) goto FAIL;

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
    int scale = (int)floor((hscale < vscale) ? hscale : vscale);
    int marginx = (img.xsize - scale * vmd->width) / 2;
    int marginy = (img.ysize - scale * vmd->height) / 2;

    // Downsample image, and convert to YUV
    int x, y;
#pragma omp parallel for private(x,y)
    for (y = 0; y < vmd->height; y++)
        for (x = 0; x < vmd->width; x++) {
            int i2, j2;
            int r = 0, g = 0, b = 0;
            for (i2 = 0; i2 < scale; i2++)
                for (j2 = 0; j2 < scale; j2++) {
                    r += img.data_red[(i2 + marginx + x * scale) + (j2 + marginy + y * scale) * img.xsize];
                    g += img.data_grn[(i2 + marginx + x * scale) + (j2 + marginy + y * scale) * img.xsize];
                    b += img.data_blu[(i2 + marginx + x * scale) + (j2 + marginy + y * scale) * img.xsize];
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
    memset(tmpc, 0, (size_t)frameSize);
    memset(tmpc + frameSize, 128, (size_t)(frameSize / 2)); // Black frame

    EXIT:
    while (time(NULL) < utc_exit) sleep(1);
    *utc = utc_exit;
    return 0;
}

int rewind_video(void *video_handle, double *utc) {
    return 0; // Can't rewind live video!
}

int main(int argc, const char *argv[]) {
    video_metadata vmd;
    const char *mask_file = "\0";
    const char *obstory_id = "\0";
    const char *input_device = "\0";

    vmd.utc_start = time(NULL);
    vmd.utc_stop = 0;
    vmd.frame_count = 0;
    vmd.width = 720;
    vmd.height = 480;
    vmd.fps = 0.125;
    vmd.lat = 52.2;
    vmd.lng = 0.12;
    vmd.flag_gps = 0;
    vmd.flag_upside_down = 0;
    vmd.filename = "dummy.h264";

    struct argparse_option options[] = {
        OPT_HELP(),
        OPT_GROUP("Basic options"),
        OPT_STRING('o', "obsid", &obstory_id, "observatory id"),
        OPT_STRING('d', "device", &input_device, "input video device, e.g. /dev/video0"),
        OPT_STRING('m', "mask", &mask_file, "mask file"),
        OPT_FLOAT('s', "utc-stop", &vmd.utc_stop, "time stamp at which to end observing"),
        OPT_FLOAT('f', "fps", &vmd.fps, "frame count per second"),
        OPT_FLOAT('l', "latitude", &vmd.lat, "latitude of observatory"),
        OPT_FLOAT('L', "longitude", &vmd.lng, "longitude of observatory"),
        OPT_INTEGER('w', "width", &vmd.width, "frame width"),
        OPT_INTEGER('h', "height", &vmd.height, "frame height"),
        OPT_INTEGER('g', "flag-gps", &vmd.flag_gps, "boolean flag indicating whether position determined by GPS"),
        OPT_INTEGER('u', "flag-upside-down", &vmd.flag_upside_down, "boolean flag indicating whether the camera is upside down"),
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
    
    vmd.obstory_id = obstory_id;
    vmd.video_device = input_device;
    vmd.mask_file = mask_file;

    const int background_map_use_every_nth_stack = 1, background_map_use_n_images = 120, backgroundMapReductionCycles = 1;

    initLut();

    // Fetch the dimensions of the video stream as returned by V4L (which may differ from what we requested)
    unsigned char *mask = malloc((size_t)(vmd.width * vmd.height));
    FILE *maskfile = fopen(vmd.mask_file, "r");
    if (!maskfile) { logging_fatal(__FILE__, __LINE__, "mask file could not be opened"); }
    fill_polygons_from_file(maskfile, mask, vmd.width, vmd.height);
    fclose(maskfile);

    observe((void *) &vmd, vmd.obstory_id, vmd.utc_start, vmd.utc_stop, vmd.width, vmd.height, vmd.fps, "live",
            mask, CHANNEL_COUNT, STACK_COMPARISON_INTERVAL, TRIGGER_PREFIX_TIME, TRIGGER_SUFFIX_TIME, TRIGGER_FRAMEGROUP,
            TRIGGER_MAXRECORDLEN, TRIGGER_THROTTLE_PERIOD, TRIGGER_THROTTLE_MAXEVT, TIMELAPSE_EXPOSURE,
            TIMELAPSE_INTERVAL, STACK_TARGET_BRIGHTNESS, background_map_use_every_nth_stack, background_map_use_n_images,
            backgroundMapReductionCycles, &fetch_frame, &rewind_video);

    return 0;
}
