// observe.h
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

#ifndef OBSERVE_H
#define OBSERVE_H 1

#define MAX_DETECTIONS 4096 /* Maximum detections of a single event; about 160 seconds of frames */
#define MAX_EVENTS        3 /* Number of simultaneous events */

#define MAX_TRIGGER_BLOCKS 65536

#include "str_constants.h"

typedef struct detection {
    int frame_count;
    int x, y, pixel_count, amplitude;
    double utc;
} detection;

typedef struct video_output {
    int active;
    int width;
    int height;
    int buffer_write_position;
    int buffer_end_position;
    char filename[FNAME_LENGTH];
    FILE *file_handle;
    int frames_written;
} video_output;

typedef struct event {
    // 0 = inactive; 1 = object is still visible; 2 = object no longer visible, but video still writing
    int active;
    int detection_count;

    // Unix time when this object was first seen
    double start_time;

    // When check_for_triggers detects a meteor, this string is set to a filename stub with time stamp of the time
    // when the camera triggered
    char filename_stub[FNAME_LENGTH];

    // Stacked image, averaged over whole duration of event
    int *stacked_image;

    // Maximum pixel values over whole duration of event
    int *max_stack;

    // Map of all pixels which trigger motion sensor over whole duration of event
    unsigned char *max_trigger;

    // A list of the coordinate positions within frames where this moving object has been seen
    detection detections[MAX_DETECTIONS];

    // A handle to the video output of this moving object
    video_output video_output;
} event;

typedef struct observeStatus {
    // Trigger settings
    int STACK_COMPARISON_INTERVAL;
    double TRIGGER_PREFIX_TIME;
    double TRIGGER_SUFFIX_TIME;

    double TRIGGER_SUFFIX_TIME_INITIAL;
    int TRIGGER_MIN_DETECTIONS;
    double TRIGGER_MIN_PATH_LENGTH;
    double TRIGGER_MAX_MOVEMENT_PER_FRAME;
    double TRIGGER_MIN_SIGNIFICANCE;
    double TRIGGER_MIN_SIGNIFICANCE_INITIAL;

    int TRIGGER_MAX_DURATION;
    int TRIGGER_THROTTLE_PERIOD;
    int TRIGGER_THROTTLE_MAXEVT;
    int TIMELAPSE_EXPOSURE;
    int TIMELAPSE_INTERVAL;
    int STACK_TARGET_BRIGHTNESS;

    // Video parameters
    void *video_handle;
    int width, height;
    const unsigned char *mask;
    const char *label;

    int (*fetch_frame)(void *, unsigned char *, double *);

    float fps;
    int frame_size;
    const char *obstory_id;

    double utc;
    int triggering_allowed;
    double noise_level;
    double mean_level;

    // Video buffer. This is used to store a rolling spool of recent video
    int video_buffer_frames;
    int bytes_per_frame;
    int video_buffer_bytes;
    unsigned char *video_buffer;

    int trigger_prefix_frame_count;
    int trigger_suffix_frame_count;
    int trigger_suffix_initial_frame_count;

    // Timelapse buffers
    double timelapse_utc_start;
    int frames_per_timelapse;
    int *stack_timelapse;

    // Background maps are used for background subtraction.
    int **background_maps;
    int *background_workspace;

    // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
    int *past_trigger_map;

    // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
    int block_count;
    int *trigger_map;
    int *trigger_block_count, *trigger_block_top, *trigger_block_bot;
    int *trigger_block_sumx, *trigger_block_sumy, *trigger_block_suml, *trigger_block_redirect;
    unsigned char *trigger_map_rgb;

    // Count how many frames we've fed into the brightness histograms in background_workspace
    int background_frame_count;

    // Which buffer are we feeding background models into?
    int background_buffer_current;

    // Count how many frames have been stacked into the timelapse buffer (stack_timelapse)
    int timelapse_frame_count;
    int frame_counter;

    // Let the camera run for a period before triggering, as it takes this long to make first background map
    int run_in_frame_countdown;

    // Reset trigger throttle counter after this many frame groups have been processed
    int trigger_throttle_timer;
    int trigger_throttle_counter;

    event event_list[MAX_EVENTS];
} observe_status;

char *filename_generate(char *output, const char *obstory_id, double utc, char *tag, const char *dir_name,
                        const char *label);

int read_frame(observe_status *os, unsigned char *buffer, int *stack2);

int observe(void *video_handle, const char *obstory_id, const double utc_start, const double utc_stop,
            const int width, const int height, const double fps, const char *label, const unsigned char *mask,
            const int STACK_COMPARISON_INTERVAL, const int TRIGGER_PREFIX_TIME, const int TRIGGER_SUFFIX_TIME,
            const double TRIGGER_SUFFIX_TIME_INITIAL, const int TRIGGER_MIN_DETECTIONS,
            const double TRIGGER_MIN_PATH_LENGTH, const double TRIGGER_MAX_MOVEMENT_PER_FRAME,
            const double TRIGGER_MIN_SIGNIFICANCE, const double TRIGGER_MIN_SIGNIFICANCE_INITIAL,
            const int VIDEO_BUFFER_LEN, const int TRIGGER_MAX_DURATION,
            const int TRIGGER_THROTTLE_PERIOD, const int TRIGGER_THROTTLE_MAXEVT,
            const int TIMELAPSE_EXPOSURE, const int TIMELAPSE_INTERVAL, const int STACK_TARGET_BRIGHTNESS,
            const int BACKGROUND_MAP_FRAMES, const int BACKGROUND_MAP_SAMPLES,
            const int BACKGROUND_MAP_REDUCTION_CYCLES,
            int (*fetch_frame)(void *, unsigned char *, double *), int (*rewind_video)(void *, double *));

void register_trigger(observe_status *os, const int block_id, const int x_pos, const int y_pos, const int pixel_count,
                      const int amplitude, const unsigned char *image1, const unsigned char *image2);

void register_trigger_ends(observe_status *os);

#endif

