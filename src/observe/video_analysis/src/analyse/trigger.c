// trigger.c
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

#define MIN(X, Y) (((X) < (Y)) ? (X) : (Y))
#define MAX(X, Y) (((X) > (Y)) ? (X) : (Y))

//! trigger_blocks_merge - When we are mapping groups of pixels which have brightened, we may discover part-way down
//! the frame that two groups which were previously unconnected actually join together. This routine merges the two
//! blocks into a single ID. We populate the array <os->trigger_block_redirect> to indicate that id_old is the same
//! block as id_new. We do not alter any brightened pixels which have already been assigned group ID <id_old> in the
//! map contained in <os->trigger_map> as this would take time. We do update metadata associated with <id_new> to now
//! include <id_old>'s pixels.
//!
//! \param os - Settings pertaining to the current observing run
//! \param id_old - The block ID that we are getting rid of.
//! \param id_new - The block ID that we are merging <id_old> pixels into.

inline void trigger_blocks_merge(observe_status *os, int id_old, int id_new) {
    // If either of the blocks <id_old> or <id_new> have already been merged into other groups, make sure that we merge
    // the whole groups.
    while (os->trigger_block_redirect[id_old] > 0) id_old = os->trigger_block_redirect[id_old];
    while (os->trigger_block_redirect[id_new] > 0) id_new = os->trigger_block_redirect[id_new];

    // If it turns out that id_old and id_new are actually part of the same big group already, then we have nothing to
    // do
    if (id_old == id_new) return;

    // Merge the pixels from <id_old> into <id_new>
    os->trigger_block_count[id_new] += os->trigger_block_count[id_old];
    os->trigger_block_top[id_new] = MIN(os->trigger_block_top[id_new], os->trigger_block_top[id_old]);
    os->trigger_block_bot[id_new] = MAX(os->trigger_block_bot[id_new], os->trigger_block_bot[id_old]);
    os->trigger_block_sumx[id_new] += os->trigger_block_sumx[id_old];
    os->trigger_block_sumy[id_new] += os->trigger_block_sumy[id_old];
    os->trigger_block_suml[id_new] += os->trigger_block_suml[id_old];

    // Mark id_old as being dead and having no pixels
    os->trigger_block_count[id_old] = 0;

    // Create a redirect to indicate the pixels in the trigger map marked as part of <id_old> are actually part of
    // <id_new>
    os->trigger_block_redirect[id_old] = id_new;
}

//! test_pixel - Test a single pixel to see whether it has brightened enough to potentially trigger to motion sensor
//! \param os - Settings pertaining to the current observing run
//! \param image1 - The video frame which we are analysing for triggers
//! \param image2 - The previous video frame which image1 is being compared against
//! \param o - The offset of the pixel from the beginning of the video buffer
//! \param threshold - The threshold increase in brightness which triggers the camera
//! \return Boolean flag indicating whether this pixel has brightened by an interesting amount

static inline int test_pixel(observe_status *os,
                             const unsigned char *image1, const unsigned char *image2,
                             const int o, const int threshold) {
    // Pixel must be brighter than test pixels this distance away
    const int radius = 16;

    // Search for pixels which have brightened by more than threshold since past image
    if (image1[o] - image2[o] > threshold) {
        // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels.
        // This pixel must be brighter than 6/9 of these pixels were
        int i, j, c = 0;
        for (i = -1; i <= 1; i++)
            for (j = -1; j <= 1; j++)
                if (image1[o] - image2[o + (j + i * os->width) * radius] > threshold)c++;
        if (c > 7) {
            // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels.
            // This pixel must be brighter than 6/9 of these pixels were
            int i, j, c = 0;
            for (i = -1; i <= 1; i++)
                for (j = -1; j <= 1; j++)
                    if (image1[o] - image1[o + (j + i * os->width) * radius] > threshold)c++;
            if (c > 6) return 1;
        }
    }
    return 0;
}

//! check_for_triggers - Search the frame <image1> for blocks of pixels which have brightened relative to <image2>
//! \param os - Settings pertaining to the current observing run
//! \param image1 - The video frame which we are analysing for triggers
//! \param image2 - The previous video frame which image1 is being compared against
//! \return Boolean flag indicating whether any pixels triggered the motion sensor

int check_for_triggers(observe_status *os, const unsigned char *image1, const unsigned char *image2) {
    int y;
    int output = 0;

    // Ignore pixels within this distance of the edge
    const int margin = 20;

    // To trigger this number of pixels connected together must have brightened
    const int threshold_blockSize = 7;

    // Total brightness excess must be 50 standard deviations
    const int threshold_intensity = (int) (os->TRIGGER_MIN_SIGNIFICANCE * os->noise_level);

    // Pixel must have brightened by at least N standard deviations to trigger
    const int threshold_trigger = MAX(10, 3.5 * os->noise_level);

    // Monitor and flag pixels which brighten by this amount
    const int threshold_monitor = MAX(10, 2.0 * os->noise_level);

    // These arrays are used to produce diagnostic images when the camera triggers
    unsigned char *trigger_r = os->trigger_map_rgb;
    unsigned char *trigger_g = os->trigger_map_rgb + os->frame_size * 1;
    unsigned char *trigger_b = os->trigger_map_rgb + os->frame_size * 2;
    memset(os->trigger_map, 0, os->frame_size * sizeof(int));
    os->block_count = 0;

    static unsigned long long past_trigger_map_average = 1;
    unsigned int pixel_count_within_mask = 1;
    unsigned long long past_trigger_map_average_new = 0;

#pragma omp parallel for private(y)
    for (y = margin; y < os->height - margin; y++) {
        int x, d;
        int trigger_map_line_sum = 0, pixel_count_within_mask_line_sum = 0;
        for (x = margin; x < os->width - margin; x++) {
            const int o = x + y * os->width;
            trigger_map_line_sum += os->past_trigger_map[o];
            if (os->mask[o]) pixel_count_within_mask_line_sum++;

            // RED channel - difference between images B and A
            trigger_r[o] = CLIP256((image1[o] - image2[o]) * 64 / threshold_trigger);

            // GRN channel - map of pixels which are excluded for triggering too often
            trigger_g[o] = CLIP256(os->past_trigger_map[o] * 256 / (2.3 * past_trigger_map_average));

            // BLU channel - blank for now; will put spots where triggers happen
            trigger_b[o] = 0;

            if ((os->mask[o]) && test_pixel(os, image1, image2, o, threshold_monitor)) {
                os->past_trigger_map[o]++;

                // Search for pixels which have brightened by more than threshold since past image
                if (test_pixel(os, image1, image2, o, threshold_trigger)) {
                    os->past_trigger_map[o]++;
#pragma omp critical (add_trigger)
                    {
                        // Put triggering pixel on map. Wait till be have <Npixels> connected pixels.
                        trigger_b[o] = (os->past_trigger_map[o] < 3 * past_trigger_map_average) ? 63 : 31;
                        int block_id = 0;
                        if (os->trigger_map[o - 1]) {
                            if (!block_id) {
                                block_id = os->trigger_map[o - 1];
                            } else { trigger_blocks_merge(os, os->trigger_map[o - 1], block_id); }
                        }
                        if (os->trigger_map[o + 1 - os->width]) {
                            if (!block_id) {
                                block_id = os->trigger_map[o + 1 - os->width];
                            } else { trigger_blocks_merge(os, os->trigger_map[o + 1 - os->width], block_id); }
                        }
                        if (os->trigger_map[o - os->width]) {
                            if (!block_id) {
                                block_id = os->trigger_map[o - os->width];
                            } else { trigger_blocks_merge(os, os->trigger_map[o - os->width], block_id); }
                        }
                        if (os->trigger_map[o - 1 - os->width]) {
                            if (!block_id) {
                                block_id = os->trigger_map[o - 1 - os->width];
                            } else { trigger_blocks_merge(os, os->trigger_map[o - 1 - os->width], block_id); }
                        }
                        if (os->trigger_map[o + 1 + os->width]) {
                            if (!block_id) {
                                block_id = os->trigger_map[o + 1 + os->width];
                            } else { trigger_blocks_merge(os, os->trigger_map[o + 1 + os->width], block_id); }
                        }
                        if (os->trigger_map[o + os->width]) {
                            if (!block_id) {
                                block_id = os->trigger_map[o + os->width];
                            } else { trigger_blocks_merge(os, os->trigger_map[o + os->width], block_id); }
                        }
                        if (os->trigger_map[o - 1 + os->width]) {
                            if (!block_id) {
                                block_id = os->trigger_map[o - 1 + os->width];
                            } else { trigger_blocks_merge(os, os->trigger_map[o - 1 + os->width], block_id); }
                        }
                        while (block_id && (os->trigger_block_redirect[block_id] > 0))
                            block_id = os->trigger_block_redirect[block_id];
                        if (block_id == 0) {
                            if (os->block_count < MAX_TRIGGER_BLOCKS - 1) os->block_count++;
                            block_id = os->block_count;
                            os->trigger_block_count[block_id] = 0;
                            os->trigger_block_sumx[block_id] = 0;
                            os->trigger_block_sumy[block_id] = 0;
                            os->trigger_block_suml[block_id] = 0;
                            os->trigger_block_top[block_id] = y;
                            os->trigger_block_bot[block_id] = y;
                            os->trigger_block_redirect[block_id] = 0;
                        }

                        if (os->past_trigger_map[o] < 2.3 * past_trigger_map_average) {
                            os->trigger_block_count[block_id]++;
                            os->trigger_block_top[block_id] = MIN(os->trigger_block_top[block_id], y);
                            os->trigger_block_bot[block_id] = MAX(os->trigger_block_bot[block_id], y);
                            os->trigger_block_sumx[block_id] += x;
                            os->trigger_block_sumy[block_id] += y;
                            os->trigger_block_suml[block_id] += image1[o] - image2[o];
                        }
                        os->trigger_map[o] = block_id;
                    }
                }
            }
        }
#pragma omp critical (trigger_cleanup)
        {
            past_trigger_map_average_new += trigger_map_line_sum;
            pixel_count_within_mask += pixel_count_within_mask_line_sum;
        }
    }

    // Loop over blocks of pixels which have brightened and see if any are large enough to be interesting
    int i;
    for (i = 1; i <= os->block_count; i++) {
        if (i == MAX_TRIGGER_BLOCKS - 1) break;
        if ((os->trigger_block_suml[i] > threshold_intensity) &&
            (os->trigger_block_count[i] > threshold_blockSize) &&
            (os->trigger_block_bot[i] - os->trigger_block_top[i] >= 2)
                ) {
            const int n = os->trigger_block_count[i];
            const int x = (os->trigger_block_sumx[i] / n); // average x position of moving object
            const int y = (os->trigger_block_sumy[i] / n); // average y position of moving object
            const int l = os->trigger_block_suml[i]; // total excess brightness
            output = 1; // We have triggered!
            register_trigger(os, i, x, y, n, l, image1, image2);
        }
    }
    past_trigger_map_average = past_trigger_map_average_new / pixel_count_within_mask + 1;
    return output;
}

