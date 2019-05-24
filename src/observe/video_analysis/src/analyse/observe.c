// observe.c
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

// Each pixel is 1.5 bytes in YUV420 stream
#define YUV420_BYTES_PER_PIXEL  3/2

// Generate a filename which starts with a time stamp string
char *filename_generate(char *output, const char *obstory_id, double utc, char *tag, const char *dir_name,
                        const char *label) {
    char path[FNAME_LENGTH];

    // Convert unix time into a Julian day number
    const double JD = utc / 86400.0 + 2440587.5;
    int year, month, day, hour, min, status;
    double sec;

    // Make sure that the analysis products directory exists
    sprintf(path, "%s/analysis_products", OUTPUT_PATH);
    status = mkdir(path, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    if (status && (errno != EEXIST)) {
        sprintf(temp_err_string, "ERROR: Could not create directory <%s>. Returned error code %d. errno %d. %s.",
                path, status, errno, strerror(errno));
        logging_info(temp_err_string);
    }

    // Make sure that the subdirectory for this kind of observation exists, e.g. <timelapse_live>
    sprintf(path, "%s/analysis_products/%s_%s", OUTPUT_PATH, dir_name, label);
    status = mkdir(path, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    if (status && (errno != EEXIST)) {
        sprintf(temp_err_string, "ERROR: Could not create directory <%s>. Returned error code %d. errno %d. %s.",
                path, status, errno, strerror(errno));
        logging_info(temp_err_string);
    }

    // Convert unix time into a calendar date
    inv_julian_day(JD, &year, &month, &day, &hour, &min, &sec, &status, output);
    sprintf(output, "%s/%04d%02d%02d%02d%02d%02d_%s_%s", path, year, month, day, hour, min, (int) sec, obstory_id, tag);
    return output;
}

// Record metadata associated with each file into a text file. filename must be writable string.
void write_metadata(char *filename, char *item_types, ...) {
    // Change file extension of filename to .txt
    int filename_len = (int) strlen(filename);
    int i = filename_len - 1;
    while ((i > 0) && (filename[i] != '.')) i--;
    sprintf(filename + i, ".txt");

    // Write metadata, item by item
    FILE *f = fopen(filename, "w");
    if (!f) return;
    va_list ap;
    va_start(ap, item_types);
    for (i = 0; item_types[i] != '\0'; i++) {
        char *x = va_arg(ap, char*);
        switch (item_types[i]) {
            // String metadata
            case 's': {
                char *y = va_arg(ap, char*);
                fprintf(f, "%s %s\n", x, y);
                break;
            }
                // Double type metadata
            case 'd': {
                double y = va_arg(ap, double);
                fprintf(f, "%s %.15e\n", x, y);
                break;
            }
                // Int type metadata
            case 'i': {
                int y = va_arg(ap, int);
                fprintf(f, "%s %d\n", x, y);
                break;
            }
                // Metadata type characters in <item_types> must be s, d or i.
            default: {
                sprintf(temp_err_string, "ERROR: Unrecognised data type character '%c'.", item_types[i]);
                logging_fatal(__FILE__, __LINE__, temp_err_string);
            }
        }
    }
    // Close metadata output file
    va_end(ap);
    fclose(f);
}

// Read a group of frames, and create the stacks used to test for triggers
int read_frame(observe_status *os, unsigned char *buffer, int *stack2) {
    int i;

    static unsigned char *tmp_rgb = NULL;

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

int observe(void *video_handle, const char *obstory_id, const double utc_start, const double utc_stop,
            const int width, const int height, const double fps, const char *label, const unsigned char *mask,
            const int STACK_COMPARISON_INTERVAL, const int TRIGGER_PREFIX_TIME, const int TRIGGER_SUFFIX_TIME,
            const int VIDEO_BUFFER_LEN, const int TRIGGER_MAX_DURATION,
            const int TRIGGER_THROTTLE_PERIOD, const int TRIGGER_THROTTLE_MAXEVT,
            const int TIMELAPSE_EXPOSURE, const int TIMELAPSE_INTERVAL, const int STACK_TARGET_BRIGHTNESS,
            const int BACKGROUND_MAP_FRAMES, const int BACKGROUND_MAP_SAMPLES,
            const int BACKGROUND_MAP_REDUCTION_CYCLES,
            int (*fetch_frame)(void *, unsigned char *, double *), int (*rewind_video)(void *, double *)) {
    int i;
    char line[FNAME_LENGTH], line2[FNAME_LENGTH], line3[FNAME_LENGTH];

    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    if (DEBUG) {
        sprintf(line, "Starting observing run at %s; observing run will end at %s.",
                str_strip(friendly_time_string(utc_start), line2), str_strip(friendly_time_string(utc_stop), line3));
        logging_info(line);
    }

    observe_status *os = calloc(1, sizeof(observe_status));
    if (os == NULL) {
        sprintf(temp_err_string, "ERROR: malloc fail in observe.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
        exit(1);
    }

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
    os->TRIGGER_MAX_DURATION = TRIGGER_MAX_DURATION;
    os->TRIGGER_THROTTLE_PERIOD = TRIGGER_THROTTLE_PERIOD;
    os->TRIGGER_THROTTLE_MAXEVT = TRIGGER_THROTTLE_MAXEVT;
    os->TIMELAPSE_EXPOSURE = TIMELAPSE_EXPOSURE;
    os->TIMELAPSE_INTERVAL = TIMELAPSE_INTERVAL;
    os->STACK_TARGET_BRIGHTNESS = STACK_TARGET_BRIGHTNESS;

    // Video buffer. This store the last few seconds of video in a rolling spool.
    os->video_buffer_frames = (int) (os->fps * VIDEO_BUFFER_LEN);
    os->bytes_per_frame = os->frame_size * YUV420_BYTES_PER_PIXEL;
    os->video_buffer_bytes = os->video_buffer_frames * os->bytes_per_frame;
    os->video_buffer = malloc((size_t) os->video_buffer_bytes);

    // When we catch a trigger, we include a few frames before the object appears, and after it disappears
    os->trigger_prefix_frame_count = (int) (os->TRIGGER_PREFIX_TIME * os->fps);
    os->trigger_suffix_frame_count = (int) (os->TRIGGER_SUFFIX_TIME * os->fps);

    // Timelapse buffers
    os->utc = 0;
    os->timelapse_utc_start = 1e40; // This is UTC of next frame, but we don't start until we've done a run-in period
    os->frames_per_timelapse = (int) (os->fps * os->TIMELAPSE_EXPOSURE);
    os->stack_timelapse = malloc(os->frame_size * sizeof(int) * channel_count);

    // Background maps are used for background subtraction.
    // Holds the background value of each pixel, sampled over a few thousand frames
    os->background_maps = malloc((BACKGROUND_MAP_SAMPLES + 1) * sizeof(int *));

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
    os->trigger_map_rgb = calloc(1, os->frame_size * 3);

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
        (!os->trigger_map) || (!os->trigger_map_rgb) ||
        (!os->trigger_block_count) || (!os->trigger_block_top) || (!os->trigger_block_bot) ||
        (!os->trigger_block_sumx) ||
        (!os->trigger_block_sumy) || (!os->trigger_block_suml) || (!os->trigger_block_redirect)
            ) {
        sprintf(temp_err_string, "ERROR: malloc fail in observe.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    // For each object that we are tracking, we compile a stacked image of its appearance,
    // and the max value of each pixel.
    for (i = 0; i < MAX_EVENTS; i++) {
        os->event_list[i].stacked_image = malloc(os->frame_size * channel_count * sizeof(int));
        os->event_list[i].max_stack = malloc(os->frame_size * channel_count * sizeof(int));
        os->event_list[i].max_trigger = malloc(os->frame_size);

        if ((!os->event_list[i].stacked_image) ||
            (!os->event_list[i].max_stack) || (!os->event_list[i].max_trigger)) {
            sprintf(temp_err_string, "ERROR: malloc fail in observe.");
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
    os->run_in_frame_countdown = 100 + BACKGROUND_MAP_FRAMES;
    os->noise_level = 128;

    // Trigger throttling
    os->trigger_throttle_timer = 0;
    os->trigger_throttle_counter = 0;

    // Reset trigger throttle counter after this many frame groups have been processed
    os->trigger_throttle_period = (int) (os->TRIGGER_THROTTLE_PERIOD * 60. * os->fps);

    // Processing loop
    while (1) {
        int t = (int) (time(NULL));
        if (t >= utc_stop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!

        // Once we've done initial run-in period, rewind the tape to the beginning if we can
        if (os->run_in_frame_countdown && !--os->run_in_frame_countdown) {
            if (DEBUG) {
                sprintf(line, "Run-in period completed.");
                logging_info(line);
            }
            (*rewind_video)(os->video_handle, &os->utc);

            // Start making timelapse video
            os->timelapse_utc_start = ceil(os->utc / os->TIMELAPSE_EXPOSURE) * os->TIMELAPSE_EXPOSURE + 0.5;
        }

        // Work out where we're going to read next second of video to.
        unsigned char *buffer_pos = (os->video_buffer +
                                     (os->frame_counter % os->video_buffer_frames) * os->bytes_per_frame);

        // Once on each cycle through the video buffer, estimate the thermal noise of the camera
        if (buffer_pos == os->video_buffer) {
            os->noise_level = estimate_noise_level(os->width, os->height, os->video_buffer, 16);
        }

        // Read the next frame of input video
        int status = read_frame(os, buffer_pos, (os->timelapse_frame_count >= 0) ? os->stack_timelapse : NULL);
        if (status) break; // We've run out of video

        // If we've stacked enough frames since we last made a background map, make a new background map
        os->background_frame_count++;
        if (os->background_frame_count >= BACKGROUND_MAP_FRAMES) {
            const int reduction_cycle = os->background_frame_count - BACKGROUND_MAP_FRAMES;
            background_calculate(os->width, os->height, channel_count,
                                 reduction_cycle, BACKGROUND_MAP_REDUCTION_CYCLES,
                                 os->background_workspace, os->background_maps,
                                 BACKGROUND_MAP_SAMPLES, os->background_buffer_current);
            if (reduction_cycle >= BACKGROUND_MAP_REDUCTION_CYCLES) {
                os->background_frame_count = 0;
                os->background_buffer_current = (os->background_buffer_current + 1) % BACKGROUND_MAP_SAMPLES;
                memset(os->background_workspace, 0, os->frame_size * channel_count * 256 * sizeof(int));
            }
        }

        // If we're making a time lapse exposure, count the frames we've put in
        if (os->timelapse_frame_count >= 0) {
            os->timelapse_frame_count++;
        }
            // Is it time to start a new time lapse exposure?
        else if (os->utc > os->timelapse_utc_start) {
            memset(os->stack_timelapse, 0, os->frame_size * channel_count * sizeof(int));
            os->timelapse_frame_count = 0;
        }

        // If time-lapse exposure is finished, dump it
        if ((os->timelapse_frame_count >= os->frames_per_timelapse) ||
            (os->utc > os->timelapse_utc_start + os->TIMELAPSE_INTERVAL - 1)) {
            const int frame_count = os->timelapse_frame_count;
            char fstub[FNAME_LENGTH], fname[FNAME_LENGTH];
            double gain_factor;

            // First dump the time-lapse image without background subtraction
            filename_generate(fstub, os->obstory_id, os->timelapse_utc_start, "frame_", "timelapse", os->label);

            sprintf(fname, "%s%s", fstub, "BS0.rgb");
            dump_frame_from_ints(os->width, os->height, channel_count, os->stack_timelapse, frame_count,
                                 os->STACK_TARGET_BRIGHTNESS, &gain_factor, fname);

            // Store metadata about the time-lapse frame
            write_metadata(fname, "sdsiidddi",
                           "obstoryId", os->obstory_id,
                           "utc", os->timelapse_utc_start,
                           "semanticType", "pigazing:timelapse",
                           "width", os->width,
                           "height", os->height,
                           "inputNoiseLevel", os->noise_level,
                           "stackNoiseLevel", os->noise_level / sqrt(frame_count) * gain_factor,
                           "gainFactor", gain_factor,
                           "stackedFrames", frame_count);

            // Dump a background-subtracted version of the time-lapse image
            sprintf(fname, "%s%s", fstub, "BS1.rgb");
            dump_frame_from_int_subtraction(os->width, os->height, channel_count, os->stack_timelapse, frame_count,
                                            os->STACK_TARGET_BRIGHTNESS, &gain_factor,
                                            os->background_maps[0], fname);

            // Store metadata about the time-lapse frame
            write_metadata(fname, "sdsiidddi",
                           "obstoryId", os->obstory_id,
                           "utc", os->timelapse_utc_start,
                           "semanticType", "pigazing:timelapse/backgroundSubtracted",
                           "width", os->width,
                           "height", os->height,
                           "inputNoiseLevel", os->noise_level,
                           "stackNoiseLevel", os->noise_level / sqrt(frame_count) * gain_factor,
                           "gainFactor", gain_factor,
                           "stackedFrames", frame_count);

            // Every few minutes, dump an image of the sky background map for diagnostic purposes
            if (floor(fmod(os->timelapse_utc_start, 1)) == 0) {
                sprintf(fname, "%s%s", fstub, "skyBackground.rgb");
                dump_frame_from_ints(os->width, os->height, channel_count, os->background_maps[0],
                                     256, 0, NULL, fname);
                write_metadata(fname, "sdsiiddi",
                               "obstoryId", os->obstory_id,
                               "utc", os->timelapse_utc_start,
                               "semanticType", "pigazing:timelapse/backgroundModel",
                               "width", os->width,
                               "height", os->height,
                               "inputNoiseLevel", os->noise_level,
                               "stackNoiseLevel", os->noise_level / sqrt(BACKGROUND_MAP_FRAMES),
                               "stackedFrames", ((int) BACKGROUND_MAP_FRAMES));
            }

            // Schedule the next time-lapse exposure
            os->timelapse_utc_start += os->TIMELAPSE_INTERVAL;
            os->timelapse_frame_count = -1;
        }

        // Update counters for trigger throttling
        os->trigger_throttle_timer++;
        const int trigger_throttle_cycles = (int) (os->TRIGGER_THROTTLE_PERIOD * 60 * os->fps);
        if (os->trigger_throttle_timer >= trigger_throttle_cycles) {
            os->trigger_throttle_timer = 0;
            os->trigger_throttle_counter = 0;
        }

        // Test whether triggering is allowed
        os->triggering_allowed = ((!os->run_in_frame_countdown) &&
                                  (os->trigger_throttle_counter < os->TRIGGER_THROTTLE_MAXEVT));

        // Close any trigger events which are no longer active
        register_trigger_ends(os);

        // Pointers to the two frames we plan to compare
        unsigned char *image_new = buffer_pos;

        unsigned char *image_old =
                os->video_buffer +
                (((os->frame_counter + os->video_buffer_frames - STACK_COMPARISON_INTERVAL) % os->video_buffer_frames)
                 * os->bytes_per_frame);

        // Test whether motion sensor has triggered
        check_for_triggers(os, image_new, image_old);

        os->frame_counter++;
    }

    for (i = 0; i < MAX_EVENTS; i++) {
        free(os->event_list[i].stacked_image);
        free(os->event_list[i].max_stack);
        free(os->event_list[i].max_trigger);
    }
    free(os->trigger_map);
    free(os->trigger_block_count);
    free(os->trigger_block_sumx);
    free(os->trigger_block_sumy);
    free(os->trigger_block_suml);
    free(os->trigger_block_redirect);
    free(os->trigger_map_rgb);
    free(os->video_buffer);
    free(os->stack_timelapse);
    for (i = 0; i < BACKGROUND_MAP_SAMPLES; i++) free(os->background_maps[i]);
    free(os->background_maps);
    free(os->background_workspace);
    free(os->past_trigger_map);
    free(os);
    return 0;
}

// Register a new trigger event
void register_trigger(observe_status *os, const int block_id, const int x_pos, const int y_pos, const int pixel_count,
                      const int amplitude, const unsigned char *image1, const unsigned char *image2) {
    if (!os->triggering_allowed) return;

    const int trigger_maximum_movement_per_frame = 70;
    const int minimum_detections_for_event = 2;
    const int minimum_object_path_length = 4;

    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    // Colour in block of pixels which have triggered in schematic trigger map
    int k;
    for (k = 1; k <= os->block_count; k++) {
        int k2 = k;
        while (os->trigger_block_redirect[k2] > 0) k2 = os->trigger_block_redirect[k2];
        if (k2 == block_id) {
            unsigned char *triggerB = os->trigger_map_rgb + os->frame_size * 2;
            int j;
#pragma omp parallel for private(j)
            for (j = 0; j < os->frame_size; j++)
                if (os->trigger_map[j] == k2) {
                    triggerB[j] *= 4;

                    for (int i = 0; i < MAX_EVENTS; i++)
                        if (os->event_list[i].active == 1)
                            os->event_list[i].max_trigger[j] = triggerB[j];
                }
        }
    }

    // Cycle through objects we are already tracking to find nearest one
    int i;
    int closest_trigger = -1;
    int closest_trigger_dist = 9999;
    for (i = 0; i < MAX_EVENTS; i++)
        if (os->event_list[i].active) {
            const int N = os->event_list[i].detection_count - 1;
            const int dist = (int) hypot(x_pos - os->event_list[i].detections[N].x,
                                         y_pos - os->event_list[i].detections[N].y);
            if (dist < closest_trigger_dist) {
                closest_trigger_dist = dist;
                closest_trigger = i;
            }
        }

    // If it's relatively close, assume this detection is of that object
    if (closest_trigger_dist < trigger_maximum_movement_per_frame) {
        const int i = closest_trigger;
        const int n = os->event_list[i].detection_count - 1;

        // Has this object already been seen in this frame?
        if (os->event_list[i].detections[n].frame_count == os->frame_counter) {
            // If so, take position of object as average position of multiple amplitude peaks
            detection *d = &os->event_list[i].detections[n];
            d->x = (d->x * d->amplitude + x_pos * amplitude) / (d->amplitude + amplitude);
            d->y = (d->y * d->amplitude + y_pos * amplitude) / (d->amplitude + amplitude);
            d->amplitude += amplitude;
            d->pixel_count += pixel_count;
        } else {
            // Otherwise add new detection to list
            os->event_list[i].detection_count++;
            detection *d = &os->event_list[i].detections[n + 1];
            d->frame_count = os->frame_counter;
            d->x = x_pos;
            d->y = y_pos;
            d->utc = os->utc;
            d->pixel_count = pixel_count;
            d->amplitude = amplitude;

            // If we've reached a threshold number of detections, we can start writing video
            if (!os->event_list[i].video_output.active) {
                // Detections which span the whole duration of this event so far
                const int N0 = 0;
                const int N2 = os->event_list[i].detection_count - 1;

                // Have we had enough detections of this object to confirm it as real?
                const int sufficient_detections = (os->event_list[i].detection_count >= minimum_detections_for_event);

                // Has this object moved far enough to be a moving object, not a twinkling star?
                double pixel_track_len = hypot(os->event_list[i].detections[N0].x - os->event_list[i].detections[N2].x,
                                               os->event_list[i].detections[N0].y - os->event_list[i].detections[N2].y);

                // Reject events that don't move much -- probably a twinkling star
                const int sufficient_movement = (pixel_track_len >= minimum_object_path_length);

                // Start writing video if this event looks plausible
                if (sufficient_movement && sufficient_detections) {
                    logging_info("Detection confirmed.");

                    os->event_list[i].video_output.active = 1;
                    os->event_list[i].video_output.file_handle = dump_video_init(
                            os->width, os->height,
                            os->event_list[i].video_output.filename);

                }
            }
        }
        return;
    }

    // We have detected a new object. Create new event descriptor.
    if (DEBUG) {
        int year, month, day, hour, min, status;
        double sec;
        double JD = (os->utc / 86400.0) + 2440587.5;
        inv_julian_day(JD, &year, &month, &day, &hour, &min, &sec, &status, temp_err_string);
        sprintf(temp_err_string, "Camera has triggered at (%04d/%02d/%02d %02d:%02d:%02d -- x=%d,y=%d).", year, month,
                day, hour, min, (int) sec, x_pos, y_pos);
        logging_info(temp_err_string);
    }

    for (i = 0; i < MAX_EVENTS; i++) if (os->event_list[i].active == 0) break;
    if (i >= MAX_EVENTS) {
        // No free event storage space
        logging_info("Ignoring trigger; no event descriptors available.");
        return;
    }

    // Register event in events table
    os->event_list[i].active = 1;
    os->event_list[i].detection_count = 1;
    os->event_list[i].start_time = os->utc;

    // Record first detection of this event
    detection *d = &os->event_list[i].detections[0];
    d->frame_count = os->frame_counter;
    d->x = x_pos;
    d->y = y_pos;
    d->utc = os->utc;
    d->pixel_count = pixel_count;
    d->amplitude = amplitude;

    // Start producing output files describing this camera trigger
    char fname[FNAME_LENGTH];
    filename_generate(os->event_list[i].filename_stub, os->obstory_id, os->utc, "event", "triggers", os->label);

    // Configuration for video file output
    sprintf(os->event_list[i].video_output.filename, "%s%s", os->event_list[i].filename_stub, ".vid");
    os->event_list[i].video_output.active = 0;
    os->event_list[i].video_output.width = os->width;
    os->event_list[i].video_output.height = os->height;
    os->event_list[i].video_output.frames_written = 0;
    os->event_list[i].video_output.buffer_write_position = ((os->frame_counter - os->trigger_prefix_frame_count)
                                                            % os->video_buffer_frames);
    os->event_list[i].video_output.buffer_end_position = -1;

    // Difference image, B-A, which we get from the red channel of <os->trigger_map_rgb>, set by <check_for_triggers>
    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_mapDifference.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_map_rgb + 0 * os->frame_size, fname);
    write_metadata(fname, "sdsiiddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/mapDifference",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "stackedFrames", 1);

    // Map of pixels which are currently excluded from triggering due to excessive variability
    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_mapExcludedPixels.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_map_rgb + 1 * os->frame_size, fname);
    write_metadata(fname, "sdsiiddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/mapExcludedPixels",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "stackedFrames", 1);

    // Map of the pixels whose brightening caused this trigger
    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_mapTrigger.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_map_rgb + 2 * os->frame_size, fname);
    write_metadata(fname, "sdsiiddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/mapTrigger",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "stackedFrames", 1);

    // The video frame in which this trigger was first detected
    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_triggerFrame.rgb");
    dump_frame(os->width, os->height, channel_count, image1, fname);
    write_metadata(fname, "sdsiiddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/triggerFrame",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "stackedFrames", 1);

    // The comparison frame which preceded the frame where the trigger was detected
    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_previousFrame.rgb");
    dump_frame(os->width, os->height, channel_count, image2, fname);
    write_metadata(fname, "sdsiiddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/previousFrame",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "stackedFrames", 1);

    // Copy the trigger frame into the stacked version of this trigger
    int j;
#pragma omp parallel for private(j)
    for (j = 0; j < os->frame_size * channel_count; j++) {
        os->event_list[i].stacked_image[j] = image1[j];
        os->event_list[i].max_stack[j] = image1[j];
    }

#pragma omp parallel for private(j)
    for (j = 0; j < os->frame_size; j++) {
        os->event_list[i].max_trigger[j] = os->trigger_map_rgb[2 * os->frame_size + j];
    }
}

// Check through list of events we are currently tracking.
// Weed out any which haven't been seen for a long time, or are exceeding maximum allowed recording time.
void register_trigger_ends(observe_status *os) {
    int i;
    unsigned char *current_frame = (os->video_buffer +
                                    (os->frame_counter % os->video_buffer_frames) * os->bytes_per_frame);

    const int channel_count = GREYSCALE_IMAGING ? 1 : 3;

    for (i = 0; i < MAX_EVENTS; i++)
        if (os->event_list[i].active == 1) {
            int j;

            // Three detections which span the whole duration of this event
            const int N0 = 0;
            const int N1 = os->event_list[i].detection_count / 2;
            const int N2 = os->event_list[i].detection_count - 1;

            // Create stack of the average brightness of each pixel over the duration of this event
#pragma omp parallel for private(j)
            for (j = 0; j < os->frame_size * channel_count; j++)
                os->event_list[i].stacked_image[j] += current_frame[j];

            // Create record of the maximum brightness of each pixel over the duration of this event
#pragma omp parallel for private(j)
            for (j = 0; j < os->frame_size * channel_count; j++) {
                const int x = current_frame[j];
                if (x > os->event_list[i].max_stack[j]) os->event_list[i].max_stack[j] = x;
            }

            // Has event exceeded TRIGGER_MAX_DURATION?
            const int max_event_frames = (int) (os->TRIGGER_MAX_DURATION * os->fps);
            const int event_too_long = (os->frame_counter >
                                        os->event_list[i].detections[N0].frame_count + max_event_frames);

            // Has event disappeared?
            const int event_disappeared = (os->frame_counter >
                                           os->event_list[i].detections[N2].frame_count +
                                           os->trigger_suffix_frame_count);

            // Test whether this event has ended
            if (event_too_long || event_disappeared) {

                // If event was not confirmed, take no further action
                if (!os->event_list[i].video_output.active) {
                    logging_info("Detection not confirmed.");
                    os->event_list[i].active = 0;
                    continue;
                }

                // Event is now only writing video
                os->event_list[i].active = 2;

                // Work out duration of event
                double duration = os->event_list[i].detections[N2].utc - os->event_list[i].detections[N0].utc;

                // Update counter for trigger rate throttling
                os->trigger_throttle_counter++;

                // Write path of event as JSON string
                char fname[FNAME_LENGTH], path_json[LSTR_LENGTH], path_bezier[FNAME_LENGTH];
                int amplitude_peak = 0, amplitude_time_integrated = 0;
                {
                    int j = 0, k = 0;
                    sprintf(path_json + k, "[");
                    k += strlen(path_json + k);
                    for (j = 0; j < os->event_list[i].detection_count; j++) {
                        const detection *d = &os->event_list[i].detections[j];
                        sprintf(path_json + k, "%s[%d,%d,%d,%.3f]", j ? "," : "", d->x, d->y, d->amplitude, d->utc);
                        k += strlen(path_json + k);
                        amplitude_time_integrated += d->amplitude;
                        if (d->amplitude > amplitude_peak) amplitude_peak = d->amplitude;
                    }
                    sprintf(path_json + k, "]");
                }

                // Dump stacked images of entire duration of event
                int coAddedFrames = (os->frame_counter - os->event_list[i].detections[0].frame_count);

                // Time-averaged value of each pixel over the duration of the event
                sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_timeAverage.rgb");
                dump_frame_from_ints(os->width, os->height, channel_count, os->event_list[i].stacked_image,
                                     coAddedFrames, 0, NULL, fname);
                write_metadata(fname, "sdsiiddidiii",
                               "obstoryId", os->obstory_id,
                               "utc", os->event_list[i].start_time,
                               "semanticType", "pigazing:movingObject/timeAverage",
                               "width", os->width,
                               "height", os->height,
                               "inputNoiseLevel", os->noise_level,
                               "stackNoiseLevel", os->noise_level / sqrt(coAddedFrames),
                               "stackedFrames", coAddedFrames,
                               "duration", duration,
                               "detectionCount", os->event_list[i].detection_count,
                               "amplitudeTimeIntegrated", amplitude_time_integrated,
                               "amplitudePeak", amplitude_peak);

                // Maximum brightness of each pixel over the duration of the event
                sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_maxBrightness.rgb");
                dump_frame_from_ints(os->width, os->height, channel_count, os->event_list[i].max_stack,
                                     1, 0, NULL, fname);
                write_metadata(fname, "sdsiiddidiii",
                               "obstoryId", os->obstory_id,
                               "utc", os->event_list[i].start_time,
                               "semanticType", "pigazing:movingObject/maximumBrightness",
                               "width", os->width,
                               "height", os->height,
                               "inputNoiseLevel", os->noise_level,
                               "stackNoiseLevel", os->noise_level / sqrt(coAddedFrames),
                               "stackedFrames", coAddedFrames,
                               "duration", duration,
                               "detectionCount", os->event_list[i].detection_count,
                               "amplitudeTimeIntegrated", amplitude_time_integrated,
                               "amplitudePeak", amplitude_peak);

                // Map of all pixels which triggered motion sensor over the duration of the event
                sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_allTriggers.rgb");
                dump_frame(os->width, os->height, 1, os->event_list[i].max_trigger, fname);
                write_metadata(fname, "sdsiiddidiii",
                               "obstoryId", os->obstory_id,
                               "utc", os->event_list[i].start_time,
                               "semanticType", "pigazing:movingObject/allTriggers",
                               "width", os->width,
                               "height", os->height,
                               "inputNoiseLevel", os->noise_level,
                               "stackNoiseLevel", 1.,
                               "stackedFrames", coAddedFrames,
                               "duration", duration,
                               "detectionCount", os->event_list[i].detection_count,
                               "amplitudeTimeIntegrated", amplitude_time_integrated,
                               "amplitudePeak", amplitude_peak);

                // Make sure that video of this event ends at the right time
                os->event_list[i].video_output.buffer_end_position = os->frame_counter % os->video_buffer_frames;

                // Write path of event as a three-point Bezier curve
                {
                    int k = 0;
                    sprintf(path_bezier + k, "[");
                    k += strlen(path_bezier + k);
                    sprintf(path_bezier + k, "[%d,%d,%.3f],", os->event_list[i].detections[N0].x,
                            os->event_list[i].detections[N0].y, os->event_list[i].detections[N0].utc);
                    k += strlen(path_bezier + k);
                    sprintf(path_bezier + k, "[%d,%d,%.3f],", os->event_list[i].detections[N1].x,
                            os->event_list[i].detections[N1].y, os->event_list[i].detections[N1].utc);
                    k += strlen(path_bezier + k);
                    sprintf(path_bezier + k, "[%d,%d,%.3f]", os->event_list[i].detections[N2].x,
                            os->event_list[i].detections[N2].y, os->event_list[i].detections[N2].utc);
                    k += strlen(path_bezier + k);
                    sprintf(path_bezier + k, "]");
                }

                // Now that we know the duration of this video, we can write metadata about the video file
                write_metadata(os->event_list[i].video_output.filename, "sdsiidsdiiiis",
                               "obstoryId", os->obstory_id,
                               "utc", os->event_list[i].start_time,
                               "semanticType", "pigazing:movingObject/video",
                               "width", os->width,
                               "height", os->height,
                               "inputNoiseLevel", os->noise_level,
                               "path", path_json,
                               "duration", duration,
                               "detectionCount", os->event_list[i].detection_count,
                               "detectionSignificance", os->event_list[i].detections[0].amplitude,
                               "amplitudeTimeIntegrated", amplitude_time_integrated,
                               "amplitudePeak", amplitude_peak,
                               "pathBezier", path_bezier
                );
            }
        }

    for (i = 0; i < MAX_EVENTS; i++)
        if (os->event_list[i].video_output.active) {
            const int still_going = dump_video_frame(
                    os->event_list[i].video_output.width, os->event_list[i].video_output.height,
                    os->video_buffer, os->video_buffer_frames,
                    &os->event_list[i].video_output.buffer_write_position,
                    &os->event_list[i].video_output.frames_written,
                    os->event_list[i].video_output.buffer_end_position,
                    os->event_list[i].video_output.file_handle
            );

            if (!still_going) {
                os->event_list[i].video_output.active = 0;
                os->event_list[i].active = 0;
            }
        }
}
