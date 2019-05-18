// observe.h
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

#ifndef OBSERVE_H
#define OBSERVE_H 1

#define MAX_DETECTIONS 1024 /* Maximum detections of a single event; about 40 seconds of frames */
#define MAX_EVENTS        3 /* Number of simultaneous events */

#define MAX_TRIGGER_BLOCKS 65536

#include "str_constants.h"

typedef struct detection {
    int frame_count;
    int x, y, pixel_count, amplitude;
    double utc;
} detection;

typedef struct event {
    int active;
    int detection_count;
    double start_time;

    // When testTrigger detects a meteor, this string is set to a filename stub with time stamp of the time when the
    // camera triggered
    char filename_stub[FNAME_LENGTH];

    // Stacked image, averaged over whole duration of event
    int *stacked_image;

    // Maximum pixel values over whole duration of event
    int *max_stack;

    detection detections[MAX_DETECTIONS];
} event;

typedef struct videoOutput {
    int active;
    int width;
    int height;
    unsigned char *buffer1;
    int buffer1_frames;
    unsigned char *buffer2;
    int buffer2_frames;
    char fName[FNAME_LENGTH];
    FILE *file_handle;
    int frames_written;
} videoOutput;

typedef struct observeStatus {
    // Trigger settings
    int channel_count;
    int STACK_COMPARISON_INTERVAL;
    int TRIGGER_PREFIX_TIME;
    int TRIGGER_SUFFIX_TIME;
    int TRIGGER_FRAMEGROUP;
    int TRIGGER_MAXRECORDLEN;
    int TRIGGER_THROTTLE_PERIOD;
    int TRIGGER_THROTTLE_MAXEVT;
    int TIMELAPSE_EXPOSURE;
    int TIMELAPSE_INTERVAL;
    int STACK_TARGET_BRIGHTNESS;

    // backgroundMap is a structure used to keep track of the average brightness of each pixel in the frame.
    // This is subtracted from stacked image to remove the sky background and hot pixels
    // A histogram is constructed of the brightnesses of each pixel in successive groups of frames.
    int background_map_use_every_nth_stack;

    // Add every Nth stacked group of frames of histogram. Increase this to reduce CPU load.
    int background_map_use_n_images;

    // Stack this many groups of frames before generating a sky brightness map from histograms.
    // Reducing histograms to brightness map is time consuming, so we'll miss frames if we do it all at once.
    // Do it in this many chunks after successive frames.
    int background_map_reduction_cycles;

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

    // Trigger buffers. These are used to store 1 second of video for comparison with the next
    int buffer_group_count;
    int buffer_group_bytes;
    int buffer_frame_count;
    int buffer_length;
    unsigned char *buffer;
    int *stack[256];
    int trigger_prefix_group_count;
    int trigger_suffix_group_count;

    // Timelapse buffers
    double timelapse_utc_start;
    int frames_timelapse;
    int *stackT;

    // Background maps are used for background subtraction. Maps A and B are used alternately and contain the background value of each pixel.
    unsigned char *background_map;
    int *background_workspace;

    // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
    int *past_trigger_map;

    // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
    int block_count;
    int *trigger_map;
    int *trigger_block_count, *trigger_block_top, *trigger_block_bot;
    int *trigger_block_sumx, *trigger_block_sumy, *trigger_block_suml, *trigger_block_redirect;
    unsigned char *trigger_rgb;

    // Flag for whether we're feeding images into stackA or stackB
    int group_number;

    // Count how many frames we've fed into the brightness histograms in background_workspace
    int background_count;

    // Count how many frames have been stacked into the timelapse buffer (stackT)
    int timelapse_count;
    int frame_counter;

    // Let the camera run for a period before triggering, as it takes this long to make first background map
    int run_in_countdown;

    // Reset trigger throttle counter after this many frame groups have been processed
    int trigger_throttle_period;
    int trigger_throttle_timer;
    int trigger_throttle_counter;

    event event_list[MAX_EVENTS];
    videoOutput video_outputs[MAX_EVENTS];
} observe_status;

char *filename_generate(char *output, const char *obstory_id, double utc, char *tag, const char *dir_name,
                        const char *label);

int read_frame_group(observe_status *os, unsigned char *buffer, int *stack1, int *stack2);

int observe(void *video_handle, const char *obstory_id, const int utc_start, const int utc_stop,
            const int width, const int height, const double fps, const char *label, const unsigned char *mask,
            const int channel_count, const int STACK_COMPARISON_INTERVAL, const int TRIGGER_PREFIX_TIME,
            const int TRIGGER_SUFFIX_TIME, const int TRIGGER_FRAMEGROUP, const int TRIGGER_MAXRECORDLEN,
            const int TRIGGER_THROTTLE_PERIOD, const int TRIGGER_THROTTLE_MAXEVT, const int TIMELAPSE_EXPOSURE,
            const int TIMELAPSE_INTERVAL, const int STACK_TARGET_BRIGHTNESS,
            const int background_map_use_every_nth_stack, const int background_map_use_n_images, const int background_map_reduction_cycles,
            int (*fetch_frame)(void *, unsigned char *, double *), int (*rewind_video)(void *, double *));

void register_trigger(observe_status *os, const int block_id, const int x_pos, const int y_pos, const int pixel_count,
                      const int amplitude, const int *image1, const int *image2, const int coadded_frames);

void register_trigger_ends(observe_status *os);

#endif

