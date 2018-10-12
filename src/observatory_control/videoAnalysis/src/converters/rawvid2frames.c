// rawvid2frames.c
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
#include <unistd.h>
#include "utils/tools.h"
#include "png/image.h"
#include "utils/error.h"
#include "vidtools/color.h"

#include "settings.h"

int main(int argc, char *argv[]) {
    int i;

    if (argc != 3) {
        sprintf(temp_err_string,
                "ERROR: Need to specify raw video filename on commandline, followed by stub for output frames, e.g. 'rawvid2frames foo.raw frame'.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    char *rawFname = argv[1];
    char *frOut = argv[2];

    FILE *infile;
    if ((infile = fopen(rawFname, "rb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output raw video file %s.\n", rawFname);
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int size, width, height;
    i = fread(&size, sizeof(int), 1, infile);
    i = fread(&width, sizeof(int), 1, infile);
    i = fread(&height, sizeof(int), 1, infile);

    size -= 3 * sizeof(int);
    unsigned char *vidRaw = malloc(size);
    if (vidRaw == NULL) {
        sprintf(temp_err_string, "ERROR: malloc fail");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }
    i = fread(vidRaw, 1, size, infile);
    fclose(infile);

    const int frameSize = width * height * 3 / 2;
    const int nfr = size / frameSize;

    image_ptr OutputImage;
    image_alloc(&OutputImage, width, height);
    OutputImage.data_w = 1;

    long l = 0;
    unsigned char *tmprgb = malloc(frameSize * 3);

    for (i = 0; i < nfr; i++) {
        int x, y, p = 0;
        Pyuv420torgb(vidRaw + l, vidRaw + l + frameSize, vidRaw + l + frameSize * 5 / 4, tmprgb, tmprgb + frameSize,
                     tmprgb + frameSize * 2, width, height);
        for (y = 0; y < height; y++)
            for (x = 0; x < width; x++) {
                OutputImage.data_red[l] = tmprgb[p + frameSize * 0];
                OutputImage.data_grn[l] = tmprgb[p + frameSize * 1];
                OutputImage.data_blu[l] = tmprgb[p + frameSize * 2];
                p++;
            }
        l += frameSize * 3 / 2;
        char fname[FNAME_BUFFER];
        sprintf(fname, "%s%06d.png", frOut, i);
        image_deweight(&OutputImage);
        image_put(fname, OutputImage, ALLDATAMONO);
    }
    image_dealloc(&OutputImage);
    free(vidRaw);
    free(tmprgb);
    return 0;
}

