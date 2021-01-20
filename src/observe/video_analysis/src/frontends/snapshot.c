// snapshot.c
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2021 Dominic Ford.

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

// Record a single long-exposure image, by averaging together a large number of webcam frames.

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

static const char *const usage[] = {
        "snapshot [options] [[--] args]",
        "snapshot [options]",
        NULL,
};

//! Record a single long-exposure image, by averaging together a large number of webcam frames.
//! \param argc Command-line arguments
//! \param argv Command-line arguments
//! \return None

int main(int argc, const char *argv[]) {
    char line[FNAME_LENGTH];
    const char *output_filename = "\0";
    const char *background_filename = "\0";
    const char *video_device = "/dev/video0";
    int frame_count = 50;

    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('o', "output", &output_filename, "output filename"),
            OPT_INTEGER('f', "frames", &frame_count, "frames to stack"),
            OPT_STRING('d', "device", &video_device, "webcam device to use"),
            OPT_STRING('b', "background", &background_filename, "background to subtract"),
            OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
                      "\nTake a snapshot image.",
                      "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }


    if (frame_count < 1) frame_count = 1;

    int have_background = (strlen(background_filename) > 0);
    int utc_stop;
    struct video_info *video_in;

    float fps = nearest_multiple(VIDEO_FPS, 1);       // Requested frame rate
    int format = V4L2_PIX_FMT_YUYV;
    int grab_method = 1;
    int query_formats = 0;

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

    initLut();

    unsigned char *background_raw = NULL;

    if (have_background) {
        FILE *infile;
        if ((infile = fopen(background_filename, "rb")) == NULL) {
            snprintf(temp_err_string, FNAME_LENGTH,
                     "ERROR: Cannot open background filter image %s.\n", background_filename);
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }

        int size, background_width, background_height;
        utc_stop = fread(&background_width, sizeof(int), 1, infile);
        utc_stop = fread(&background_height, sizeof(int), 1, infile);

        if ((background_width != width) || (background_height != height)) {
            snprintf(temp_err_string, FNAME_LENGTH,
                     "ERROR: Background subtraction image has dimensions %d x %d. But frames from webcam have dimensions %d x %d. These must match.\n",
                     background_width, background_height, width, height);
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }

        size = width * height;
        background_raw = malloc(size);
        if (background_raw == NULL) {
            snprintf(temp_err_string, FNAME_LENGTH, "ERROR: malloc fail in snapshot.");
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }
        utc_stop = fread(background_raw, 1, size, infile);
        fclose(infile);
    }

    int utc_start = time(NULL);
    if (DEBUG) {
        snprintf(line, FNAME_LENGTH,
                 "Commencing snapshot at %s. Will stack %d frames.", friendly_time_string(utc_start), frame_count);
        logging_info(line);
    }

    snapshot(video_in, frame_count, 0, 1, output_filename, background_raw);

    utc_stop = time(NULL);
    if (DEBUG) {
        snprintf(line, FNAME_LENGTH, "Finishing snapshot at %s.", friendly_time_string(utc_stop));
        logging_info(line);
    }
    if (DEBUG) {
        snprintf(line, FNAME_LENGTH, "Frame rate was %.1f fps.", (utc_stop - utc_start) / ((double) frame_count));
        logging_info(line);
    }

    return 0;
}
