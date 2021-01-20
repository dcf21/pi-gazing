// observe.h
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

#ifndef OBSERVE_H
#define OBSERVE_H 1

#define MAX_DETECTIONS 4096 /* Maximum detections of a single event; about 160 seconds of frames */
#define MAX_EVENTS        2 /* Number of simultaneous events */

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
    // int *stacked_image;

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

    int TRIGGER_THROTTLE_PERIOD;
    int TRIGGER_THROTTLE_MAXEVT;
    int TIMELAPSE_EXPOSURE;
    int TIMELAPSE_INTERVAL;
    int STACK_TARGET_BRIGHTNESS;

    // Video parameters
    void *video_handle;
    int width, height;

    // An array of Boolean pixels indicating which pixels contain sky (false) and which are obscured (true)
    const unsigned char *mask;

    // The label to associate with this observing run, e.g. live or nonlive
    const char *label;

    // The function we call to fetch a new video frame from the input source
    int (*fetch_frame)(void *, unsigned char *, double *);

    // The nominal FPS that we expect from this video input
    float fps;

    // The number of pixels in each frame, i.e. width * height
    int frame_size;

    // The name of this observatory, e.g. eddington0
    const char *obstory_id;

    // The unix time stamp associated with the frame we are currently analysing
    double utc;

    // Boolean indicating whether we have completed run in period and are allowed to trigger
    int triggering_allowed;

    // The standard deviation of the brightness of video pixels from one frame to the next; a measure of noise
    double noise_level;

    // The average brightness of the pixels in recent video frames
    double mean_level;

    // Video buffer. This is used to store a rolling spool of recent video
    int video_buffer_frames;
    int bytes_per_frame;
    int video_buffer_bytes;
    unsigned char *video_buffer;

    // The number of frames of video to include before a moving object appears
    int trigger_prefix_frame_count;

    // The number of frames of video to include after a moving object has disappeared
    int trigger_suffix_frame_count;

    // An object which has only been seen once must recur within this number of frames
    int trigger_suffix_initial_frame_count;

    // Time lapse buffers
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

    // Buffers used to create images used to produce diagnostic images of triggers
    unsigned char *difference_frame, *trigger_mask_frame, *trigger_map_frame;

    // Count how many frames we've fed into the brightness histograms in background_workspace
    int background_frame_count;

    // Which buffer are we feeding background models into?
    int background_buffer_current;

    // Count how many frames have been stacked into the timelapse buffer (stack_timelapse)
    int timelapse_frame_count;
    int frame_counter;

    // Let the camera run for a period before triggering, as it takes this long to make first background map
    // This counts down to zero. When it reaches zero, we start observing.
    int run_in_frame_countdown;

    // Reset trigger throttle counter after this many frame groups have been processed
    int trigger_throttle_timer;
    int trigger_throttle_counter;

    event event_list[MAX_EVENTS];
} observe_status;

int read_frame(observe_status *os, unsigned char *buffer, int *stack2);

int observe(void *video_handle, const char *obstory_id, const double utc_start, const double utc_stop,
            const int width, const int height, const double fps, const char *label, const unsigned char *mask,
            const int STACK_COMPARISON_INTERVAL, const int TRIGGER_PREFIX_TIME, const int TRIGGER_SUFFIX_TIME,
            const double TRIGGER_SUFFIX_TIME_INITIAL, const int TRIGGER_MIN_DETECTIONS,
            const double TRIGGER_MIN_PATH_LENGTH, const double TRIGGER_MAX_MOVEMENT_PER_FRAME,
            const double TRIGGER_MIN_SIGNIFICANCE, const double TRIGGER_MIN_SIGNIFICANCE_INITIAL,
            const int VIDEO_BUFFER_LEN, const int TRIGGER_THROTTLE_PERIOD, const int TRIGGER_THROTTLE_MAXEVT,
            const int TIMELAPSE_EXPOSURE, const int TIMELAPSE_INTERVAL, const int STACK_TARGET_BRIGHTNESS,
            const int BACKGROUND_MAP_FRAMES, const int BACKGROUND_MAP_SAMPLES,
            const int BACKGROUND_MAP_REDUCTION_CYCLES,
            int (*fetch_frame)(void *, unsigned char *, double *), int (*rewind_video)(void *, double *));

void observing_loop(observe_status *os, const double utc_stop,
                    const int BACKGROUND_MAP_FRAMES, const int BACKGROUND_MAP_SAMPLES,
                    const int BACKGROUND_MAP_REDUCTION_CYCLES, int (*rewind_video)(void *, double *));

void register_trigger(observe_status *os, const int block_id, const int x_pos, const int y_pos, const int pixel_count,
                      const int amplitude, const unsigned char *image1, const unsigned char *image2);

void register_trigger_ends(observe_status *os);

void moving_object_disappeared(observe_status *os, int trigger_index);

void consider_writing_video(observe_status *os);

#endif

