// observe.c
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

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <errno.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include "str_constants.h"
#include "analyse/observe.h"
#include "analyse/trigger.h"
#include "utils/asciiDouble.h"
#include "utils/tools.h"
#include "utils/error.h"
#include "utils/julianDate.h"
#include "vidtools/color.h"

#include "settings.h"
#include "write_output.h"

// Each pixel is 1.5 bytes in YUV420 stream
#define YUV420_BYTES_PER_PIXEL  3/2


//! read_frame - Read a frame of input video. This is done by calling the function pointer os->fetch_frame, which
//! points to a function which may variously either capture a frame of live video from a webcam via the v4l2 library,
//! or else may return a frame of pre-recorded video from a file. The video frame is added into the stacked frame
//! <stack2>, which is used to create long-exposure images.
//! \param os - The settings for the current observing run.
//! \param buffer - The character array into which to write this frame as YUV420
//! \param stack2 - Int array of size (channels * width * height) into which we add frames to create long-exposure
//! images.
//! \return Zero on success; One if a frame could not be captured.

int read_frame(observe_status *os, unsigned char *buffer, int *stack2) {
    int i;

    static unsigned char *tmp_rgb = NULL;

    // Are we dealing with single-channel greyscale frames, or RGB video?
    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    // If we're doing colour imaging, we need a buffer for turning YUV data into RGB pixels
    if ((!GREYSCALE_IMAGING) && (tmp_rgb == NULL)) {
        tmp_rgb = malloc(channel_count * os->frame_size);
    }

    // Fetch a frame
    if ((*os->fetch_frame)(os->video_handle, buffer, &os->utc) != 0) {
        if (DEBUG) logging_info("Error grabbing");
        return 1;
    }

    if (GREYSCALE_IMAGING) {
        // If we're working in greyscale, we simply use the Y component of the YUV frame
        tmp_rgb = buffer;
    } else {
        // If we're working in colour, we need to convert frame to RGB
        Pyuv420torgb(buffer, buffer + os->frame_size, buffer + os->frame_size * 5 / 4,
                     tmp_rgb, tmp_rgb + os->frame_size, tmp_rgb + os->frame_size * 2,
                     os->width, os->height);
    }

#pragma omp parallel for private(i)
    for (i = 0; i < os->frame_size * channel_count; i++) {
        // Stack2 integrates frames into time lapse exposures
        if (stack2) stack2[i] += tmp_rgb[i];

        // Add the pixel values in this stack into the histogram in background_workspace
        os->background_workspace[i * 256 + tmp_rgb[i]]++;
    }

    // Done
    return 0;
}

//! observe - Main entry point for analysing a video stream for moving objects, including making periodic time-lapse
//! exposures.
//! \param video_handle Settings pertaining to the video stream. We pass this as an argument to the function pointer
//! <fetch_frame>, but otherwise we are agnostic to what data the structure might contain.
//! \param obstory_id The ID of the observatory from which this video stream is/was observed.
//! \param utc_start The unix time stamp of the start of the video
//! \param utc_stop The unix time stamp at which we need to exit the observing loop if we don't reach the end of the
//! video beforehand. Zero means we never exit.
//! \param width - The width of the video frames
//! \param height - The height of the video frames
//! \param fps - The frames per second count, used to calculate the time stamp of each frame in pre-recorded video
//! \param label - Either "live" or "non-live"; used in the filenames of file products.
//! \param mask - Array of (width * height) boolean chars, indicating whether pixels are inside the allowed area for
//! moving object detection (masking out trees, etc, which may blow in the wind).
//! \param STACK_COMPARISON_INTERVAL - When looking for moving objects, compare either frame with the frame which came
//! this number of frames earlier. Making this larger than one increases sensitivity to slow-moving objects.
//! \param TRIGGER_PREFIX_TIME - When we detect a moving object, include this number of seconds of preceding video.
//! \param TRIGGER_SUFFIX_TIME - When we detect a moving object, include this number of seconds of video after it
//! disappears. Also, this is the amount of time that an object is allowed to go undetected, before we stop looking for
//! further detections.
//! \param TRIGGER_SUFFIX_TIME_INITIAL - When we detect a moving object for the first time, it must be re-detected in a
//! subsequent frame within this time limit. Otherwise it is assumed to be noise.
//! \param TRIGGER_MIN_DETECTIONS - The minimum number of frames in which a moving object must appear to be detected.
//! \param TRIGGER_MIN_PATH_LENGTH - The minimum number of pixels that a moving object must move in order to be
//! trusted not to be a star.
//! \param TRIGGER_MAX_MOVEMENT_PER_FRAME - The maximum number of pixels that a moving object may move between
//! consecutive frames to be plausibly the same object.
//! \param TRIGGER_MIN_SIGNIFICANCE - The minimum number of standard deviations above the noise level that a
//! brightening must be to trigger the motion sensor. This is summed over all the pixels which brighten.
//! \param TRIGGER_MIN_SIGNIFICANCE_INITIAL - The minimum number of standard deviations above the noise level that a
//! brightening must be to trigger the motion sensor for the first time. This is summed over all the pixels which
//! brighten.
//! \param VIDEO_BUFFER_LEN - The number of seconds of video that we hold in a rolling buffer
//! \param TRIGGER_THROTTLE_PERIOD - The time period over which we throttle the allowed number of object detections.
//! \param TRIGGER_THROTTLE_MAXEVT - The maximum number of moving objects we can track in each
//! <TRIGGER_THROTTLE_PERIOD>.
//! \param TIMELAPSE_EXPOSURE - The length of each long-exposure time-lapse image.
//! \param TIMELAPSE_INTERVAL - The interval between long-exposure time-lapse images.
//! \param STACK_TARGET_BRIGHTNESS - The target mean brightness of the pixels in background-subtracted  time-lapse
//! images.
//! \param BACKGROUND_MAP_FRAMES - The number of frames which are averages to create each map of the sky background.
//! \param BACKGROUND_MAP_SAMPLES - The number of background maps which we hold concurrently, taking the lowest sky
//! background estimate from the set to filter out pixels which brighten for a few minutes while stars pass through.
//! \param BACKGROUND_MAP_REDUCTION_CYCLES - The number of frames over which we reduce the background map after every
//! <BACKGROUND_MAP_FRAMES> have been averaged. The reduction is time consuming, so we do it in lots of small chunks
//! whilst processing the video frames which are coming in.
//! \param fetch_frame - Function pointer to the function we call to fetch video frames.
//! \param rewind_video - Function pointer to the function we call to rewind the video to the beginning after the
//! initial run-in period. For live observing, this function is allowed to do nothing.
//! \return Zero on success

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
            int (*fetch_frame)(void *, unsigned char *, double *), int (*rewind_video)(void *, double *)) {
    int i;
    char line[FNAME_LENGTH], line2[FNAME_LENGTH], line3[FNAME_LENGTH];

    // Are we dealing with single-channel greyscale frames, or RGB video?
    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    if (DEBUG) {
        snprintf(line, FNAME_LENGTH, "Starting observing run at %s; observing run will end at %s.",
                 str_strip(friendly_time_string(utc_start), line2), str_strip(friendly_time_string(utc_stop), line3));
        logging_info(line);
    }

    // Allocate structure to store the current status of the observatory
    observe_status *os = calloc(1, sizeof(observe_status));
    if (os == NULL) {
        snprintf(temp_err_string, FNAME_LENGTH, "ERROR: malloc fail in observe.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
        exit(1);
    }

    // Store input settings inside observatory status
    os->video_handle = video_handle;
    os->width = width;
    os->height = height;
    os->label = label;
    os->obstory_id = obstory_id;
    os->mask = mask;
    os->fetch_frame = fetch_frame;
    os->fps = (float) fps;       // Requested frame rate
    os->frame_size = width * height;

    os->STACK_COMPARISON_INTERVAL = STACK_COMPARISON_INTERVAL;
    os->TRIGGER_PREFIX_TIME = TRIGGER_PREFIX_TIME;
    os->TRIGGER_SUFFIX_TIME = TRIGGER_SUFFIX_TIME;

    os->TRIGGER_SUFFIX_TIME_INITIAL = TRIGGER_SUFFIX_TIME_INITIAL;
    os->TRIGGER_MIN_DETECTIONS = TRIGGER_MIN_DETECTIONS;
    os->TRIGGER_MIN_PATH_LENGTH = TRIGGER_MIN_PATH_LENGTH;
    os->TRIGGER_MAX_MOVEMENT_PER_FRAME = TRIGGER_MAX_MOVEMENT_PER_FRAME;
    os->TRIGGER_MIN_SIGNIFICANCE = TRIGGER_MIN_SIGNIFICANCE;
    os->TRIGGER_MIN_SIGNIFICANCE_INITIAL = TRIGGER_MIN_SIGNIFICANCE_INITIAL;
    os->TRIGGER_THROTTLE_PERIOD = TRIGGER_THROTTLE_PERIOD;
    os->TRIGGER_THROTTLE_MAXEVT = TRIGGER_THROTTLE_MAXEVT;
    os->TIMELAPSE_EXPOSURE = TIMELAPSE_EXPOSURE;
    os->TIMELAPSE_INTERVAL = TIMELAPSE_INTERVAL;
    os->STACK_TARGET_BRIGHTNESS = STACK_TARGET_BRIGHTNESS;

    // Allocate a rolling video buffer which we use to store the last few seconds of video
    os->video_buffer_frames = (int) (os->fps * VIDEO_BUFFER_LEN); // frames in buffer
    os->bytes_per_frame = os->frame_size * YUV420_BYTES_PER_PIXEL;
    os->video_buffer_bytes = os->video_buffer_frames * os->bytes_per_frame;
    os->video_buffer = malloc((size_t) os->video_buffer_bytes);

    // When we catch a trigger, we include a few frames before the object appears, and after it disappears
    os->trigger_prefix_frame_count = (int) (os->TRIGGER_PREFIX_TIME * os->fps); // frames to store beforehand
    os->trigger_suffix_frame_count = (int) (os->TRIGGER_SUFFIX_TIME * os->fps); // frames to store afterwards

    // An object which has only been seen once must recur within this number of frames
    os->trigger_suffix_initial_frame_count = (int) (os->TRIGGER_SUFFIX_TIME_INITIAL * os->fps);

    // Allocate timelapse buffer
    os->utc = 0;
    os->timelapse_utc_start = 1e40; // This is UTC of next frame; we don't start until we've done a run-in period
    os->frames_per_timelapse = (int) (os->fps * os->TIMELAPSE_EXPOSURE);
    os->stack_timelapse = malloc(os->frame_size * sizeof(int) * channel_count); // Stack frames here

    // Background maps are used for background subtraction.
    // Holds the average value of each pixel, sampled over a few thousand frames
    os->background_maps = malloc((BACKGROUND_MAP_SAMPLES + 1) * sizeof(int *));

    // We store a number of historical background maps over a long period, to exclude maps where stars were passing
    // through particular pixels.
    for (i = 0; i <= BACKGROUND_MAP_SAMPLES; i++) {
        os->background_maps[i] = (int *) calloc(sizeof(int), os->frame_size * channel_count);
    }

    // Workspace which counts the number of times any given pixel has a particular value
    os->background_workspace = calloc(1, (size_t) (os->frame_size * channel_count * 256 * sizeof(int)));

    // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
    os->past_trigger_map = calloc(1, os->frame_size * sizeof(int));

    // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
    // 2D array of ints used to mark out pixels which have brightened suspiciously.
    os->trigger_map = calloc(1, os->frame_size * sizeof(int));
    os->difference_frame = calloc(1, os->frame_size);
    os->trigger_mask_frame = calloc(1, os->frame_size);
    os->trigger_map_frame = calloc(1, os->frame_size);

    // Count of how many pixels are in each numbered connected block
    os->trigger_block_count = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_top = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_bot = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_sumx = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_sumy = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_suml = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_redirect = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));

    // Make sure malloc operations were successful
    if ((!os->video_buffer) ||
        (!os->stack_timelapse) || (!os->background_workspace) || (!os->past_trigger_map) ||
        (!os->trigger_map) || (!os->difference_frame) || (!os->trigger_mask_frame) || (!os->trigger_map_frame) ||
        (!os->trigger_block_count) || (!os->trigger_block_top) || (!os->trigger_block_bot) ||
        (!os->trigger_block_sumx) ||
        (!os->trigger_block_sumy) || (!os->trigger_block_suml) || (!os->trigger_block_redirect)
            ) {
        snprintf(temp_err_string, FNAME_LENGTH, "ERROR: malloc fail in observe.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    // For each object that we are tracking, we compile a stacked image of its appearance,
    // and the maximum value of each pixel.
    for (i = 0; i < MAX_EVENTS; i++) {
        //os->event_list[i].stacked_image = malloc(os->frame_size * channel_count * sizeof(int));
        os->event_list[i].max_stack = malloc(os->frame_size * channel_count * sizeof(int));
        os->event_list[i].max_trigger = malloc(os->frame_size);

        if (  // (!os->event_list[i].stacked_image) ||
                (!os->event_list[i].max_stack) || (!os->event_list[i].max_trigger)) {
            snprintf(temp_err_string, FNAME_LENGTH, "ERROR: malloc fail in observe.");
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }
    }

    // Make sure that all event trackers are set to being inactive before a start
    for (i = 0; i < MAX_EVENTS; i++) {
        os->event_list[i].active = 0;
        os->event_list[i].video_output.active = 0;
    }

    // Count how many frames we've fed into the brightness histograms in background_workspace
    os->background_frame_count = 0;
    os->background_buffer_current = 0;

    // Count how many frames have been stacked into the timelapse buffer (stack_timelapse)
    os->timelapse_frame_count = -1;
    os->frame_counter = 0;

    // Let the camera run for a period before triggering, as it takes this long to make first background map
    // This counts down to zero. When it reaches zero, we start observing.
    os->run_in_frame_countdown = 15000 + BACKGROUND_MAP_FRAMES;

    // Noise level if frames, estimated from the standard deviation of pixel values between successive frames
    os->noise_level = 128;
    os->mean_level = 128;

    // Trigger throttling
    os->trigger_throttle_timer = 0; // Count down to when we reset the trigger throttle
    os->trigger_throttle_counter = 0; // Number of triggers within the last time period

    // Do some observing!
    observing_loop(os, utc_stop, BACKGROUND_MAP_FRAMES, BACKGROUND_MAP_SAMPLES, BACKGROUND_MAP_REDUCTION_CYCLES,
                   rewind_video);

    // Clean up all the buffers we allocated
    for (i = 0; i < MAX_EVENTS; i++) {
        //free(os->event_list[i].stacked_image);
        free(os->event_list[i].max_stack);
        free(os->event_list[i].max_trigger);
    }
    free(os->trigger_map);
    free(os->trigger_block_count);
    free(os->trigger_block_sumx);
    free(os->trigger_block_sumy);
    free(os->trigger_block_suml);
    free(os->trigger_block_redirect);
    free(os->difference_frame);
    free(os->trigger_mask_frame);
    free(os->trigger_map_frame);
    free(os->video_buffer);
    free(os->stack_timelapse);
    for (i = 0; i < BACKGROUND_MAP_SAMPLES; i++) free(os->background_maps[i]);
    free(os->background_maps);
    free(os->background_workspace);
    free(os->past_trigger_map);
    free(os);
    return 0;
}

//! observing_loop - The main observing loop
//! \param os - Settings pertaining to this observing run.
//! \param utc_stop The unix time stamp at which we need to exit the observing loop if we don't reach the end of the
//! video beforehand. Zero means we never exit.
//! \param BACKGROUND_MAP_FRAMES - The number of frames which are averages to create each map of the sky background.
//! \param BACKGROUND_MAP_SAMPLES - The number of background maps which we hold concurrently, taking the lowest sky
//! background estimate from the set to filter out pixels which brighten for a few minutes while stars pass through.
//! \param BACKGROUND_MAP_REDUCTION_CYCLES - The number of frames over which we reduce the background map after every
//! <BACKGROUND_MAP_FRAMES> have been averaged. The reduction is time consuming, so we do it in lots of small chunks
//! whilst processing the video frames which are coming in.
//! \param rewind_video - Function pointer to the function we call to rewind the video to the beginning after the
//! initial run-in period. For live observing, this function is allowed to do nothing.
void observing_loop(observe_status *os, const double utc_stop,
                    const int BACKGROUND_MAP_FRAMES, const int BACKGROUND_MAP_SAMPLES,
                    const int BACKGROUND_MAP_REDUCTION_CYCLES, int (*rewind_video)(void *, double *)) {
    char line[FNAME_LENGTH];

    // Are we dealing with single-channel greyscale frames, or RGB video?
    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    // Main observing loop
    while (1) {

        // Check how we're doing for time; if we've reached the time to stop, stop now!
        int t = (int) (time(NULL));
        if (t >= utc_stop) break;

        // Check if we've just completed the initial run-in period
        if ((os->run_in_frame_countdown > 0) && (--os->run_in_frame_countdown == 0)) {
            if (DEBUG) {
                snprintf(line, FNAME_LENGTH, "Run-in period completed.");
                logging_info(line);
            }

            // Test if this is the first run-in period, or a subsequent one after writing video
            const int first_run_in_period = os->timelapse_utc_start > 1e20;

            // After initial run-in period, we need to start process of taking time-lapse exposures
            if (first_run_in_period) {
                // Rewind the tape to the beginning if we can
                (*rewind_video)(os->video_handle, &os->utc);

                // Start making time lapse video; set the start time for the first frame at a round number of seconds
                os->timelapse_utc_start = ceil(os->utc / os->TIMELAPSE_INTERVAL) * os->TIMELAPSE_INTERVAL + 0.5;
            }
        }

        // Calculate position in the rolling buffer where we will store the next video frame
        unsigned char *buffer_pos = (os->video_buffer +
                                     (os->frame_counter % os->video_buffer_frames) * os->bytes_per_frame);

        // Once on each cycle through the video buffer, estimate the noise level and mean level of the input frames
        if (buffer_pos == os->video_buffer) {
            os->noise_level = estimate_noise_level(os->width, os->height,
                                                   os->video_buffer, 16, &os->mean_level);
        }

        // Fetch the next frame of input video
        int status = read_frame(os, buffer_pos, (os->timelapse_frame_count >= 0) ? os->stack_timelapse : NULL);
        if (status) break; // We've run out of video

        // We've just stacked another frame into the histograms we use to construct a background map for each pixel
        os->background_frame_count++;

        // Have we just finished compiling the histograms for a new background model?
        if (os->background_frame_count >= BACKGROUND_MAP_FRAMES) {
            // In the successive frames after we've got enough frames, we compile small parts of the background map, but
            // not all in one go as it takes quite a long time

            // The chunk number we want to work on is given by how many frames past <BACKGROUND_MAP_FRAMES> we are
            const int reduction_cycle = os->background_frame_count - BACKGROUND_MAP_FRAMES;

            // Compile the next chunk of the background map
            background_calculate(os->width, os->height, channel_count,
                                 reduction_cycle, BACKGROUND_MAP_REDUCTION_CYCLES,
                                 os->background_workspace, os->background_maps,
                                 BACKGROUND_MAP_SAMPLES, os->background_buffer_current);

            // Was this the last data reduction cycle?
            if (reduction_cycle >= BACKGROUND_MAP_REDUCTION_CYCLES) {
                // Start compiling histograms for a new background model
                os->background_frame_count = 0;

                // Pointer to the buffer where we will compile the next background model
                os->background_buffer_current = (os->background_buffer_current + 1) % BACKGROUND_MAP_SAMPLES;

                // Set the buffer to zero
                memset(os->background_workspace, 0, os->frame_size * channel_count * 256 * sizeof(int));
            }
        }

        // Are we making a time-lapse exposure?
        if (os->timelapse_frame_count >= 0) {
            // Count the number of frames we've added into time-lapse exposure
            os->timelapse_frame_count++;
        }

            // We are not making a time-lapse exposure, but is it time to start a new one?
        else if (os->utc > os->timelapse_utc_start) {
            // Clear buffer to hold new exposure, and reset frame counter
            memset(os->stack_timelapse, 0, os->frame_size * channel_count * sizeof(int));
            os->timelapse_frame_count = 0;
        }

        // If time-lapse exposure is finished, write it to disk
        // This happens if we have collected enough frames, or if the next time-lapse exposure is due to begin soon
        if ((os->timelapse_frame_count >= os->frames_per_timelapse) ||
            (os->utc > os->timelapse_utc_start + os->TIMELAPSE_INTERVAL - 1)) {
            // How many frames did we integrate?
            const int frame_count = os->timelapse_frame_count;
            char filename_stub[FNAME_LENGTH];

            // First record the time-lapse frame without background subtraction
            filename_generate(filename_stub, os->obstory_id, os->timelapse_utc_start,
                              "frame_", "timelapse", os->label);

            write_timelapse_frame(channel_count, os, frame_count, filename_stub);

            // Second, record a background-subtracted version of the time-lapse frame
            write_timelapse_bs_frame(channel_count, os, frame_count, filename_stub);

            // Every little while, dump an image of the sky background map for diagnostic purposes
            //if (floor(fmod(os->timelapse_utc_start, 1)) == 0) {
            //    write_timelapse_bg_model(BACKGROUND_MAP_FRAMES, channel_count, os, filename_stub);
            //}

            // Schedule the next time-lapse exposure
            os->timelapse_utc_start += os->TIMELAPSE_INTERVAL;

            // We are not actively recording a time-lapse exposure any longer
            os->timelapse_frame_count = -1;
        }

        // Increment the timer used to clear the trigger throttle counter periodically
        os->trigger_throttle_timer++;

        // How many frames before we clear the trigger throttling counter?
        const int trigger_throttle_cycles = (int) (os->TRIGGER_THROTTLE_PERIOD * 60 * os->fps);

        // Has the trigger-throttling timer reached its limit?
        if (os->trigger_throttle_timer >= trigger_throttle_cycles) {
            // Refresh throttling counter, and allow events to be recorded again
            os->trigger_throttle_timer = 0;
            os->trigger_throttle_counter = 0;
        }

        // Attenuate the map of past triggers <past_trigger_map> so that old-triggers decay with a half-life around
        // 7-8 minutes
        if ((os->frame_counter % 1000) == 0) {
            int o;
#pragma omp parallel for private(o)
            for (o = 0; o < os->frame_size; o++) {
                os->past_trigger_map[o] *= 0.95;
            }
        }

        // Consider stopping everything to write video files out, if we have triggers which have now ended
        consider_writing_video(os);

        // Test whether triggering is allowed (we are not in run-in period, and trigger throttle not active)
        os->triggering_allowed = ((os->run_in_frame_countdown == 0) &&
                                  (os->trigger_throttle_counter < os->TRIGGER_THROTTLE_MAXEVT));

        // Close any trigger events which are no longer active
        register_trigger_ends(os);

        // Pointers to the latest video frame
        unsigned char *image_new = buffer_pos;

        // Pointer to the previous frame that we compare the latest frame to
        unsigned char *image_old =
                os->video_buffer +
                (((os->frame_counter + os->video_buffer_frames - os->STACK_COMPARISON_INTERVAL)
                  % os->video_buffer_frames)
                 * os->bytes_per_frame);

        // Test whether motion sensor has triggered
        check_for_triggers(os, image_new, image_old);

        // Count frames from the beginning of the video
        os->frame_counter++;
    }
}

//! register_trigger - Called when <check_for_triggers> detects a moving object. We check whether this is a
//! re-detection of an existing moving object, or something new.
//! \param os - Settings pertaining to this observing run.
//! \param block_id - The ID of the block of pixels which triggered the camera, as mapped in <os->trigger_map>
//! \param x_pos - The x-position of the centroid of the block of pixels which triggered the camera.
//! \param y_pos - The y-position of the centroid of the block of pixels which triggered the camera.
//! \param pixel_count - The number of brightened pixels which produced this trigger.
//! \param amplitude - The total brightness excess, integrated over all pixels, which produced this trigger.
//! \param image1 - The video frame which triggered the camera
//! \param image2 - The previous video frame which image1 was compared against

void register_trigger(observe_status *os, const int block_id, const int x_pos, const int y_pos, const int pixel_count,
                      const int amplitude, const unsigned char *image1, const unsigned char *image2) {

    // Do not proceed if triggering is not enabled
    if (!os->triggering_allowed) return;

    // Calculate the pixel-integrated brightness of this trigger in units of standard deviations of random noise
    const double significance = amplitude / os->noise_level;

    // The maximum distance a moving object may move from one frame to next
    const int trigger_maximum_movement_per_frame = os->TRIGGER_MAX_MOVEMENT_PER_FRAME;

    // The minimum number of frames in which a moving object must be detected
    const int minimum_detections_for_event = os->TRIGGER_MIN_DETECTIONS;

    // The minimum number of pixels that the moving object must move across the frame
    const int minimum_object_path_length = os->TRIGGER_MIN_PATH_LENGTH;

    // Are we dealing with single-channel greyscale frames, or RGB video?
    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    // Cycle through objects we are already tracking to find nearest one
    int closest_trigger_index = -1;
    int closest_trigger_distance = 9999;
    for (int trigger_index = 0; trigger_index < MAX_EVENTS; trigger_index++)
        if (os->event_list[trigger_index].active) {
            const int latest_detection_index = os->event_list[trigger_index].detection_count - 1;
            const int distance = (int) hypot(x_pos - os->event_list[trigger_index].detections[latest_detection_index].x,
                                             y_pos - os->event_list[trigger_index].detections[latest_detection_index].y
            );
            if (distance < closest_trigger_distance) {
                closest_trigger_distance = distance;
                closest_trigger_index = trigger_index;
            }
        }

    // If there is an existing object that is close by, decide that this detection is of that object
    const int repeat_detection = (closest_trigger_distance < trigger_maximum_movement_per_frame);

    // Check that this detection meets minimum significance threshold
    // (lower for repeat detections than for a first detection)
    if (significance < (repeat_detection ? os->TRIGGER_MIN_SIGNIFICANCE : os->TRIGGER_MIN_SIGNIFICANCE_INITIAL)) {
        return;
    }

    // Update trigger map to highlight the block of pixels which have triggered in schematic trigger map
    int block_index;
    for (block_index = 1; block_index <= os->block_count; block_index++) {
        // Some blocks are aliases for other blocks, if they connect further down the image
        int root_index = block_index;
        while (os->trigger_block_redirect[root_index] > 0) root_index = os->trigger_block_redirect[root_index];

        // Is this block an alias for the one which has just triggered the camera?
        if (root_index == block_id) {
            // Loop over all pixels in the frame, highlighting pixels in this block
            int j;
#pragma omp parallel for private(j)
            for (j = 0; j < os->frame_size; j++)
                if (os->trigger_map[j] == block_index) {
                    // Make pixels belonging to this block brighter
                    os->trigger_map_frame[j] *= 4;

                    // For all events that are currently active, flag this pixel in the <max_trigger> map
                    for (int i = 0; i < MAX_EVENTS; i++)
                        if (os->event_list[i].active == 1)
                            os->event_list[i].max_trigger[j] = os->trigger_map_frame[j];
                }
        }
    }

    // If this is a repeat detection, update that object's event structure to include the new detection
    if (repeat_detection) {
        const int trigger_index = closest_trigger_index;
        const int last_detection_index = os->event_list[trigger_index].detection_count - 1;

        // Has this object already been seen in this frame?
        if (os->event_list[trigger_index].detections[last_detection_index].frame_count == os->frame_counter) {
            // If so, take position of object as average position of multiple amplitude peaks

            // Update structure describing existing detection
            detection *detection = &os->event_list[trigger_index].detections[last_detection_index];
            const int new_amplitude = detection->amplitude + amplitude;
            detection->x = (detection->x * detection->amplitude + x_pos * amplitude) / new_amplitude;
            detection->y = (detection->y * detection->amplitude + y_pos * amplitude) / new_amplitude;
            detection->amplitude = new_amplitude;
            detection->pixel_count += pixel_count;
        } else {
            // No existing detection of this object, so add a new detection to list
            os->event_list[trigger_index].detection_count++;
            detection *detection = &os->event_list[trigger_index].detections[last_detection_index + 1];
            detection->frame_count = os->frame_counter;
            detection->x = x_pos;
            detection->y = y_pos;
            detection->utc = os->utc;
            detection->pixel_count = pixel_count;
            detection->amplitude = amplitude;

            // If we've reached a threshold number of detections, this detection is "confirmed"
            if (!os->event_list[trigger_index].video_output.active) {

                // Have we had enough detections of this object to confirm it as real?
                const int sufficient_detections = (os->event_list[trigger_index].detection_count >=
                                                   minimum_detections_for_event);

                // Detections which span the whole duration of this event so far
                const int N0 = 0;  // first detection
                const int N2 = os->event_list[trigger_index].detection_count - 1;  // latest detection

                // Has this object moved far enough across the frame to be a moving object, not a twinkling star?
                double pixel_track_len = hypot(os->event_list[trigger_index].detections[N0].x -
                                               os->event_list[trigger_index].detections[N2].x,
                                               os->event_list[trigger_index].detections[N0].y -
                                               os->event_list[trigger_index].detections[N2].y);

                // Reject events that don't move much -- probably a twinkling star
                const int sufficient_movement = (pixel_track_len >= minimum_object_path_length);

                // Start producing output files if this event has now achieved required number of detections
                if (sufficient_movement && sufficient_detections) {
                    // We have detected a new object, seen in multiple frames
                    if (DEBUG) {
                        int year, month, day, hour, min, status;
                        double sec;
                        double JD = (os->utc / 86400.0) + 2440587.5;
                        inv_julian_day(JD, &year, &month, &day, &hour, &min, &sec, &status, temp_err_string);
                        snprintf(temp_err_string, FNAME_LENGTH,
                                 "Camera has triggered at (%04d/%02d/%02d %02d:%02d:%02d -- x=%d,y=%d).",
                                 year, month, day, hour, min, (int) sec, x_pos, y_pos);
                        logging_info(temp_err_string);
                    }

                    // Start producing output files associated with this camera trigger
                    filename_generate(os->event_list[trigger_index].filename_stub, os->obstory_id, os->utc,
                                      "event", "triggers", os->label);

                    // Configuration for video file output
                    snprintf(os->event_list[trigger_index].video_output.filename, FNAME_LENGTH,
                             "%s%s", os->event_list[trigger_index].filename_stub, ".vid");
                    os->event_list[trigger_index].video_output.active = 1;
                    os->event_list[trigger_index].video_output.width = os->width;
                    os->event_list[trigger_index].video_output.height = os->height;
                    os->event_list[trigger_index].video_output.buffer_write_position = os->frame_counter -
                                                                                       os->trigger_prefix_frame_count;
                    os->event_list[trigger_index].video_output.buffer_end_position = -1;

                    // Difference image, B-A, set by <check_for_triggers>
                    write_trigger_difference_frame(os, trigger_index);

                    // Map of pixels which are currently excluded from triggering due to excessive variability
                    write_trigger_mask_frame(os, trigger_index);

                    // Map of the pixels whose brightening caused this trigger
                    write_trigger_map_frame(os, trigger_index);

                    // The video frame in which this trigger was first detected
                    write_trigger_frame(os, image1, channel_count, trigger_index);

                    // The comparison frame which preceded the frame where the trigger was detected
                    write_trigger_previous_frame(os, image2, channel_count, trigger_index);
                }
            }
        }
        return;
    }

    // We have detected a new object. Create new event descriptor.

    // Search for first available trigger descriptor
    int trigger_index;
    for (trigger_index = 0; trigger_index < MAX_EVENTS; trigger_index++)
        if (os->event_list[trigger_index].active == 0) break;

    // If no descriptor available, we cannot continue
    if (trigger_index >= MAX_EVENTS) {
        // No free event storage space
        logging_info("Ignoring trigger; no event descriptors available.");
        return;
    }

    // Register event in events table
    os->event_list[trigger_index].active = 1;
    os->event_list[trigger_index].detection_count = 1;
    os->event_list[trigger_index].start_time = os->utc;

    // Record first detection of this event
    detection *detection = &os->event_list[trigger_index].detections[0];
    detection->frame_count = os->frame_counter;
    detection->x = x_pos;
    detection->y = y_pos;
    detection->utc = os->utc;
    detection->pixel_count = pixel_count;
    detection->amplitude = amplitude;

    // Copy the frame that triggered the camera as a starting point for the stacked frames associated with this trigger
    int j;
#pragma omp parallel for private(j)
    for (j = 0; j < os->frame_size * channel_count; j++) {
        //os->event_list[trigger_index].stacked_image[j] = image1[j];
        os->event_list[trigger_index].max_stack[j] = image1[j];
    }

    // Copy the max of pixels which triggered the camera
#pragma omp parallel for private(j)
    for (j = 0; j < os->frame_size; j++) {
        os->event_list[trigger_index].max_trigger[j] = os->trigger_map_frame[j];
    }
}

//! register_trigger_ends - Check through list of events we are currently tracking.
//! Weed out any which haven't been seen for a long time, or are exceeding maximum allowed recording time.
//! \param os - Settings pertaining to the current observing run

void register_trigger_ends(observe_status *os) {

    // Pointer to the latest video frame in the rolling buffer
    unsigned char *current_frame = (os->video_buffer +
                                    (os->frame_counter % os->video_buffer_frames) * os->bytes_per_frame);

    // Are we dealing with single-channel greyscale frames, or RGB video?
    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    // Loop through moving objects we're tracking, and see whether any of them have disappeared
    for (int trigger_index = 0; trigger_index < MAX_EVENTS; trigger_index++)
        if (os->event_list[trigger_index].active == 1) {

            // Latest detection of this event
            const int N2 = os->event_list[trigger_index].detection_count - 1;

//            // Update the stack of the average brightness of each pixel over the duration of this event
//#pragma omp parallel for private(j)
//            for (j = 0; j < os->frame_size * channel_count; j++)
//                os->event_list[trigger_index].stacked_image[j] += current_frame[j];

            // Update the maximum brightness of each pixel over the duration of this event
            int j;
#pragma omp parallel for private(j)
            for (j = 0; j < os->frame_size * channel_count; j++) {
                const int x = current_frame[j];
                if (x > os->event_list[trigger_index].max_stack[j]) os->event_list[trigger_index].max_stack[j] = x;
            }

            // How long must event disappear for, before we decide it has gone away?
            const int suffix_frames = (os->event_list[trigger_index].detection_count > 1)
                                      ? os->trigger_suffix_frame_count
                                      : os->trigger_suffix_initial_frame_count;

            // Has event disappeared?
            const int event_disappeared = (os->frame_counter >
                                           os->event_list[trigger_index].detections[N2].frame_count +
                                           suffix_frames);

            // If this object has disappeared, update its status accordingly
            if (event_disappeared) moving_object_disappeared(os, trigger_index);
        }
}

//! moving_object_disappeared - Called when a moving object has disappeared, in order to mark its event descriptor
//! accordingly.
//! \param os - The current observing status.
//! \param trigger_index - The number of the moving object trigger within the array <os->event_list>

void moving_object_disappeared(observe_status *os, int trigger_index) {
    // Are we dealing with single-channel greyscale frames, or RGB video?
    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    // Detections which span the whole duration of this event
    const int N0 = 0;  // first detection
    const int N2 = os->event_list[trigger_index].detection_count - 1;  // latest detection

    // If event was not confirmed, take no further action
    if (!os->event_list[trigger_index].video_output.active) {
        // logging_info("Detection not confirmed.");
        os->event_list[trigger_index].active = 0;
        return;
    }

    // Event is now only writing video
    os->event_list[trigger_index].active = 2;

    // Work out duration of event
    const double duration = os->event_list[trigger_index].detections[N2].utc -
                            os->event_list[trigger_index].detections[N0].utc;

    // Update counter for trigger rate throttling
    os->trigger_throttle_counter++;

    // Write path of event as JSON string
    int amplitude_peak = 0, amplitude_time_integrated = 0;
    {
        for (int j = 0; j < os->event_list[trigger_index].detection_count; j++) {
            const detection *d = &os->event_list[trigger_index].detections[j];
            amplitude_time_integrated += d->amplitude;
            if (d->amplitude > amplitude_peak) amplitude_peak = d->amplitude;
        }
    }

    // Dump stacked images of entire duration of event
    int stacked_frame_count = (os->frame_counter - os->event_list[trigger_index].detections[0].frame_count);

    // Time-averaged value of each pixel over the duration of the event
//write_trigger_time_average_frame(os, trigger_index, channel_count, duration, amplitude_peak,
//                                 amplitude_time_integrated, stacked_frame_count);

    // Maximum brightness of each pixel over the duration of the event
    write_trigger_max_brightness_frame(os, trigger_index, channel_count, duration, amplitude_peak,
                                       amplitude_time_integrated, stacked_frame_count);

    // Map of all pixels which triggered motion sensor over the duration of the event
    write_trigger_integrated_trigger_map(os, trigger_index, duration, amplitude_peak, amplitude_time_integrated,
                                         stacked_frame_count);

    // Make sure that video of this event ends at the right time
    os->event_list[trigger_index].video_output.buffer_end_position = os->frame_counter;

    // Write metadata to associate with this video file
    write_video_metadata(os, trigger_index);
}

//! consider_writing_video - Check whether we have moving objects waiting to write video files, in which case we may
//! want to write them if nothing is currently moving.
//! \param os - The current observing status.

void consider_writing_video(observe_status *os) {
    // Do we have any events whose start points will soon get over-written?
    int about_to_overwrite = 0;
    const int overwrite_position = os->frame_counter - os->video_buffer_frames + 5;
    for (int trigger_index = 0; trigger_index < MAX_EVENTS; trigger_index++)
        if (os->event_list[trigger_index].video_output.active)
            if (os->event_list[trigger_index].video_output.buffer_write_position < overwrite_position)
                about_to_overwrite = 1;

    // Do we have any events which are active?
    int have_active_events = 0;
    for (int trigger_index = 0; trigger_index < MAX_EVENTS; trigger_index++)
        if (os->event_list[trigger_index].active == 1)
            have_active_events = 1;

    // Do we have any events which need to write video?
    int have_events_to_write = 0;
    for (int trigger_index = 0; trigger_index < MAX_EVENTS; trigger_index++)
        if (os->event_list[trigger_index].video_output.active)
            have_events_to_write = 1;

    // If we're about to overwrite video we want to record, then sadly we need to stop tracking objects
    if (about_to_overwrite && have_active_events) {
        for (int trigger_index = 0; trigger_index < MAX_EVENTS; trigger_index++)
            if (os->event_list[trigger_index].active == 1)
                moving_object_disappeared(os, trigger_index);

        // We don't have any active events any longer!
        have_active_events = 0;
    }

    // If we have video to record, and no active events, write the video now!
    if (have_events_to_write && !have_active_events) {
        // Loop over events to see which ones need to write video
        for (int trigger_index = 0; trigger_index < MAX_EVENTS; trigger_index++)
            if (os->event_list[trigger_index].video_output.active) {
                dump_video(
                        os->event_list[trigger_index].video_output.width,
                        os->event_list[trigger_index].video_output.height,
                        os->event_list[trigger_index].video_output.filename,
                        os->video_buffer, os->video_buffer_frames,
                        os->event_list[trigger_index].video_output.buffer_write_position,
                        os->event_list[trigger_index].video_output.buffer_end_position,
                        (int) (VIDEO_CUTOFF_TIME * os->fps)
                );

                // Mark that this video no longer needs writing
                os->event_list[trigger_index].video_output.active = 0;
                os->event_list[trigger_index].active = 0;
            }

        // We should now do a new video run-in period, because the video buffer is probably quite screwed up...
        os->run_in_frame_countdown = 100;
    }
}
