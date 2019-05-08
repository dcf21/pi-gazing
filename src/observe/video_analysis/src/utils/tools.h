// tools.h
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

#ifndef TOOLS_H
#define TOOLS_H 1

#include "vidtools/v4l2uvc.h"
#include "png/image.h"

#define CLIP256(X) ( d=X , ((d<0)?0: ((d>255)?255:d) ))

typedef struct videoMetadata {
    double tstart, tstop, fps, lng, lat;
    int width, height, flagGPS, flagUpsideDown, nframe;
    char *obstoryId, *videoDevice, *filename, *maskFile;
} video_metadata;

void write_raw_video_metadata(video_metadata v);

int nearest_multiple(double in, int factor);

void frame_invert(unsigned char *buffer, int len);

void *video_record(struct vdIn *video_in, double seconds);

void snapshot(struct vdIn *video_in, int frame_count, int zero, double exposure_compensation, char *filename, unsigned char *background_raw);

double estimate_noise_level(int width, int height, unsigned char *buffer, int frame_count);

void background_calculate(const int width, const int height, const int channels, const int reduction_cycle,
                          const int reduction_cycle_count, int *background_workspace, unsigned char *background_map);

int dump_frame(int width, int height, int channels, const unsigned char *buffer, char *filename);

int dump_frame_from_ints(int width, int height, int channels, const int *buffer, int frame_count, int target_brightness,
                         int *gain_out, char *filename);

int dump_frame_from_int_subtraction(int width, int height, int channels, const int *buffer, int frame_count,
                                    int target_brightness, int *gain_out,
                                    const unsigned char *buffer2, char *filename);

FILE *dump_video_init(int width, int height, const unsigned char *buffer1, int buffer1_frames,
                      const unsigned char *buffer2, int buffer2_frames, char *filename);

int dump_video_frame(int width, int height, const unsigned char *buffer1, int buffer1_frames,
                     const unsigned char *buffer2,
                     int buffer2_frames, FILE *out_file, int *frames_written);

#endif

