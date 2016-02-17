// readConfig.c
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include <gsl/gsl_errno.h>
#include <gsl/gsl_math.h>

#include "asciidouble.h"
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
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
    }
    file_linenumber = 0;
    while (!feof(infile)) {
        file_readline(infile, line, LSTR_LENGTH);
        file_linenumber++;
        StrStrip(line, line);
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
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_s->ExpComp = GetFloat(cp, NULL);
            sprintf(temp_err_string, "ExpComp = %f", feed_s->ExpComp);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read output X pixel size");
            feed_s->XSize = GetFloat(cp, NULL);
            sprintf(temp_err_string, "XSize = %6d pixels", feed_s->XSize);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read output Y pixel size");
            feed_s->YSize = GetFloat(cp, NULL);
            sprintf(temp_err_string, "YSize = %6d pixels", feed_s->YSize);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read central RA");
            feed_s->RA0 = GetFloat(cp, NULL) * M_PI / 12.;
            sprintf(temp_err_string, "Central RA = %.6f hr", feed_s->RA0 / M_PI * 12.);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read central Dec");
            feed_s->Dec0 = GetFloat(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "Central Dec = %.6f deg", feed_s->Dec0 / M_PI * 180.);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read position angle");
            feed_s->PA = GetFloat(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "Position Angle = %.6f deg", feed_s->PA / M_PI * 180.);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read output X angular size");
            feed_s->XScale = GetFloat(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "XScale = %.6f deg/width", feed_s->XScale / M_PI * 180.);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read output Y angular size");
            feed_s->YScale = GetFloat(cp, NULL) * M_PI / 180.;
            sprintf(temp_err_string, "YScale = %.6f deg/height", feed_s->YScale / M_PI * 180.);
            gnom_report(temp_err_string);
        }
        else if (strcmp(key, "FLAT") == 0) {
            feed_s->mode = MODE_FLAT;
            // Exposure compensation, x size, y size, x shift, y shift, rotation
            char *cp = keyval;
            while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_s->ExpComp = GetFloat(cp, NULL);
            sprintf(temp_err_string, "ExpComp = %f", feed_s->ExpComp);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read output X pixel size");
            feed_s->XSize = GetFloat(cp, NULL);
            sprintf(temp_err_string, "XSize = %6d pixels", feed_s->XSize);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read output Y pixel size");
            feed_s->YSize = GetFloat(cp, NULL);
            sprintf(temp_err_string, "YSize = %6d pixels", feed_s->YSize);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read x offset");
            feed_s->XOff = GetFloat(cp, NULL);
            sprintf(temp_err_string, "XOff = %6d pixel", feed_s->XOff);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read y offset");
            feed_s->YOff = GetFloat(cp, NULL);
            sprintf(temp_err_string, "Yoff = %6d pixel", feed_s->YOff);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read linear rotation");
            feed_s->LinearRot = GetFloat(cp, NULL);
            sprintf(temp_err_string, "LinearRot = %.6f deg", feed_s->LinearRot);
            gnom_report(temp_err_string);
        }
        else if (strcmp(key, "SET") == 0) {
            int i = 0;
            char key2[1024];
            while (!isalnum(*keyval) && (*keyval != '\0')) keyval++;
            while (isalnum(*keyval)) { key2[i++] = *(keyval++); }
            key2[i++] = '\0';
            sprintf(temp_err_string, "SET %s", key2);
            gnom_report(temp_err_string);

            if (strcmp(key2, "output") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                GetWord(feed_s->OutFName, cp, FNAME_LENGTH);
                sprintf(temp_err_string, "Output filename = %s", feed_s->OutFName);
                gnom_report(temp_err_string);
            }
            else if (strcmp(key2, "barrel_a") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read barrel_a");
                s_in_default->barrel_a = GetFloat(cp, NULL);
                sprintf(temp_err_string, "barrel_a = %.6f", s_in_default->barrel_a);
                gnom_report(temp_err_string);
            }
            else if (strcmp(key2, "barrel_b") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read barrel_b");
                s_in_default->barrel_b = GetFloat(cp, NULL);
                sprintf(temp_err_string, "barrel_b = %.6f", s_in_default->barrel_b);
                gnom_report(temp_err_string);
            }
            else if (strcmp(key2, "barrel_c") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read barrel_c");
                s_in_default->barrel_c = GetFloat(cp, NULL);
                sprintf(temp_err_string, "barrel_c = %.6f", s_in_default->barrel_c);
                gnom_report(temp_err_string);
            }
            else if (strcmp(key2, "backgroundsub") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read backgroundsub");
                s_in_default->backSub = GetFloat(cp, NULL);
                sprintf(temp_err_string, "backgroundsub = %d", s_in_default->backSub);
                gnom_report(temp_err_string);
            }
            else if (strcmp(key2, "cloudmask") == 0) {
                char *cp = keyval;
                while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read cloudmask");
                feed_s->cloudMask = GetFloat(cp, NULL);
                sprintf(temp_err_string, "cloudmask = %d", feed_s->cloudMask);
                gnom_report(temp_err_string);
            }
            continue;
        }
        else if (strcmp(key, "ADD") == 0) // This is a source image to be stacked
        {
            char *cp = keyval;
            while (!isalnum(*cp) && (*cp != '/') && (*cp != '\0')) cp++;
            if (*cp == '\0') continue;
            feed_si = si + (*nImages);
            *feed_si = *s_in_default;
            gnom_report("\nNew Image:");
            GetWord(feed_si->InFName, cp, FNAME_LENGTH);
            sprintf(temp_err_string, "Input filename = %s", feed_si->InFName);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read image weight");
            feed_si->InWeight = GetFloat(cp, NULL);
            sprintf(temp_err_string, "Image weight = %.6f", feed_si->InWeight);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read exposure compensation");
            feed_si->InExpComp = GetFloat(cp, NULL);
            sprintf(temp_err_string, "Exposure compensation = %.6f", feed_si->InExpComp);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read x size");
            feed_si->InXSize = GetFloat(cp, NULL);
            sprintf(temp_err_string, "XSize = %6d", feed_si->InXSize);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read y size");
            feed_si->InYSize = GetFloat(cp, NULL);
            sprintf(temp_err_string, "YSize = %6d", feed_si->InYSize);
            gnom_report(temp_err_string);
            cp = NextWord(cp);
            if (feed_s->mode == MODE_GNOMONIC) {
                // Filename, weight, exposure compensation, Central RA, Central Dec, position angle, scalex, scaley
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read central RA");
                feed_si->InRA0 = GetFloat(cp, NULL) * M_PI / 12.;
                sprintf(temp_err_string, "Central RA = %.6f hr", feed_si->InRA0 / M_PI * 12.);
                gnom_report(temp_err_string);
                cp = NextWord(cp);
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read central Dec");
                feed_si->InDec0 = GetFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Central Dec = %.6f deg", feed_si->InDec0 / M_PI * 180.);
                gnom_report(temp_err_string);
                cp = NextWord(cp);
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read input rotation angle");
                feed_si->InRotation = GetFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Rotation = %.6f deg", feed_si->InRotation / M_PI * 180.);
                gnom_report(temp_err_string);
                cp = NextWord(cp);
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read input X angular size");
                feed_si->InXScale = GetFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "XScale = %.6f deg/width", feed_si->InXScale / M_PI * 180.);
                gnom_report(temp_err_string);
                cp = NextWord(cp);
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read input Y angular size");
                feed_si->InYScale = GetFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "YScale = %.6f deg/height", feed_si->InYScale / M_PI * 180.);
                gnom_report(temp_err_string);
            }
            else {
                // Filename, weight, exposure compensation, x shift, y shift, rotation
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read x offset");
                feed_si->InXOff = GetFloat(cp, NULL);
                sprintf(temp_err_string, "X Shift = %.2f pixels", feed_si->InYOff);
                gnom_report(temp_err_string);
                cp = NextWord(cp);
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read y offset");
                feed_si->InYOff = GetFloat(cp, NULL);
                sprintf(temp_err_string, "Y Shift = %.2f pixels", feed_si->InXOff);
                gnom_report(temp_err_string);
                cp = NextWord(cp);
                if (!ValidFloat(cp, NULL)) gnom_fatal(__FILE__, __LINE__, "Could not read linear rotation");
                feed_si->InLinearRotation = GetFloat(cp, NULL) * M_PI / 180.;
                sprintf(temp_err_string, "Rotation = %.6f deg", feed_si->InLinearRotation / M_PI * 180.);
                gnom_report(temp_err_string);
            }
            (*nImages)++;
        }

    }

    fclose(infile);
    return 0;
}

