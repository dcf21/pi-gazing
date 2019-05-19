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

#define YUV420  3/2 /* Each pixel is 1.5 bytes in YUV420 stream */

// Generate a filename stub with a timestamp
char *filename_generate(char *output, const char *obstory_id, double utc, char *tag, const char *dir_name,
                        const char *label) {
    char path[FNAME_LENGTH];
    const double JD = utc / 86400.0 + 2440587.5;
    int year, month, day, hour, min, status;
    double sec;
    inv_julian_day(JD - 0.5, &year, &month, &day, &hour, &min, &sec, &status,
                   output); // Subtract 0.5 from Julian Day as we want days to start at noon, not midnight

    sprintf(path, "%s/analysis_products", OUTPUT_PATH);
    status = mkdir(path, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    if (status && (errno != EEXIST)) {
        sprintf(temp_err_string, "ERROR: Could not create directory <%s>. Returned error code %d. errno %d. %s.", path,
                status, errno, strerror(errno));
        logging_info(temp_err_string);
    }

    sprintf(path, "%s/analysis_products/%s_%s", OUTPUT_PATH, dir_name, label);
    status = mkdir(path, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
    if (status && (errno != EEXIST)) {
        sprintf(temp_err_string, "ERROR: Could not create directory <%s>. Returned error code %d. errno %d. %s.", path,
                status, errno, strerror(errno));
        logging_info(temp_err_string);
    }

    inv_julian_day(JD, &year, &month, &day, &hour, &min, &sec, &status, output);
    sprintf(output, "%s/%04d%02d%02d%02d%02d%02d_%s_%s", path, year, month, day, hour, min, (int) sec, obstory_id, tag);
    return output;
}

// Record metadata to accompany a file. filename must be writable.
void write_metadata(char *filename, char *item_types, ...) {
    // Change file extension to .txt
    int filename_len = (int) strlen(filename);
    int i = filename_len - 1;
    while ((i > 0) && (filename[i] != '.')) i--;
    sprintf(filename + i, ".txt");

    // Write metadata
    FILE *f = fopen(filename, "w");
    if (!f) return;
    va_list ap;
    va_start(ap, item_types);
    for (i = 0; item_types[i] != '\0'; i++) {
        char *x = va_arg(ap, char*);
        switch (item_types[i]) {
            case 's': {
                char *y = va_arg(ap, char*);
                fprintf(f, "%s %s\n", x, y);
                break;
            }
            case 'd': {
                double y = va_arg(ap, double);
                fprintf(f, "%s %.15e\n", x, y);
                break;
            }
            case 'i': {
                int y = va_arg(ap, int);
                fprintf(f, "%s %d\n", x, y);
                break;
            }
            default: {
                sprintf(temp_err_string, "ERROR: Unrecognised data type character '%c'.", item_types[i]);
                logging_fatal(__FILE__, __LINE__, temp_err_string);
            }
        }
    }
    va_end(ap);
    fclose(f);
}

// Read enough video (1 second) to create the stacks used to test for triggers
int read_frame_group(observe_status *os, unsigned char *buffer, int *stack1, int *stack2) {
    int i, j;

    // Stack1 is wiped prior to each call to this function
    memset(stack1, 0, os->frame_size * os->channel_count * sizeof(int));

    unsigned char *tmp_rgb;
    if (!GREYSCALE_IMAGING) tmp_rgb = malloc((size_t) (os->channel_count * os->frame_size));

    for (j = 0; j < os->TRIGGER_FRAMEGROUP; j++) {
        unsigned char *tmpc = buffer + j * os->frame_size * YUV420;
        if (GREYSCALE_IMAGING) tmp_rgb = tmpc;
        if ((*os->fetch_frame)(os->video_handle, tmpc, &os->utc) != 0) {
            if (DEBUG) logging_info("Error grabbing");
            return 1;
        }
        if (!GREYSCALE_IMAGING)
            Pyuv420torgb(tmpc, tmpc + os->frame_size, tmpc + os->frame_size * 5 / 4, tmp_rgb, tmp_rgb + os->frame_size,
                         tmp_rgb + os->frame_size * 2, os->width, os->height);
#pragma omp parallel for private(i)
        for (i = 0; i < os->frame_size * os->channel_count; i++) stack1[i] += tmp_rgb[i];
    }

    if (stack2) {
#pragma omp parallel for private(i)
        for (i = 0; i < os->frame_size * os->channel_count; i++)
            stack2[i] += stack1[i]; // Stack2 can stack output of many calls to this function
    }

    // Add the pixel values in this stack into the histogram in background_workspace
    const int include_in_background_histograms = (
                                                         (os->background_count %
                                                          os->background_map_use_every_nth_stack) == 0) &&
                                                 (os->background_count < os->background_map_use_n_images *
                                                                         os->background_map_use_every_nth_stack);
    if (include_in_background_histograms) {
#pragma omp parallel for private(j)
        for (j = 0; j < os->frame_size * os->channel_count; j++) {
            int d;
            int pixelVal = CLIP256(stack1[j] / os->TRIGGER_FRAMEGROUP);
            os->background_workspace[j * 256 + pixelVal]++;
        }
    }
    if (!GREYSCALE_IMAGING) free(tmp_rgb);
    return 0;
}

int observe(void *video_handle, const char *obstory_id, const double utc_start, const double utc_stop,
            const int width, const int height, const double fps, const char *label, const unsigned char *mask,
            const int channel_count, const int STACK_COMPARISON_INTERVAL, const int TRIGGER_PREFIX_TIME,
            const int TRIGGER_SUFFIX_TIME, const int TRIGGER_FRAMEGROUP, const int TRIGGER_MAXRECORDLEN,
            const int TRIGGER_THROTTLE_PERIOD, const int TRIGGER_THROTTLE_MAXEVT, const int TIMELAPSE_EXPOSURE,
            const int TIMELAPSE_INTERVAL, const int STACK_TARGET_BRIGHTNESS,
            const int background_map_use_every_nth_stack, const int background_map_use_n_images,
            const int background_map_reduction_cycles,
            int (*fetch_frame)(void *, unsigned char *, double *), int (*rewind_video)(void *, double *)) {
    int i;
    char line[FNAME_LENGTH], line2[FNAME_LENGTH], line3[FNAME_LENGTH];

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
    os->channel_count = channel_count;

    os->STACK_COMPARISON_INTERVAL = STACK_COMPARISON_INTERVAL;
    os->TRIGGER_PREFIX_TIME = TRIGGER_PREFIX_TIME;
    os->TRIGGER_SUFFIX_TIME = TRIGGER_SUFFIX_TIME;
    os->TRIGGER_FRAMEGROUP = TRIGGER_FRAMEGROUP;
    os->TRIGGER_MAXRECORDLEN = TRIGGER_MAXRECORDLEN;
    os->TRIGGER_THROTTLE_PERIOD = TRIGGER_THROTTLE_PERIOD;
    os->TRIGGER_THROTTLE_MAXEVT = TRIGGER_THROTTLE_MAXEVT;
    os->TIMELAPSE_EXPOSURE = TIMELAPSE_EXPOSURE;
    os->TIMELAPSE_INTERVAL = TIMELAPSE_INTERVAL;
    os->STACK_TARGET_BRIGHTNESS = STACK_TARGET_BRIGHTNESS;

    os->background_map_use_every_nth_stack = background_map_use_every_nth_stack;
    os->background_map_use_n_images = background_map_use_n_images;
    os->background_map_reduction_cycles = background_map_reduction_cycles;

    // Trigger buffers. These are used to store 1 second of video for comparison with the next
    os->buffer_group_count = (int) (os->fps * os->TRIGGER_MAXRECORDLEN / os->TRIGGER_FRAMEGROUP);
    os->buffer_group_bytes = os->TRIGGER_FRAMEGROUP * os->frame_size * YUV420;
    os->buffer_frame_count = os->buffer_group_count * os->TRIGGER_FRAMEGROUP;
    os->buffer_length = os->buffer_group_count * os->buffer_group_bytes;
    os->buffer = malloc((size_t) os->buffer_length);
    for (i = 0; i <= os->STACK_COMPARISON_INTERVAL; i++) {
        os->stack[i] = malloc(os->frame_size * sizeof(int) *
                              os->channel_count); // A stacked version of the current and preceding frame group; used to form a difference image
        if (!os->stack[i]) {
            sprintf(temp_err_string, "ERROR: malloc fail in observe.");
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }
    }

    os->trigger_prefix_group_count = (int) (os->TRIGGER_PREFIX_TIME * os->fps / os->TRIGGER_FRAMEGROUP);
    os->trigger_suffix_group_count = (int) (os->TRIGGER_SUFFIX_TIME * os->fps / os->TRIGGER_FRAMEGROUP);

    // Timelapse buffers
    os->utc = 0;
    os->timelapse_utc_start = 1e40; // Store timelapse exposures at set intervals. This is UTC of next frame, but we don't start until we've done a run-in period
    os->frames_timelapse = (int) (os->fps * os->TIMELAPSE_EXPOSURE);
    os->stackT = malloc(os->frame_size * sizeof(int) * os->channel_count);

    // Background maps are used for background subtraction. Maps A and B are used alternately and contain the background value of each pixel.
    // Holds the background value of each pixel, sampled over 255 stacked images
    os->background_map = calloc(1, (size_t) (os->frame_size * os->channel_count));

    // Workspace which counts the number of times any given pixel has a particular value
    os->background_workspace = calloc(1, (size_t) (os->frame_size * os->channel_count * 256 * sizeof(int)));

    // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
    os->past_trigger_map = calloc(1, os->frame_size * sizeof(int));

    // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
    os->trigger_map = calloc(1, os->frame_size *
                                sizeof(int)); // 2D array of ints used to mark out pixels which have brightened suspiciously.
    os->trigger_rgb = calloc(1, (size_t) (os->frame_size * 3));

    os->trigger_block_count = calloc(1, MAX_TRIGGER_BLOCKS *
                                        sizeof(int)); // Count of how many pixels are in each numbered connected block
    os->trigger_block_top = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_bot = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_sumx = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_sumy = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_suml = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));
    os->trigger_block_redirect = calloc(1, MAX_TRIGGER_BLOCKS * sizeof(int));

    if ((!os->buffer) ||
        (!os->stackT) ||
        (!os->background_map) || (!os->background_workspace) || (!os->past_trigger_map) ||
        (!os->trigger_map) || (!os->trigger_rgb) ||
        (!os->trigger_block_count) || (!os->trigger_block_top) || (!os->trigger_block_bot) ||
        (!os->trigger_block_sumx) ||
        (!os->trigger_block_sumy) || (!os->trigger_block_suml) || (!os->trigger_block_redirect)
            ) {
        sprintf(temp_err_string, "ERROR: malloc fail in observe.");
        logging_fatal(__FILE__, __LINE__, temp_err_string);
    }

    for (i = 0; i < MAX_EVENTS; i++) {
        os->event_list[i].stacked_image = malloc(os->frame_size * os->channel_count * sizeof(int));
        os->event_list[i].max_stack = malloc(os->frame_size * os->channel_count * sizeof(int));
        if ((!os->event_list[i].stacked_image) || (!os->event_list[i].max_stack)) {
            sprintf(temp_err_string, "ERROR: malloc fail in observe.");
            logging_fatal(__FILE__, __LINE__, temp_err_string);
        }
    }

    for (i = 0; i < MAX_EVENTS; i++) {
        os->video_outputs[i].active = 0;
    }

    // Flag for whether we're feeding images into stackA or stackB
    os->group_number = 0;

    // Count how many frames we've fed into the brightness histograms in background_workspace
    os->background_count = 0;

    // Count how many frames have been stacked into the timelapse buffer (stackT)
    os->timelapse_count = -1;
    os->frame_counter = 0;

    // Let the camera run for a period before triggering, as it takes this long to make first background map
    os->run_in_countdown = 8 + os->background_map_reduction_cycles + os->background_map_use_every_nth_stack *
                                                                     os->background_map_use_n_images;
    os->noise_level = 128;

    // Trigger throttling
    os->trigger_throttle_timer = 0;
    os->trigger_throttle_counter = 0;

    // Reset trigger throttle counter after this many frame groups have been processed
    os->trigger_throttle_period = (int) (os->TRIGGER_THROTTLE_PERIOD * 60. * os->fps / os->TRIGGER_FRAMEGROUP);

    // Processing loop
    while (1) {
        int t = (int) (time(NULL));
        if (t >= utc_stop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!

        // Once we've done initial run-in period, rewind the tape to the beginning if we can
        if (os->run_in_countdown && !--os->run_in_countdown) {
            if (DEBUG) {
                sprintf(line, "Run-in period completed.");
                logging_info(line);
            }
            (*rewind_video)(os->video_handle, &os->utc);
            os->timelapse_utc_start = ceil(os->utc / 60) * 60 + 0.5; // Start making timelapse video
        }

        // Work out where we're going to read next second of video to. Either bufferA / bufferB, or the long buffer if we're recording
        unsigned char *buffer_pos = os->buffer + (os->frame_counter % os->buffer_group_count) * os->buffer_group_bytes;

        // Once on each cycle through the video buffer, estimate the thermal noise of the camera
        if (buffer_pos == os->buffer) os->noise_level = estimate_noise_level(os->width, os->height, os->buffer, 16);

        // Read the next second of video
        int status = read_frame_group(os, buffer_pos,
                                      os->stack[os->frame_counter % (os->STACK_COMPARISON_INTERVAL + 1)],
                                      (os->timelapse_count >= 0) ? os->stackT : NULL);
        if (status) break; // We've run out of video

        // If we've stacked enough frames since we last made a background map, make a new background map
        os->background_count++;
        if (os->background_count >= os->background_map_use_n_images * os->background_map_use_every_nth_stack) {
            const int reduction_cycle = (
                    os->background_count - os->background_map_use_n_images * os->background_map_use_every_nth_stack);
            background_calculate(os->width, os->height, os->channel_count, reduction_cycle,
                                 os->background_map_reduction_cycles,
                                 os->background_workspace, os->background_map);
            if (reduction_cycle >= os->background_map_reduction_cycles) {
                os->background_count = 0;
                memset(os->background_workspace, 0, os->frame_size * os->channel_count * 256 * sizeof(int));
            }
        }

        // Periodically, dump a stacked timelapse exposure lasting for <secondsTimelapseBuff> seconds
        if (os->timelapse_count >= 0) { os->timelapse_count++; }
        else if (os->utc > os->timelapse_utc_start) {
            memset(os->stackT, 0, os->frame_size * os->channel_count * sizeof(int));
            os->timelapse_count = 0;
        }

        // If timelapse exposure is finished, dump it
        if ((os->timelapse_count >= os->frames_timelapse / os->TRIGGER_FRAMEGROUP) ||
            (os->utc > os->timelapse_utc_start + os->TIMELAPSE_INTERVAL - 1)) {
            const int Nframes = os->timelapse_count * os->TRIGGER_FRAMEGROUP;
            char fstub[FNAME_LENGTH], fname[FNAME_LENGTH];
            int gainFactor;

            filename_generate(fstub, os->obstory_id, os->timelapse_utc_start, "frame_", "timelapse", os->label);

            sprintf(fname, "%s%s", fstub, "BS0.rgb");
            dump_frame_from_ints(os->width, os->height, os->channel_count, os->stackT, Nframes,
                                 os->STACK_TARGET_BRIGHTNESS, &gainFactor, fname);
            write_metadata(fname, "sdsddii",
                           "obstoryId", os->obstory_id,
                           "utc", os->timelapse_utc_start,
                           "semanticType", "pigazing:timelapse",
                           "inputNoiseLevel", os->noise_level,
                           "stackNoiseLevel", os->noise_level / sqrt(Nframes) * gainFactor,
                           "gainFactor", gainFactor,
                           "stackedFrames", Nframes);

            sprintf(fname, "%s%s", fstub, "BS1.rgb");
            dump_frame_from_int_subtraction(os->width, os->height, os->channel_count, os->stackT, Nframes,
                                            os->STACK_TARGET_BRIGHTNESS, &gainFactor,
                                            os->background_map, fname);
            write_metadata(fname, "sdsddii",
                           "obstoryId", os->obstory_id,
                           "utc", os->timelapse_utc_start,
                           "semanticType", "pigazing:timelapse/backgroundSubtracted",
                           "inputNoiseLevel", os->noise_level,
                           "stackNoiseLevel", os->noise_level / sqrt(Nframes) * gainFactor,
                           "gainFactor", gainFactor,
                           "stackedFrames", Nframes);

            // Every 15 minutes, dump an image of the sky background map for diagnostic purposes
            if (floor(fmod(os->timelapse_utc_start, 900)) == 0) {
                sprintf(fname, "%s%s", fstub, "skyBackground.rgb");
                dump_frame(os->width, os->height, os->channel_count, os->background_map, fname);
                write_metadata(fname, "sdsddi",
                               "obstoryId", os->obstory_id,
                               "utc", os->timelapse_utc_start,
                               "semanticType", "pigazing:timelapse/backgroundModel",
                               "inputNoiseLevel", os->noise_level,
                               "stackNoiseLevel", 1.,
                               "stackedFrames", ((int) os->background_map_use_n_images));
            }
            os->timelapse_utc_start += os->TIMELAPSE_INTERVAL;
            os->timelapse_count = -1;
        }

        // Update counters for trigger throttling
        os->trigger_throttle_timer++;
        const int trigger_throttle_cycles = (int) (os->TRIGGER_THROTTLE_PERIOD * 60 * os->fps / os->TRIGGER_FRAMEGROUP);
        if (os->trigger_throttle_timer >= trigger_throttle_cycles) {
            os->trigger_throttle_timer = 0;
            os->trigger_throttle_counter = 0;
        }

        // Test whether motion sensor has triggered
        os->triggering_allowed = ((!os->run_in_countdown) &&
                                  (os->trigger_throttle_counter < os->TRIGGER_THROTTLE_MAXEVT));
        register_trigger_ends(os);
        int *image_new = os->stack[os->frame_counter % (os->STACK_COMPARISON_INTERVAL + 1)];
        int *image_old = os->stack[(os->frame_counter + os->STACK_COMPARISON_INTERVAL) %
                                   (os->STACK_COMPARISON_INTERVAL + 1)];
        check_for_triggers(os, image_new, image_old, os->TRIGGER_FRAMEGROUP);

        os->frame_counter++;
        os->group_number = !os->group_number;
    }

    for (i = 0; i <= os->STACK_COMPARISON_INTERVAL; i++) free(os->stack[i]);
    for (i = 0; i < MAX_EVENTS; i++) {
        free(os->event_list[i].stacked_image);
        free(os->event_list[i].max_stack);
    }
    free(os->trigger_map);
    free(os->trigger_block_count);
    free(os->trigger_block_sumx);
    free(os->trigger_block_sumy);
    free(os->trigger_block_suml);
    free(os->trigger_block_redirect);
    free(os->trigger_rgb);
    free(os->buffer);
    free(os->stackT);
    free(os->background_map);
    free(os->background_workspace);
    free(os->past_trigger_map);
    free(os);
    return 0;
}

// Register a new trigger event
void register_trigger(observe_status *os, const int block_id, const int x_pos, const int y_pos, const int pixel_count,
                      const int amplitude, const int *image1, const int *image2, const int coadded_frames) {
    int i, closest_trigger = -1, closest_trigger_dist = 9999;
    if (!os->triggering_allowed) return;

    // Cycle through objects we are tracking to find nearest one
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
    if (closest_trigger_dist < 70) {
        const int i = closest_trigger;
        const int n = os->event_list[i].detection_count - 1;
        if (os->event_list[i].detections[n].frame_count ==
            os->frame_counter) // Has this object already been seen in this frame?
        {
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

    for (i = 0; i < MAX_EVENTS; i++) if (!os->event_list[i].active) break;
    if (i >= MAX_EVENTS) {
        logging_info("Ignoring trigger; no event descriptors available.");
        return;
    } // No free event storage space

    // Colour in block of pixels which have triggered in schematic trigger map
    int k;
    for (k = 1; k <= os->block_count; k++) {
        int k2 = k;
        while (os->trigger_block_redirect[k2] > 0) k2 = os->trigger_block_redirect[k2];
        if (k2 == block_id) {
            unsigned char *triggerB = os->trigger_rgb + os->frame_size * 2;
            int j;
#pragma omp parallel for private(j)
            for (j = 0; j < os->frame_size; j++) if (os->trigger_map[j] == k2) triggerB[j] *= 4;
        }
    }

    // Register event in events table
    os->event_list[i].active = 1;
    os->event_list[i].detection_count = 1;
    os->event_list[i].start_time = os->utc;
    detection *d = &os->event_list[i].detections[0];
    d->frame_count = os->frame_counter;
    d->x = x_pos;
    d->y = y_pos;
    d->utc = os->utc;
    d->pixel_count = pixel_count;
    d->amplitude = amplitude;

    char fname[FNAME_LENGTH];

    filename_generate(os->event_list[i].filename_stub, os->obstory_id, os->utc, "event", "triggers", os->label);

    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_mapDifference.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_rgb + 0 * os->frame_size, fname);
    write_metadata(fname, "sdsddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/mapDifference",
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "stackedFrames", 1);

    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_mapExcludedPixels.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_rgb + 1 * os->frame_size, fname);
    write_metadata(fname, "sdsddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/mapExcludedPixels",
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "stackedFrames", 1);

    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_mapTrigger.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_rgb + 2 * os->frame_size, fname);
    write_metadata(fname, "sdsddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/mapTrigger",
                   "inputNoiseLevel", os->noise_level, "stackNoiseLevel",
                   os->noise_level, "stackedFrames", 1);

    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_triggerFrame.rgb");
    dump_frame_from_ints(os->width, os->height, os->channel_count, image1, coadded_frames, 0, NULL, fname);
    write_metadata(fname, "sdsddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/triggerFrame",
                   "inputNoiseLevel", os->noise_level, "stackNoiseLevel",
                   os->noise_level / sqrt(coadded_frames), "stackedFrames", coadded_frames);

    sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_previousFrame.rgb");
    dump_frame_from_ints(os->width, os->height, os->channel_count, image2, coadded_frames, 0, NULL, fname);
    write_metadata(fname, "sdsddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[i].start_time,
                   "semanticType", "pigazing:movingObject/previousFrame",
                   "inputNoiseLevel", os->noise_level, "stackNoiseLevel",
                   os->noise_level / sqrt(coadded_frames), "stackedFrames", coadded_frames);

    memcpy(os->event_list[i].stacked_image, image1, os->frame_size * os->channel_count * sizeof(int));
    int j;
#pragma omp parallel for private(j)
    for (j = 0; j < os->frame_size * os->channel_count; j++) os->event_list[i].max_stack[j] = image1[j];
}

// Check through list of events we are currently tracking.
// Weed out any which haven't been seen for a long time, or are exceeding maximum allowed recording time.
void register_trigger_ends(observe_status *os) {
    int i;
    int *stackbuf = os->stack[os->frame_counter % (os->STACK_COMPARISON_INTERVAL + 1)];
    for (i = 0; i < MAX_EVENTS; i++)
        if (os->event_list[i].active) {
            int j;
            const int N0 = 0;
            const int N1 = os->event_list[i].detection_count / 2;
            const int N2 = os->event_list[i].detection_count - 1;
#pragma omp parallel for private(j)
            for (j = 0; j < os->frame_size * os->channel_count; j++) os->event_list[i].stacked_image[j] += stackbuf[j];
#pragma omp parallel for private(j)
            for (j = 0; j < os->frame_size * os->channel_count; j++) {
                const int x = stackbuf[j];
                if (x > os->event_list[i].max_stack[j]) os->event_list[i].max_stack[j] = x;
            }

            if ((os->event_list[i].detections[N0].frame_count <=
                 (os->frame_counter - (os->buffer_group_count - os->trigger_prefix_group_count))) ||
                // Event is exceeding TRIGGER_MAXRECORDLEN?
                (os->event_list[i].detections[N2].frame_count <= (os->frame_counter -
                                                                  os->trigger_suffix_group_count))) // ... or event hasn't been seen for TRIGGER_SUFFIXTIME?
            {
                os->event_list[i].active = 0;

                // If event was seen in fewer than two frames, reject it
                if (os->event_list[i].detection_count < 2) continue;

                // Work out duration of event
                double duration = os->event_list[i].detections[N2].utc - os->event_list[i].detections[N0].utc;
                double pixel_track_len = hypot(os->event_list[i].detections[N0].x - os->event_list[i].detections[N2].x,
                                               os->event_list[i].detections[N0].y - os->event_list[i].detections[N2].y);

                if (pixel_track_len < 4) continue; // Reject events that don't move much -- probably a twinkling star

                // Update counter for trigger rate throttling
                os->trigger_throttle_counter++;

                // Dump stacked images of entire duration of event
                int coAddedFrames =
                        (os->frame_counter - os->event_list[i].detections[0].frame_count) * os->TRIGGER_FRAMEGROUP;
                char fname[FNAME_LENGTH], path_json[LSTR_LENGTH], path_bezier[FNAME_LENGTH];

                sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_timeAverage.rgb");
                dump_frame_from_ints(os->width, os->height, os->channel_count, os->event_list[i].stacked_image,
                                     coAddedFrames, 0, NULL,
                                     fname);
                write_metadata(fname, "sdsddi",
                               "obstoryId", os->obstory_id,
                               "utc", os->event_list[i].start_time,
                               "semanticType", "pigazing:movingObject/timeAverage",
                               "inputNoiseLevel", os->noise_level,
                               "stackNoiseLevel", os->noise_level / sqrt(coAddedFrames),
                               "stackedFrames", coAddedFrames);

                sprintf(fname, "%s%s", os->event_list[i].filename_stub, "_maxBrightness.rgb");
                dump_frame_from_ints(os->width, os->height, os->channel_count, os->event_list[i].max_stack,
                                     os->TRIGGER_FRAMEGROUP, 0, NULL, fname);
                write_metadata(fname, "sdsddi",
                               "obstoryId", os->obstory_id,
                               "utc", os->event_list[i].start_time,
                               "semanticType", "pigazing:movingObject/maximumBrightness",
                               "inputNoiseLevel", os->noise_level,
                               "stackNoiseLevel", os->noise_level / sqrt(coAddedFrames),
                               "stackedFrames", coAddedFrames);

                // Dump a video of the meteor from our video buffer
                int video_frame_count =
                        (os->frame_counter - os->event_list[i].detections[N0].frame_count +
                         os->trigger_prefix_group_count) *
                        os->TRIGGER_FRAMEGROUP;
                unsigned char *bufferPos =
                        os->buffer + (os->frame_counter % os->buffer_group_count) * os->buffer_group_bytes;
                unsigned char *video1 = NULL;
                int video1frs = 0;
                unsigned char *video2 = bufferPos - video_frame_count * os->frame_size * YUV420;
                int video2frs = video_frame_count;

                // Video spans a buffer wrap-around, so need to include two chunks of video data
                if (video2 < os->buffer) {
                    video2frs = (bufferPos - os->buffer) / (os->frame_size * YUV420);
                    video1frs = video_frame_count - video2frs;
                    video1 = video2 + os->buffer_length;
                    video2 = os->buffer;
                }

                // Write path of event as JSON string
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
                    k += strlen(path_json + k);
                }

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
                    k += strlen(path_bezier + k);
                }

                // Start process of exporting video of this event
                {
                    int k = 0;
                    for (k = 0; k < MAX_EVENTS; k++) if (!os->video_outputs[k].active) break;
                    if (k >= MAX_EVENTS) {
                        logging_info("Ignoring video; already writing too many video files at once.");
                    } // No free event storage space
                    else {
                        sprintf(fname, "%s%s", os->event_list[i].filename_stub, ".vid");
                        os->video_outputs[k].width = os->width;
                        os->video_outputs[k].height = os->height;
                        os->video_outputs[k].buffer1 = video1;
                        os->video_outputs[k].buffer1_frames = video1frs;
                        os->video_outputs[k].buffer2 = video2;
                        os->video_outputs[k].buffer2_frames = video2frs;
                        strcpy(os->video_outputs[k].fName, fname);
                        os->video_outputs[k].frames_written = 0;
                        os->video_outputs[k].active = 1;

                        os->video_outputs[k].file_handle = dump_video_init(os->width, os->height, video1, video1frs,
                                                                           video2, video2frs, fname);

                        write_metadata(fname, "sdsdsdiiis",
                                       "obstoryId", os->obstory_id,
                                       "utc", os->event_list[i].start_time,
                                       "semanticType", "pigazing:movingObject/video",
                                       "inputNoiseLevel", os->noise_level,
                                       "path", path_json,
                                       "duration", duration,
                                       "detectionCount", os->event_list[i].detection_count,
                                       "amplitude_time_integrated", amplitude_time_integrated,
                                       "amplitude_peak", amplitude_peak,
                                       "path_bezier", path_bezier
                        );
                    }
                }
            }
        }

    for (i = 0; i < MAX_EVENTS; i++)
        if (os->video_outputs[i].active) {
            os->video_outputs[i].active =
                    dump_video_frame(os->video_outputs[i].width, os->video_outputs[i].height,
                                     os->video_outputs[i].buffer1, os->video_outputs[i].buffer1_frames,
                                     os->video_outputs[i].buffer2, os->video_outputs[i].buffer2_frames,
                                     os->video_outputs[i].file_handle, &os->video_outputs[i].frames_written);
        }
}
