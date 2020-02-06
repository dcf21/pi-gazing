// rawvid2frames.c
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

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

// Convert a raw video file into a sequence of frames in PNG format.

// Due to the tight constraints on data processing when analysing video in real time, we dump video to disk in
// uncompressed format. This converter is used for diagnostic purposes to view video frames as PNG files.

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include "argparse/argparse.h"
#include "png/image.h"
#include "utils/error.h"
#include "vidtools/color.h"

#include "settings.h"

static const char *const usage[] = {
        "rawvid2frames [options] [[--] args]",
        "rawvid2frames [options]",
        NULL,
};

//! Convert a raw video file into a sequence of frames in PNG format.
//! Due to the tight constraints on data processing when analysing video in real time, we dump video to disk in
//! uncompressed format. This converter is used for diagnostic purposes to view video frames as PNG files.
//! \param argc Command-line arguments
//! \param argv Command-line arguments
//! \return None

int main(int argc, const char *argv[]) {
    int i;

    const char *input_filename = "\0";
    const char *output_filename = "\0";

    struct argparse_option options[] = {
            OPT_HELP(),
            OPT_GROUP("Basic options"),
            OPT_STRING('i', "input", &input_filename, "input filename"),
            OPT_STRING('o', "output", &output_filename, "output filename"),
            OPT_END(),
    };

    struct argparse argparse;
    argparse_init(&argparse, options, usage, 0);
    argparse_describe(&argparse,
                      "\nConvert raw video files into frames in PNG format.",
                      "\n");
    argc = argparse_parse(&argparse, argc, argv);

    if (argc != 0) {
        int i;
        for (i = 0; i < argc; i++) {
            printf("Error: unparsed argument <%s>\n", *(argv + i));
        }
        logging_fatal(__FILE__, __LINE__, "Unparsed arguments");
    }

    FILE *infile;
    if ((infile = fopen(input_filename, "rb")) == NULL) {
        sprintf(temp_err_string, "ERROR: Cannot open output raw video file %s.\n", input_filename);
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    int size, width, height;
    i = fread(&size, sizeof(int), 1, infile);
    i = fread(&width, sizeof(int), 1, infile);
    i = fread(&height, sizeof(int), 1, infile);

    size -= 3 * sizeof(int);
    unsigned char *video_raw = malloc(size);
    if (video_raw == NULL) {
        sprintf(temp_err_string, "ERROR: malloc fail");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }
    i = fread(video_raw, 1, size, infile);
    fclose(infile);

    const int frame_size = width * height * 3 / 2;
    const int frame_count = size / frame_size;

    image_ptr output_image;
    image_alloc(&output_image, width, height);
    for (i = 0; i < width * height; i++) output_image.data_w[i] = 1;

    long l = 0;
    unsigned char *tmp_rgb = malloc(frame_size * 3);

    for (i = 0; i < frame_count; i++) {
        int x, y, p = 0;
        Pyuv420torgb(video_raw + l, video_raw + l + frame_size, video_raw + l + frame_size * 5 / 4,
                     tmp_rgb, tmp_rgb + frame_size,
                     tmp_rgb + frame_size * 2, width, height);
        for (y = 0; y < height; y++)
            for (x = 0; x < width; x++) {
                output_image.data_red[l] = tmp_rgb[p + frame_size * 0];
                output_image.data_grn[l] = tmp_rgb[p + frame_size * 1];
                output_image.data_blu[l] = tmp_rgb[p + frame_size * 2];
                p++;
            }
        l += frame_size * 3 / 2;
        char fname[FNAME_LENGTH];
        sprintf(fname, "%s%06d.png", output_filename, i);
        image_deweight(&output_image);
        image_put(fname, output_image, GREYSCALE_IMAGING);
    }
    image_dealloc(&output_image);
    free(video_raw);
    free(tmp_rgb);
    return 0;
}
