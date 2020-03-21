// write_output.c
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

#include "settings.h"
#include "vidtools/color.h"
#include "utils/julianDate.h"
#include "utils/error.h"
#include "utils/tools.h"
#include "utils/asciiDouble.h"
#include "analyse/trigger.h"
#include "analyse/observe.h"
#include "str_constants.h"
#include <time.h>
#include <math.h>
#include <errno.h>
#include <sys/stat.h>
#include <unistd.h>
#include <string.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>
#include "write_output.h"

//! filename_generate - Generate a filename for an output product. We place output products in the directory
//! <datadir/analysis_products>. Within this, we create directories of the form <dir_name>_<label>, where label is
//! either "live" or "nonlive", for real-time and post-observation video analysis. The file products themselves have
//! filenames which start with a time stamp string, followed by the observatory ID, followed by <tag>.
//!
//! These filenames do not have file type suffices, which the user will need to add afterwards.
//!
//! \param [out] output The string buffer into which to write the filename for this product.
//! \param [in] obstory_id The observatory ID which created this product.
//! \param [in] utc The time stamp of the product.
//! \param [in] tag The type of file, used as the last part of the filename
//! \param [in] dir_name The name of the directory within <analysis_products> where this product should go.
//! \param [in] label Suffix to the name of the directory; either "live" or "nonlive".
//! \return Pointer to <output>.

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

//! write_metadata - Record metadata associated with each output file product into a metadata text file which sits
//! alongside the file product, but with a '.txt' file extension.
//! \param filename The filename of the file product that we are going to write metadata for. This character array
//! must be writable, since we change the filename suffix to '.txt' in place, in order to write the metadata into a
//! text file alongside the file product.
//! \param item_types A string representing the list of types of the metadata items to write into the file. The
//! character 's' represents a string item, 'i' represents an integer value, and 'd' represents a double
//! (floating point).
//! \param ... For each character in the <item_types> string, two additional parameters are required. The first should
//! be a string containing the keyword associated with the metadata item, while the latter is the metadata value.

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

void write_timelapse_frame(const int channel_count, const observe_status *os, const int frame_count,
                           const char *filename_stub) {
    char fname[FNAME_LENGTH];
    double gain_factor;
    sprintf(fname, "%s%s", filename_stub, "BS0.rgb");
    dump_frame_from_ints(os->width, os->height, channel_count, os->stack_timelapse, frame_count,
                         os->STACK_TARGET_BRIGHTNESS, &gain_factor, fname);

    // Store metadata about the time-lapse frame
    write_metadata(fname, "sdsiiddddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->timelapse_utc_start,
                   "semanticType", "pigazing:timelapse",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level / sqrt(frame_count) * gain_factor,
                   "meanLevel", os->mean_level,
                   "gainFactor", gain_factor,
                   "stackedFrames", frame_count);
}

void write_timelapse_bs_frame(const int channel_count, const observe_status *os, const int frame_count,
                              const char *filename_stub) {
    char fname[FNAME_LENGTH];
    double gain_factor;
    sprintf(fname, "%s%s", filename_stub, "BS1.rgb");
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
}

void write_timelapse_bg_model(const int BACKGROUND_MAP_FRAMES, const int channel_count, const observe_status *os,
                              const char *filename_stub) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", filename_stub, "skyBackground.rgb");
    dump_frame_from_ints(os->width, os->height, channel_count, os->background_maps[0],
                         256, 0, NULL, fname);
    write_metadata(fname, "sdsiidddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->timelapse_utc_start,
                   "semanticType", "pigazing:timelapse/backgroundModel",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level / sqrt(BACKGROUND_MAP_FRAMES),
                   "meanLevel", os->mean_level,
                   "stackedFrames", ((int) BACKGROUND_MAP_FRAMES));
}

void write_trigger_difference_frame(const observe_status *os, const int trigger_index) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", os->event_list[trigger_index].filename_stub, "_mapDifference.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_map_rgb + 0 * os->frame_size, fname);
    write_metadata(fname, "sdsiidddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/mapDifference",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "meanLevel", os->mean_level,
                   "stackedFrames", 1);
}

void write_trigger_mask_frame(const observe_status *os, const int trigger_index) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", os->event_list[trigger_index].filename_stub, "_mapExcludedPixels.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_map_rgb + 1 * os->frame_size, fname);
    write_metadata(fname, "sdsiidddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/mapExcludedPixels",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "meanLevel", os->mean_level,
                   "stackedFrames", 1);
}

void write_trigger_map_frame(const observe_status *os, const int trigger_index) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", os->event_list[trigger_index].filename_stub, "_mapTrigger.rgb");
    dump_frame(os->width, os->height, 1, os->trigger_map_rgb + 2 * os->frame_size, fname);
    write_metadata(fname, "sdsiidddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/mapTrigger",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "meanLevel", os->mean_level,
                   "stackedFrames", 1);
}

void write_trigger_frame(const observe_status *os, const unsigned char *image1, const int channel_count,
                         const int trigger_index) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", os->event_list[trigger_index].filename_stub, "_triggerFrame.rgb");
    dump_frame(os->width, os->height, channel_count, image1, fname);
    write_metadata(fname, "sdsiidddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/triggerFrame",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "meanLevel", os->mean_level,
                   "stackedFrames", 1);
}

void write_trigger_previous_frame(const observe_status *os, const unsigned char *image2, const int channel_count,
                                  const int trigger_index) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", os->event_list[trigger_index].filename_stub, "_previousFrame.rgb");
    dump_frame(os->width, os->height, channel_count, image2, fname);
    write_metadata(fname, "sdsiidddi",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/previousFrame",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level,
                   "meanLevel", os->mean_level,
                   "stackedFrames", 1);
}

void write_trigger_time_average_frame(const observe_status *os, int trigger_index, const int channel_count,
                                      const double duration, int amplitude_peak, int amplitude_time_integrated,
                                      int integrated_frame_count) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", os->event_list[trigger_index].filename_stub, "_timeAverage.rgb");
    dump_frame_from_ints(os->width, os->height, channel_count, os->event_list[trigger_index].stacked_image,
                         integrated_frame_count, 0, NULL, fname);
    write_metadata(fname, "sdsiidddidiii",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/timeAverage",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level / sqrt(integrated_frame_count),
                   "meanLevel", os->mean_level,
                   "stackedFrames", integrated_frame_count,
                   "duration", duration,
                   "detectionCount", os->event_list[trigger_index].detection_count,
                   "amplitudeTimeIntegrated", amplitude_time_integrated,
                   "amplitudePeak", amplitude_peak);
}

void write_trigger_max_brightness_frame(const observe_status *os, int trigger_index, const int channel_count,
                                        const double duration, int amplitude_peak, int amplitude_time_integrated,
                                        int integrated_frame_count) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", os->event_list[trigger_index].filename_stub, "_maxBrightness.rgb");
    dump_frame_from_ints(os->width, os->height, channel_count, os->event_list[trigger_index].max_stack,
                         1, 0, NULL, fname);
    write_metadata(fname, "sdsiidddidiii",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/maximumBrightness",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "stackNoiseLevel", os->noise_level / sqrt(integrated_frame_count),
                   "meanLevel", os->mean_level,
                   "stackedFrames", integrated_frame_count,
                   "duration", duration,
                   "detectionCount", os->event_list[trigger_index].detection_count,
                   "amplitudeTimeIntegrated", amplitude_time_integrated,
                   "amplitudePeak", amplitude_peak);
}

void write_trigger_integrated_trigger_map(const observe_status *os, int trigger_index,
                                          const double duration, int amplitude_peak, int amplitude_time_integrated,
                                          int integrated_frame_count) {
    char fname[FNAME_LENGTH];
    sprintf(fname, "%s%s", os->event_list[trigger_index].filename_stub, "_allTriggers.rgb");
    dump_frame(os->width, os->height, 1, os->event_list[trigger_index].max_trigger, fname);
    write_metadata(fname, "sdsiidddidiii",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/allTriggers",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "meanLevel", os->mean_level,
                   "stackNoiseLevel", 1.,
                   "stackedFrames", integrated_frame_count,
                   "duration", duration,
                   "detectionCount", os->event_list[trigger_index].detection_count,
                   "amplitudeTimeIntegrated", amplitude_time_integrated,
                   "amplitudePeak", amplitude_peak);
}

void write_video_metadata(observe_status *os, int trigger_index) {
    // Three detections which span the whole duration of this event
    const int N0 = 0;
    const int N1 = os->event_list[trigger_index].detection_count / 2;
    const int N2 = os->event_list[trigger_index].detection_count - 1;

    // Work out duration of event
    const double duration =
            os->event_list[trigger_index].detections[N2].utc - os->event_list[trigger_index].detections[N0].utc;
    const int duration_frames =
            os->event_list[trigger_index].detections[N2].frame_count -
            os->event_list[trigger_index].detections[N0].frame_count;

    // Write path of event as JSON string
    char path_json[LSTR_LENGTH], path_bezier[FNAME_LENGTH];
    int amplitude_peak = 0, amplitude_time_integrated = 0;
    {
        int j = 0, k = 0;
        sprintf(path_json + k, "[");
        k += strlen(path_json + k);
        for (j = 0; j < os->event_list[trigger_index].detection_count; j++) {
            const detection *d = &os->event_list[trigger_index].detections[j];
            sprintf(path_json + k, "%s[%d,%d,%d,%.3f]", j ? "," : "", d->x, d->y, d->amplitude, d->utc);
            k += strlen(path_json + k);
            amplitude_time_integrated += d->amplitude;
            if (d->amplitude > amplitude_peak) amplitude_peak = d->amplitude;
        }
        sprintf(path_json + k, "]");
    }

    // Write path of event as a three-point Bezier curve
    {
        int k = 0;
        sprintf(path_bezier + k, "[");
        k += strlen(path_bezier + k);
        sprintf(path_bezier + k, "[%d,%d,%.3f],", os->event_list[trigger_index].detections[N0].x,
                os->event_list[trigger_index].detections[N0].y, os->event_list[trigger_index].detections[N0].utc);
        k += strlen(path_bezier + k);
        sprintf(path_bezier + k, "[%d,%d,%.3f],", os->event_list[trigger_index].detections[N1].x,
                os->event_list[trigger_index].detections[N1].y, os->event_list[trigger_index].detections[N1].utc);
        k += strlen(path_bezier + k);
        sprintf(path_bezier + k, "[%d,%d,%.3f]", os->event_list[trigger_index].detections[N2].x,
                os->event_list[trigger_index].detections[N2].y, os->event_list[trigger_index].detections[N2].utc);
        k += strlen(path_bezier + k);
        sprintf(path_bezier + k, "]");
    }

    // Now that we know the duration of this video, we can write metadata about the video file
    const double video_duration = os->utc - (os->event_list[trigger_index].start_time - os->TRIGGER_PREFIX_TIME);
    write_metadata(os->event_list[trigger_index].video_output.filename, "sdsiiddsdidiisddd",
                   "obstoryId", os->obstory_id,
                   "utc", os->event_list[trigger_index].start_time,
                   "semanticType", "pigazing:movingObject/video",
                   "width", os->width,
                   "height", os->height,
                   "inputNoiseLevel", os->noise_level,
                   "meanLevel", os->mean_level,
                   "path", path_json,
                   "duration", duration,
                   "detectionCount", os->event_list[trigger_index].detection_count,
                   "detectionSignificance", amplitude_peak / os->noise_level,
                   "amplitudeTimeIntegrated", amplitude_time_integrated,
                   "amplitudePeak", amplitude_peak,
                   "pathBezier", path_bezier,
                   "videoStart", os->event_list[trigger_index].start_time - os->TRIGGER_PREFIX_TIME,
                   "videoFPS", duration_frames / duration,
                   "videoDuration", video_duration
    );
}