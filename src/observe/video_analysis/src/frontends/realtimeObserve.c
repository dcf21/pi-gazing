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

int fetch_frame(void *video_handle, unsigned char *tmpc, double *utc) {
    struct video_info *videoIn = video_handle;
    int status = uvcGrab(videoIn);
    if (status) return status;
    Pyuv422to420(videoIn->frame_buffer, tmpc, videoIn->width, videoIn->height, videoIn->upside_down);

    struct timespec spec;
    clock_gettime(CLOCK_REALTIME, &spec);
    *utc = spec.tv_sec + ((double) spec.tv_nsec) / 1e9;
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
    vmd.fps = 24.71;
    vmd.lat = 52.2;
    vmd.lng = 0.12;
    vmd.flag_gps = 0;
    vmd.flag_upside_down = 1;
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

    const int background_map_use_every_nth_stack = 1, background_map_use_n_images = 3600, backgroundMapReductionCycles = 32;

    struct video_info *video_in;

    const char *video_device = vmd.video_device;
    const float fps = nearest_multiple(vmd.fps, 1); // Requested frame rate
    const int format = V4L2_PIX_FMT_YUYV;
    const int grab_method = 1;
    const int query_formats = 0;

    video_in = (struct video_info *) calloc(1, sizeof(struct video_info));

    if (query_formats) {
        check_videoIn(video_in, video_device);
        free(video_in);
        exit(1);
    }

    initLut();

    // Fetch the dimensions of the video stream as returned by V4L (which may differ from what we requested)
    if (init_videoIn(video_in, video_device, vmd.width, vmd.height, fps, format, grab_method) < 0)
        exit(1);
    const int width = video_in->width;
    const int height = video_in->height;
    vmd.width = width;
    vmd.height = height;
    video_in->upside_down = vmd.flag_upside_down;

    unsigned char *mask = malloc((size_t)(width * height));
    FILE *maskfile = fopen(vmd.mask_file, "r");
    if (!maskfile) { logging_fatal(__FILE__, __LINE__, "mask file could not be opened"); }
    fill_polygons_from_file(maskfile, mask, width, height);
    fclose(maskfile);

    observe((void *) video_in, vmd.obstory_id, vmd.utc_start, vmd.utc_stop, width, height, vmd.fps, "live", mask,
            CHANNEL_COUNT, STACK_COMPARISON_INTERVAL, TRIGGER_PREFIX_TIME, TRIGGER_SUFFIX_TIME, TRIGGER_FRAMEGROUP,
            TRIGGER_MAXRECORDLEN, TRIGGER_THROTTLE_PERIOD, TRIGGER_THROTTLE_MAXEVT, TIMELAPSE_EXPOSURE,
            TIMELAPSE_INTERVAL, STACK_TARGET_BRIGHTNESS, background_map_use_every_nth_stack, background_map_use_n_images,
            backgroundMapReductionCycles, &fetch_frame, &rewind_video);

    return 0;
}
