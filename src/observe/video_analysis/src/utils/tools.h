// tools.h
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

#ifndef TOOLS_H
#define TOOLS_H 1

#include "vidtools/v4l2uvc.h"
#include "png/image.h"

#define CLIP256(X) ( d=X , ((d<0)?0: ((d>255)?255:d) ))
#define CLIP65536(X) ( d=X , ((d<0)?0: ((d>65535)?65535:d) ))

typedef struct video_metadata {
    double utc_start, utc_stop, fps, lng, lat;
    int width, height, flag_gps, flag_upside_down, frame_count;
    const char *obstory_id, *video_device, *filename, *mask_file;
} video_metadata;

void write_raw_video_metadata(video_metadata v);

int nearest_multiple(double in, int factor);

void frame_invert(unsigned char *buffer, int len);

void *video_record(struct video_info *video_in, double seconds);

void snapshot(struct video_info *video_in, int frame_count, int zero, double exposure_compensation,
              const char *filename, const unsigned char *background_raw);

double estimate_noise_level(int width, int height, unsigned char *buffer, int frame_count, double *mean_level);

void background_calculate(const int width, const int height, const int channels, const int reduction_cycle,
                          const int reduction_cycle_count, const int *background_workspace,
                          int **background_maps,
                          const int background_buffer_count, const int background_buffer_current);

int dump_frame(int width, int height, int channels, const unsigned char *buffer, char *filename);

int dump_frame_from_ints(int width, int height, int channels, const int *buffer, int frame_count, int target_brightness,
                         double *gain_out, char *filename);

int dump_frame_from_int_subtraction(int width, int height, int channels, const int *buffer, int frame_count,
                                    int target_brightness, double *gain_out,
                                    const int *buffer2, char *filename);

void dump_video(int width, int height, const char *filename, const unsigned char *video_buffer,
                const int video_buffer_frames, const int write_position, const int write_end_position,
                const int max_frames);

#endif

