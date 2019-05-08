// snapshot.c
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

int main(int argc, char *argv[]) {
    if ((argc != 3) && (argc != 4)) {
        sprintf(temp_err_string,
                "ERROR: Need to specify output filename for snapshot and number of frames to stack on commandline, e.g. 'snapshot tmp.png 500'.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    char line[FNAME_LENGTH];
    int nfr = (int) getFloat(argv[2], NULL);
    if (nfr < 1) nfr = 1;

    int haveBackgroundSub = (argc == 4);
    int tstop;
    struct vdIn *videoIn;

    const char *videodevice = VIDEO_DEV;
    float fps = nearest_multiple(VIDEO_FPS, 1);       // Requested frame rate
    int format = V4L2_PIX_FMT_YUYV;
    int grabmethod = 1;
    int queryformats = 0;
    char *avifilename = "tmp.raw";

    videoIn = (struct vdIn *) calloc(1, sizeof(struct vdIn));

    if (queryformats) {
        check_videoIn(videoIn, (char *) videodevice);
        free(videoIn);
        exit(1);
    }

    if (init_videoIn(videoIn, (char *) videodevice, VIDEO_WIDTH, VIDEO_HEIGHT, fps, format, grabmethod, avifilename) <
        0)
        exit(1);
    const int width = videoIn->width;
    const int height = videoIn->height;

    initLut();

    unsigned char *backgroundRaw = NULL;

    if (haveBackgroundSub) {
        char *rawFname = argv[4];

        FILE *infile;
        if ((infile = fopen(rawFname, "rb")) == NULL) {
            sprintf(temp_err_string, "ERROR: Cannot open background filter image %s.\n", rawFname);
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }

        int size, backgroundwidth, backgroundheight;
        tstop = fread(&backgroundwidth, sizeof(int), 1, infile);
        tstop = fread(&backgroundheight, sizeof(int), 1, infile);

        if ((backgroundwidth != width) || (backgroundheight != height)) {
            sprintf(temp_err_string,
                    "ERROR: Background subtraction image has dimensions %d x %d. But frames from webcam have dimensions %d x %d. These must match.\n",
                    backgroundwidth, backgroundheight, width, height);
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }

        size = width * height;
        backgroundRaw = malloc(size);
        if (backgroundRaw == NULL) {
            sprintf(temp_err_string, "ERROR: malloc fail in snapshot.");
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }
        tstop = fread(backgroundRaw, 1, size, infile);
        fclose(infile);
    }

    int tstart = time(NULL);
    if (DEBUG) {
        sprintf(line, "Commencing snapshot at %s. Will stack %d frames.", friendly_time_string(tstart), nfr);
        logging_info(line);
    }

    snapshot(videoIn, nfr, 0, 1, argv[1], backgroundRaw);

    tstop = time(NULL);
    if (DEBUG) {
        sprintf(line, "Finishing snapshot at %s.", friendly_time_string(tstop));
        logging_info(line);
    }
    if (DEBUG) {
        sprintf(line, "Frame rate was %.1f fps.", (tstop - tstart) / ((double) nfr));
        logging_info(line);
    }

    return 0;
}
