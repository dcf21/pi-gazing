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
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"

#include "str_constants.h"
#include "settings.h"
#include "settings_webcam.h"

static const char *const usage[] = {
    "video_record [options] [[--] args]",
    "video_record [options]",
    NULL,
};

int main(int argc, char *argv[]) {
    if (argc != 2) {
        sprintf(temp_err_string,
                "ERROR: Need to specify output filename for raw video dump on commandline, e.g. 'vidRec foo.raw'.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    struct vdIn *videoIn;

    const char *videodevice = VIDEO_DEV;
    float fps = nearest_multiple(VIDEO_FPS, 1); // Requested frame rate
    int format = V4L2_PIX_FMT_YUYV;
    int grabmethod = 1;
    int queryformats = 0;
    char *avifilename = argv[1];

    videoIn = (struct vdIn *) calloc(1, sizeof(struct vdIn));

    if (queryformats) {
        check_videoIn(videoIn, (char *) videodevice);
        free(videoIn);
        exit(1);
    }

    if (init_videoIn(videoIn, (char *) videodevice, VIDEO_WIDTH, VIDEO_HEIGHT, fps, format, grabmethod, avifilename) <
        0)
        exit(1);

    initLut();

    void *vidRaw = video_record(videoIn, 4);

    FILE *outfile;
    if ((outfile = fopen(avifilename, "wb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output RAW video file %s.\n", avifilename);
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    fwrite(vidRaw, 1, *(int *) vidRaw, outfile);
    fclose(outfile);
    free(vidRaw);

    return 0;
}
