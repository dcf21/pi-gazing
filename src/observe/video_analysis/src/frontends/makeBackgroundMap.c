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

// For diagnostic purposes, observe the night sky for a few minutes, and produce a model of the sky background, with
// stars removed.

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

// Each pixel is 1.5 bytes in YUV420 stream
#define YUV420_BYTES_PER_PIXEL  3/2

static const char *const usage[] = {
        "makeBackgroundMap [options] [[--] args]",
        "makeBackgroundMap [options]",
        NULL,
};

//! For diagnostic purposes, observe the night sky for a few minutes, and produce a model of the sky background, with
//! stars removed.
//! \param argc Command-line arguments
//! \param argv Command-line arguments
//! \return None

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
    const int bytes_per_frame = frame_size * YUV420_BYTES_PER_PIXEL;

    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    initLut();

    int utc_start = time(NULL);
    if (DEBUG) {
        sprintf(line, "Commencing makeBackgroundMap at %s.", friendly_time_string(utc_start));
        logging_info(line);
    }

    unsigned char *buffer = malloc(bytes_per_frame);
    if (!buffer) {
        sprintf(temp_err_string, "ERROR: malloc fail in makeBackgroundMap.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int *background_workspace = calloc(1, frame_size * channel_count * 256 * sizeof(int));

    int **background_maps = malloc((BACKGROUND_MAP_SAMPLES + 1) * sizeof(int *));

    if ((!background_workspace) || (!background_maps)) {
        sprintf(temp_err_string, "ERROR: malloc fail in makeBackgroundMap.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    for (int i = 0; i <= BACKGROUND_MAP_SAMPLES; i++) {
        background_maps[i] = (int *)calloc(sizeof(int), frame_size * channel_count);
    }


    // If we're doing colour imaging, we need a buffer for turning YUV data into RGB pixels
    unsigned char *tmp_rgb = NULL;
    if (!GREYSCALE_IMAGING) {
        tmp_rgb = malloc(channel_count * frame_size);
    }

    int f, i;

    for (f = 0; f < BACKGROUND_MAP_FRAMES; f++) {

        // Fetch a frame
        if (uvcGrab(video_in) < 0) {
            printf("Error grabbing\n");
            break;
        }
        Pyuv422to420(video_in->frame_buffer, buffer, video_in->width, video_in->height, video_in->upside_down);

        if (GREYSCALE_IMAGING) {
            // If we're working in greyscale, we simply use the Y component of the YUV frame
            tmp_rgb = buffer;
        } else {
            // If we're working in colour, we need to convert frame to RGB
            Pyuv420torgb(buffer,
                         buffer + frame_size,
                         buffer + frame_size * 5 / 4,
                         tmp_rgb, tmp_rgb + frame_size, tmp_rgb + frame_size * 2,
                         width, height);
        }

#pragma omp parallel for private(i)
        for (i = 0; i < frame_size * channel_count; i++) {
            // Add the pixel values in this stack into the histogram in background_workspace
            background_workspace[i * 256 + tmp_rgb[i]]++;
        }
    }

    // Calculate background map
    background_calculate(width, height, channel_count, 0, 1,
                         background_workspace, background_maps,
                         1, 0);

    // Write it to a file
    dump_frame_from_ints(width, height, channel_count, background_maps[0], 256, 0, NULL, rgb_filename);

    // Make a PNG version for diagnostic use
    image_ptr output_image;
    image_alloc(&output_image, width, height);

    for (i = 0; i < frame_size; i++) output_image.data_w[i] = 1;

    if (channel_count >= 3) {
        for (i = 0; i < frame_size; i++) output_image.data_red[i] = background_maps[0][i];
        for (i = 0; i < frame_size; i++) output_image.data_grn[i] = background_maps[0][i + frame_size];
        for (i = 0; i < frame_size; i++) output_image.data_blu[i] = background_maps[0][i + frame_size * 2];
    } else {
        for (i = 0; i < frame_size; i++) output_image.data_red[i] = background_maps[0][i];
        for (i = 0; i < frame_size; i++) output_image.data_grn[i] = background_maps[0][i];
        for (i = 0; i < frame_size; i++) output_image.data_blu[i] = background_maps[0][i];
    }

    image_put(png_filename, output_image, GREYSCALE_IMAGING);

    // Clean up
    free(background_workspace);
    for (i = 0; i < BACKGROUND_MAP_SAMPLES; i++) free(background_maps[i]);
    free(background_maps);

    int utc_stop = time(NULL);
    if (DEBUG) {
        sprintf(line, "Finishing making background map at %s.", friendly_time_string(utc_stop));
        logging_info(line);
    }

    return 0;
}
