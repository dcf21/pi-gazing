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

#include "str_constants.h"
#include "settings.h"
#include "settings_webcam.h"

#define background_map_use_every_nth_stack     1
#define background_map_use_n_images         100

static const char *const usage[] = {
    "makeBackgroundMap [options] [[--] args]",
    "makeBackgroundMap [options]",
    NULL,
};

int main(int argc, const char *argv[]) {
    char line[FNAME_LENGTH] = "\0";
    const char *output_filename = "\0";

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
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    struct video_info *video_in;

    const char *video_device = VIDEO_DEV;
    float fps = nearest_multiple(VIDEO_FPS, 1);       // Requested frame rate
    int format = V4L2_PIX_FMT_YUYV;
    int grab_method = 1;
    int query_formats = 0;
    const char *stub = output_filename;

    char rgb_filename[FNAME_LENGTH], png_filename[FNAME_LENGTH];
    sprintf(rgb_filename, "%s.rgb", stub);
    sprintf(png_filename, "%s.png", stub);

    video_in = (struct video_info *) calloc(1, sizeof(struct video_info));

    if (query_formats) {
        check_videoIn(video_in, (char *) video_device);
        free(video_in);
        exit(1);
    }

    if (init_videoIn(video_in, (char *) video_device, VIDEO_WIDTH, VIDEO_HEIGHT, fps, format, grab_method) < 0)
        exit(1);
    const int width = video_in->width;
    const int height = video_in->height;
    const int frame_size = width * height;

    initLut();

    int utc_start = time(NULL);
    if (DEBUG) {
        sprintf(line, "Commencing makeBackgroundMap at %s.", friendly_time_string(utc_start));
        logging_info(line);
    }

    unsigned char *tmpc = malloc(frame_size * 1.5);
    if (!tmpc) {
        sprintf(temp_err_string, "ERROR: malloc fail in makeBackgroundMap.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }
    int *tmp_int = malloc(frame_size * 3 * sizeof(int));
    if (!tmp_int) {
        sprintf(temp_err_string, "ERROR: malloc fail in makeBackgroundMap.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int *background_workspace = calloc(1, frame_size * 3 * 256 * sizeof(int));
    unsigned char *background_map = calloc(1, 3 * frame_size);
    if ((!background_workspace) || (!background_map)) {
        sprintf(temp_err_string, "ERROR: malloc fail in makeBackgroundMap.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int f, i;

    const int total_required_stacks = background_map_use_every_nth_stack * background_map_use_n_images;
    for (f = 0; f < total_required_stacks; f++) {
        const int frame_count = 12; // Stack 12 frames
        int j;
        memset(tmp_int, 0, 3 * frame_size * sizeof(int));

        // Make a stack of frame_count frames
        for (j = 0; j < frame_count; j++) {
            if (uvcGrab(video_in) < 0) {
                printf("Error grabbing\n");
                break;
            }
            Pyuv422torgbstack(video_in->frame_buffer, tmp_int, tmp_int + frame_size, tmp_int + frame_size * 2,
                    video_in->width, video_in->height, VIDEO_UPSIDE_DOWN);
        }

        if ((f % background_map_use_every_nth_stack) != 0) continue;

        // Add stacked image into background map
#pragma omp parallel for private(j)
        for (j = 0; j < CHANNEL_COUNT * frame_size; j++) {
            int d;
            int pixel_value = CLIP256(tmp_int[j] / frame_count);
            background_workspace[j * 256 + pixel_value]++;
        }
    }

    // Calculate background map
    background_calculate(width, height, CHANNEL_COUNT, 0, 1, background_workspace, background_map);
    dump_frame(width, height, CHANNEL_COUNT, background_map, rgb_filename);

    // Make a PNG version for diagnostic use
    image_ptr output_image;
    image_alloc(&output_image, width, height);

    for (i = 0; i < frame_size; i++) output_image.data_w[i] = 1;

    if (CHANNEL_COUNT >= 3) {
        for (i = 0; i < frame_size; i++) output_image.data_red[i] = background_map[i];
        for (i = 0; i < frame_size; i++) output_image.data_grn[i] = background_map[i + frame_size];
        for (i = 0; i < frame_size; i++) output_image.data_blu[i] = background_map[i + frame_size * 2];
    } else {
        for (i = 0; i < frame_size; i++) output_image.data_red[i] = background_map[i];
        for (i = 0; i < frame_size; i++) output_image.data_grn[i] = background_map[i];
        for (i = 0; i < frame_size; i++) output_image.data_blu[i] = background_map[i];
    }

    image_put(png_filename, output_image, GREYSCALE_IMAGING);

    // Clean up
    free(background_workspace);
    free(background_map);

    int utc_stop = time(NULL);
    if (DEBUG) {
        sprintf(line, "Finishing making background map at %s.", friendly_time_string(utc_stop));
        logging_info(line);
    }

    return 0;
}
