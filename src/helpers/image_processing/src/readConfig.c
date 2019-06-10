// readConfig.c
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

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include <gsl/gsl_errno.h>
#include <gsl/gsl_math.h>

#include "utils/asciiDouble.h"
#include "utils/error.h"
#include "gnomonic.h"
#include "imageProcess.h"
#include "png/image.h"
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

int read_config(const char *filename, settings *feed_s, settings_input *si, settings_input *s_in_default, int *image_count) {
    char line[LSTR_LENGTH], key[LSTR_LENGTH], *key_value;
    int file_line_number;
    FILE *in_file;

    settings_input *feed_si = NULL;

    if ((in_file = fopen(filename, "r")) == NULL) {
        sprintf(temp_err_string, "Stacker could not open input file '%s'.", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return 1;
    }
    file_line_number = 0;
    while (!feof(in_file)) {
        file_readline(in_file, line, LSTR_LENGTH);
        file_line_number++;
        str_strip(line, line);
        if (strlen(line) == 0) continue; // Ignore blank lines
        if (line[0] == '#') continue;

        {
            int i = 0;
            key_value = line;
            while (isalnum(*key_value)) { key[i++] = *(key_value++); }
            key[i++] = '\0';
        }

        if (strcmp(key, "GNOMONIC") == 0) {
            feed_s->mode = MODE_GNOMONIC;
            // Exposure compensation, xsize, ysize, Central RA, Central Dec, position angle, scalex, scaley
            char *cp = key_value;
            while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_s->exposure_compensation = get_float(cp, NULL);
            sprintf(temp_err_string, "exposure_compensation = %f", feed_s->exposure_compensation);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output X pixel size");
            feed_s->x_size = get_float(cp, NULL);
            sprintf(temp_err_string, "x_size = %6d pixels", feed_s->x_size);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output Y pixel size");
            feed_s->y_size = get_float(cp, NULL);
            sprintf(temp_err_string, "y_size = %6d pixels", feed_s->y_size);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read central RA");
            feed_s->ra0 = get_float(cp, NULL) * M_PI / 12.;
            sprintf(temp_err_string, "Central RA = %.6f hr", feed_s->ra0 / M_PI * 12.);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read central Dec");
            feed_s->dec0 = get_float(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "Central Dec = %.6f deg", feed_s->dec0 / M_PI * 180.);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read position angle");
            feed_s->pa = get_float(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "Position Angle = %.6f deg", feed_s->pa / M_PI * 180.);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output X angular size");
            feed_s->x_scale = get_float(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "x_scale = %.6f deg/width", feed_s->x_scale / M_PI * 180.);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output Y angular size");
            feed_s->y_scale = get_float(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "y_scale = %.6f deg/height", feed_s->y_scale / M_PI * 180.);
            logging_report(temp_err_string);
        } else if (strcmp(key, "FLAT") == 0) {
            feed_s->mode = MODE_FLAT;
            // Exposure compensation, x size, y size, x shift, y shift, rotation
            char *cp = key_value;
            while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_s->exposure_compensation = get_float(cp, NULL);
            sprintf(temp_err_string, "exposure_compensation = %f", feed_s->exposure_compensation);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output X pixel size");
            feed_s->x_size = get_float(cp, NULL);
            sprintf(temp_err_string, "x_size = %6d pixels", feed_s->x_size);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output Y pixel size");
            feed_s->y_size = get_float(cp, NULL);
            sprintf(temp_err_string, "y_size = %6d pixels", feed_s->y_size);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read x offset");
            feed_s->x_off = get_float(cp, NULL);
            sprintf(temp_err_string, "x_off = %6d pixel", feed_s->x_off);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read y offset");
            feed_s->y_off = get_float(cp, NULL);
            sprintf(temp_err_string, "Yoff = %6d pixel", feed_s->y_off);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read linear rotation");
            feed_s->linear_rotation = get_float(cp, NULL);
            sprintf(temp_err_string, "linear_rotation = %.6f deg", feed_s->linear_rotation);
            logging_report(temp_err_string);
        } else if (strcmp(key, "SET") == 0) {
            int i = 0;
            char key2[1024];
            while (!isalnum(*key_value) && (*key_value != '\0')) key_value++;
            while (isalnum(*key_value)) { key2[i++] = *(key_value++); }
            key2[i++] = '\0';
            sprintf(temp_err_string, "SET %s", key2);
            logging_report(temp_err_string);

            if (strcmp(key2, "output") == 0) {
                char *cp = key_value;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                get_word(feed_s->output_filename, cp, FNAME_LENGTH);
                sprintf(temp_err_string, "Output filename = %s", feed_s->output_filename);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "barrel_a") == 0) {
                char *cp = key_value;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read barrel_a");
                s_in_default->barrel_a = get_float(cp, NULL);
                sprintf(temp_err_string, "barrel_a = %.6f", s_in_default->barrel_a);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "barrel_b") == 0) {
                char *cp = key_value;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read barrel_b");
                s_in_default->barrel_b = get_float(cp, NULL);
                sprintf(temp_err_string, "barrel_b = %.6f", s_in_default->barrel_b);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "barrel_c") == 0) {
                char *cp = key_value;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read barrel_c");
                s_in_default->barrel_c = get_float(cp, NULL);
                sprintf(temp_err_string, "barrel_c = %.6f", s_in_default->barrel_c);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "backgroundsub") == 0) {
                char *cp = key_value;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read backgroundsub");
                s_in_default->background_subtract = get_float(cp, NULL);
                sprintf(temp_err_string, "backgroundsub = %d", s_in_default->background_subtract);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "cloudmask") == 0) {
                char *cp = key_value;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read cloudmask");
                feed_s->cloud_mask = get_float(cp, NULL);
                sprintf(temp_err_string, "cloudmask = %d", feed_s->cloud_mask);
                logging_report(temp_err_string);
            }
            continue;
        } else if (strcmp(key, "ADD") == 0) // This is a source image to be stacked
        {
            char *cp = key_value;
            while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
            if (*cp == '\0') continue;
            feed_si = si + (*image_count);
            *feed_si = *s_in_default;
            logging_report("\nNew Image:");
            get_word(feed_si->input_filename, cp, FNAME_LENGTH);
            sprintf(temp_err_string, "Input filename = %s", feed_si->input_filename);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read image weight");
            feed_si->weight_in = get_float(cp, NULL);
            sprintf(temp_err_string, "Image weight = %.6f", feed_si->weight_in);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_si->exposure_compensation_in = get_float(cp, NULL);
            sprintf(temp_err_string, "Exposure compensation = %.6f", feed_si->exposure_compensation_in);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read x size");
            feed_si->x_size_in = get_float(cp, NULL);
            sprintf(temp_err_string, "x_size = %6d", feed_si->x_size_in);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read y size");
            feed_si->y_size_in = get_float(cp, NULL);
            sprintf(temp_err_string, "y_size = %6d", feed_si->y_size_in);
            logging_report(temp_err_string);
            cp = next_word(cp);
            if (feed_s->mode == MODE_GNOMONIC) {
                // Filename, weight, exposure compensation, Central RA, Central Dec, position angle, scalex, scaley
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read central RA");
                feed_si->ra0_in = get_float(cp, NULL) * M_PI / 12.;
                sprintf(temp_err_string, "Central RA = %.6f hr", feed_si->ra0_in / M_PI * 12.);
                logging_report(temp_err_string);
                cp = next_word(cp);
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read central Dec");
                feed_si->dec0_in = get_float(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Central Dec = %.6f deg", feed_si->dec0_in / M_PI * 180.);
                logging_report(temp_err_string);
                cp = next_word(cp);
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read input rotation angle");
                feed_si->rotation_in = get_float(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Rotation = %.6f deg", feed_si->rotation_in / M_PI * 180.);
                logging_report(temp_err_string);
                cp = next_word(cp);
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read input X angular size");
                feed_si->x_scale_in = get_float(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "x_scale = %.6f deg/width", feed_si->x_scale_in / M_PI * 180.);
                logging_report(temp_err_string);
                cp = next_word(cp);
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read input Y angular size");
                feed_si->y_scale_in = get_float(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "y_scale = %.6f deg/height", feed_si->y_scale_in / M_PI * 180.);
                logging_report(temp_err_string);
            } else {
                // Filename, weight, exposure compensation, x shift, y shift, rotation
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read x offset");
                feed_si->x_off_in = get_float(cp, NULL);
                sprintf(temp_err_string, "X Shift = %.2f pixels", feed_si->y_off_in);
                logging_report(temp_err_string);
                cp = next_word(cp);
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read y offset");
                feed_si->y_off_in = get_float(cp, NULL);
                sprintf(temp_err_string, "Y Shift = %.2f pixels", feed_si->x_off_in);
                logging_report(temp_err_string);
                cp = next_word(cp);
                if (!valid_float(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read linear rotation");
                feed_si->linear_rotation_in = get_float(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Rotation = %.6f deg", feed_si->linear_rotation_in / M_PI * 180.);
                logging_report(temp_err_string);
            }
            (*image_count)++;
        }

    }

    fclose(in_file);
    return 0;
}

