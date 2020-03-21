// write_output.h
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

#ifndef VIDEO_ANALYSIS_WRITE_OUTPUT_H
#define VIDEO_ANALYSIS_WRITE_OUTPUT_H

#include "observe.h"

char *filename_generate(char *output, const char *obstory_id, double utc, char *tag, const char *dir_name,
                        const char *label);

void write_timelapse_frame(const int channel_count, const observe_status *os, const int frame_count,
                           const char *filename_stub);

void write_timelapse_bs_frame(const int channel_count, const observe_status *os, const int frame_count,
                              const char *filename_stub);

void write_timelapse_bg_model(const int BACKGROUND_MAP_FRAMES, const int channel_count, const observe_status *os,
                              const char *filename_stub);

void write_trigger_difference_frame(const observe_status *os, const int trigger_index);

void write_trigger_mask_frame(const observe_status *os, const int trigger_index);

void write_trigger_map_frame(const observe_status *os, const int trigger_index);

void write_trigger_frame(const observe_status *os, const unsigned char *image1, const int channel_count,
                         const int trigger_index);

void write_trigger_previous_frame(const observe_status *os, const unsigned char *image2, const int channel_count,
                                  const int trigger_index);

void write_trigger_time_average_frame(const observe_status *os, int trigger_index, const int channel_count,
                                      const double duration, int amplitude_peak, int amplitude_time_integrated,
                                      int integrated_frame_count);

void write_trigger_max_brightness_frame(const observe_status *os, int trigger_index, const int channel_count,
                                        const double duration, int amplitude_peak, int amplitude_time_integrated,
                                        int integrated_frame_count);

void write_trigger_integrated_trigger_map(const observe_status *os, int trigger_index,
                                          const double duration, int amplitude_peak, int amplitude_time_integrated,
                                          int integrated_frame_count);

void write_video_metadata(observe_status *os, int trigger_index);


#include "str_constants.h"

#endif //VIDEO_ANALYSIS_WRITE_OUTPUT_H
