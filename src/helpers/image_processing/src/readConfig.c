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

#include "asciiDouble.h"
#include "error.h"
#include "gnomonic.h"
#include "imageProcess.h"
#include "image.h"
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

int readConfig(char *filename, settings *feed_s, settingsIn *si, settingsIn *s_in_default, int *nImages) {
    char line[LSTR_LENGTH], key[LSTR_LENGTH], *keyval;
    int file_linenumber;
    FILE *infile;

    settingsIn *feed_si = NULL;

    if ((infile = fopen(filename, "r")) == NULL) {
        sprintf(temp_err_string, "Stacker could not open input file '%s'.", filename);
        logging_error(ERR_GENERAL, temp_err_string);
        return 1;
    }
    file_linenumber = 0;
    while (!feof(infile)) {
        file_readline(infile, line, LSTR_LENGTH);
        file_linenumber++;
        strStrip(line, line);
        if (strlen(line) == 0) continue; // Ignore blank lines
        if (line[0] == '#') continue;

        {
            int i = 0;
            keyval = line;
            while (isalnum(*keyval)) { key[i++] = *(keyval++); }
            key[i++] = '\0';
        }

        if (strcmp(key, "GNOMONIC") == 0) {
            feed_s->mode = MODE_GNOMONIC;
            // Exposure compensation, xsize, ysize, Central RA, Central Dec, position angle, scalex, scaley
            char *cp = keyval;
            while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_s->ExpComp = getFloat(cp, NULL);
            sprintf(temp_err_string, "ExpComp = %f", feed_s->ExpComp);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output X pixel size");
            feed_s->XSize = getFloat(cp, NULL);
            sprintf(temp_err_string, "XSize = %6d pixels", feed_s->XSize);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output Y pixel size");
            feed_s->YSize = getFloat(cp, NULL);
            sprintf(temp_err_string, "YSize = %6d pixels", feed_s->YSize);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read central RA");
            feed_s->RA0 = getFloat(cp, NULL) * M_PI / 12.;
            sprintf(temp_err_string, "Central RA = %.6f hr", feed_s->RA0 / M_PI * 12.);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read central Dec");
            feed_s->Dec0 = getFloat(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "Central Dec = %.6f deg", feed_s->Dec0 / M_PI * 180.);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read position angle");
            feed_s->PA = getFloat(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "Position Angle = %.6f deg", feed_s->PA / M_PI * 180.);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output X angular size");
            feed_s->XScale = getFloat(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "XScale = %.6f deg/width", feed_s->XScale / M_PI * 180.);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output Y angular size");
            feed_s->YScale = getFloat(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "YScale = %.6f deg/height", feed_s->YScale / M_PI * 180.);
            logging_report(temp_err_string);
        } else if (strcmp(key, "FLAT") == 0) {
            feed_s->mode = MODE_FLAT;
            // Exposure compensation, x size, y size, x shift, y shift, rotation
            char *cp = keyval;
            while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_s->ExpComp = getFloat(cp, NULL);
            sprintf(temp_err_string, "ExpComp = %f", feed_s->ExpComp);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output X pixel size");
            feed_s->XSize = getFloat(cp, NULL);
            sprintf(temp_err_string, "XSize = %6d pixels", feed_s->XSize);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read output Y pixel size");
            feed_s->YSize = getFloat(cp, NULL);
            sprintf(temp_err_string, "YSize = %6d pixels", feed_s->YSize);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read x offset");
            feed_s->XOff = getFloat(cp, NULL);
            sprintf(temp_err_string, "XOff = %6d pixel", feed_s->XOff);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read y offset");
            feed_s->YOff = getFloat(cp, NULL);
            sprintf(temp_err_string, "Yoff = %6d pixel", feed_s->YOff);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read linear rotation");
            feed_s->LinearRot = getFloat(cp, NULL);
            sprintf(temp_err_string, "LinearRot = %.6f deg", feed_s->LinearRot);
            logging_report(temp_err_string);
        } else if (strcmp(key, "SET") == 0) {
            int i = 0;
            char key2[1024];
            while (!isalnum(*keyval) && (*keyval != '\0')) keyval++;
            while (isalnum(*keyval)) { key2[i++] = *(keyval++); }
            key2[i++] = '\0';
            sprintf(temp_err_string, "SET %s", key2);
            logging_report(temp_err_string);

            if (strcmp(key2, "output") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                getWord(feed_s->OutFName, cp, FNAME_LENGTH);
                sprintf(temp_err_string, "Output filename = %s", feed_s->OutFName);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "barrel_a") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read barrel_a");
                s_in_default->barrel_a = getFloat(cp, NULL);
                sprintf(temp_err_string, "barrel_a = %.6f", s_in_default->barrel_a);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "barrel_b") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read barrel_b");
                s_in_default->barrel_b = getFloat(cp, NULL);
                sprintf(temp_err_string, "barrel_b = %.6f", s_in_default->barrel_b);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "barrel_c") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read barrel_c");
                s_in_default->barrel_c = getFloat(cp, NULL);
                sprintf(temp_err_string, "barrel_c = %.6f", s_in_default->barrel_c);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "backgroundsub") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read backgroundsub");
                s_in_default->backSub = getFloat(cp, NULL);
                sprintf(temp_err_string, "backgroundsub = %d", s_in_default->backSub);
                logging_report(temp_err_string);
            } else if (strcmp(key2, "cloudmask") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read cloudmask");
                feed_s->cloudMask = getFloat(cp, NULL);
                sprintf(temp_err_string, "cloudmask = %d", feed_s->cloudMask);
                logging_report(temp_err_string);
            }
            continue;
        } else if (strcmp(key, "ADD") == 0) // This is a source image to be stacked
        {
            char *cp = keyval;
            while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
            if (*cp == '\0') continue;
            feed_si = si + (*nImages);
            *feed_si = *s_in_default;
            logging_report("\nNew Image:");
            getWord(feed_si->InFName, cp, FNAME_LENGTH);
            sprintf(temp_err_string, "Input filename = %s", feed_si->InFName);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read image weight");
            feed_si->InWeight = getFloat(cp, NULL);
            sprintf(temp_err_string, "Image weight = %.6f", feed_si->InWeight);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_si->InExpComp = getFloat(cp, NULL);
            sprintf(temp_err_string, "Exposure compensation = %.6f", feed_si->InExpComp);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read x size");
            feed_si->InXSize = getFloat(cp, NULL);
            sprintf(temp_err_string, "XSize = %6d", feed_si->InXSize);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read y size");
            feed_si->InYSize = getFloat(cp, NULL);
            sprintf(temp_err_string, "YSize = %6d", feed_si->InYSize);
            logging_report(temp_err_string);
            cp = nextWord(cp);
            if (feed_s->mode == MODE_GNOMONIC) {
                // Filename, weight, exposure compensation, Central RA, Central Dec, position angle, scalex, scaley
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read central RA");
                feed_si->InRA0 = getFloat(cp, NULL) * M_PI / 12.;
                sprintf(temp_err_string, "Central RA = %.6f hr", feed_si->InRA0 / M_PI * 12.);
                logging_report(temp_err_string);
                cp = nextWord(cp);
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read central Dec");
                feed_si->InDec0 = getFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Central Dec = %.6f deg", feed_si->InDec0 / M_PI * 180.);
                logging_report(temp_err_string);
                cp = nextWord(cp);
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read input rotation angle");
                feed_si->InRotation = getFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Rotation = %.6f deg", feed_si->InRotation / M_PI * 180.);
                logging_report(temp_err_string);
                cp = nextWord(cp);
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read input X angular size");
                feed_si->InXScale = getFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "XScale = %.6f deg/width", feed_si->InXScale / M_PI * 180.);
                logging_report(temp_err_string);
                cp = nextWord(cp);
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read input Y angular size");
                feed_si->InYScale = getFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "YScale = %.6f deg/height", feed_si->InYScale / M_PI * 180.);
                logging_report(temp_err_string);
            } else {
                // Filename, weight, exposure compensation, x shift, y shift, rotation
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read x offset");
                feed_si->InXOff = getFloat(cp, NULL);
                sprintf(temp_err_string, "X Shift = %.2f pixels", feed_si->InYOff);
                logging_report(temp_err_string);
                cp = nextWord(cp);
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read y offset");
                feed_si->InYOff = getFloat(cp, NULL);
                sprintf(temp_err_string, "Y Shift = %.2f pixels", feed_si->InXOff);
                logging_report(temp_err_string);
                cp = nextWord(cp);
                if (!validFloat(cp, NULL)) logging_fatal(__FILE__, __LINE__, "Could not read linear rotation");
                feed_si->InLinearRotation = getFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Rotation = %.6f deg", feed_si->InLinearRotation / M_PI * 180.);
                logging_report(temp_err_string);
            }
            (*nImages)++;
        }

    }

    fclose(infile);
    return 0;
}

