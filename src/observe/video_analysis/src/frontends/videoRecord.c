// video_record.c
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
#include <unistd.h>

#include "argparse/argparse.h"
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"

#include "str_constants.h"
#include "settings.h"
#include "settings_webcam.h"

static const char *const usage[] = {
    "videoRecord [options] [[--] args]",
    "videoRecord [options]",
    NULL,
};

int main(int argc, const char *argv[]) {
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
    "\nRecord a short video clip.",
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

    const char *videodevice = VIDEO_DEV;
    float fps = nearest_multiple(VIDEO_FPS, 1); // Requested frame rate
    int format = V4L2_PIX_FMT_YUYV;
    int grab_method = 1;
    int query_formats = 0;

    video_in = (struct video_info *) calloc(1, sizeof(struct video_info));

    if (query_formats) {
        check_videoIn(video_in, (char *) videodevice);
        free(video_in);
        exit(1);
    }

    if (init_videoIn(video_in, (char *) videodevice, VIDEO_WIDTH, VIDEO_HEIGHT, fps, format, grab_method) < 0)
        exit(1);

    initLut();

    void *vidRaw = video_record(video_in, 4);

    FILE *outfile;
    if ((outfile = fopen(output_filename, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW video file %s.\n", output_filename);
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    fwrite(vidRaw, 1, *(int *) vidRaw, outfile);
    fclose(outfile);
    free(vidRaw);

    return 0;
}
