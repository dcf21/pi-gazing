// error.c
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
#include <string.h>
#include <unistd.h>

#include "utils/asciiDouble.h"
#include "utils/error.h"
#include "settings.h"
#include "str_constants.h"

static char temp_string_a[LSTR_LENGTH], temp_string_b[LSTR_LENGTH], temp_string_c[LSTR_LENGTH];
static char temp_string_d[LSTR_LENGTH], temp_string_e[LSTR_LENGTH];
char temp_err_string[LSTR_LENGTH];

//! logging_error - Log an error message
//! \param [in] ErrType The type of error message. Should be one of the constants whose names start ERR_...
//! \param msg The error message

void logging_error(int ErrType, char *msg) {
    int i = 0;

    if (msg != temp_string_a) {
        strcpy(temp_string_a, msg);
        msg = temp_string_a;
    }

    temp_string_b[i] = '\0';

    if (ErrType != ERR_PREFORMED) // Do not prepend anything to pre-formed errors
    {
        // Prepend error type
        switch (ErrType) {
            case ERR_INTERNAL:
                sprintf(temp_string_b + i, "Internal Error: ");
                break;
            case ERR_MEMORY  :
            case ERR_GENERAL :
                sprintf(temp_string_b + i, "Error: ");
                break;
            case ERR_SYNTAX  :
                sprintf(temp_string_b + i, "Syntax Error: ");
                break;
            case ERR_NUMERIC :
                sprintf(temp_string_b + i, "Numerical Error: ");
                break;
            case ERR_FILE    :
                sprintf(temp_string_b + i, "File Error: ");
                break;
        }
        i += strlen(temp_string_b + i);
    }

    strcpy(temp_string_b + i, msg);
    if (DEBUG) { logging_info(temp_string_b); }
    sprintf(temp_string_c, "%s\n", temp_string_b);
    fputs(temp_string_c, stderr);
}

//! logging_fatal - Log a fatal error message, and exit with status 1
//! \param [in] ErrType The type of error message. Should be one of the constants whose names start ERR_...
//! \param msg The error message

void logging_fatal(char *file, int line, char *msg) {
    char introline[FNAME_LENGTH];
    if (msg != temp_string_e) strcpy(temp_string_e, msg);
    sprintf(introline, "Fatal Error encountered in %s at line %d: %s", file, line, temp_string_e);
    logging_error(ERR_PREFORMED, introline);
    if (DEBUG) logging_info("Terminating with error condition 1.");
    exit(1);
}

//! logging_warning - Log a warning message
//! \param [in] ErrType The type of warning message. Should be one of the constants whose names start ERR_...
//! \param msg The warning message

void logging_warning(int ErrType, char *msg) {
    int i = 0;

    if (msg != temp_string_a) {
        strcpy(temp_string_a, msg);
        msg = temp_string_a;
    }

    temp_string_b[i] = '\0';

    if (ErrType != ERR_PREFORMED) // Do not prepend anything to pre-formed errors
    {
        // Prepend error type
        switch (ErrType) {
            case ERR_INTERNAL:
                sprintf(temp_string_b + i, "Internal Warning: ");
                break;
            case ERR_MEMORY  :
            case ERR_GENERAL :
                sprintf(temp_string_b + i, "Warning: ");
                break;
            case ERR_SYNTAX  :
                sprintf(temp_string_b + i, "Syntax Warning: ");
                break;
            case ERR_NUMERIC :
                sprintf(temp_string_b + i, "Numerical Warning: ");
                break;
            case ERR_FILE    :
                sprintf(temp_string_b + i, "File Warning: ");
                break;
        }
        i += strlen(temp_string_b + i);
    }

    strcpy(temp_string_b + i, msg);
    if (DEBUG) { logging_info(temp_string_b); }
    sprintf(temp_string_c, "%s\n", temp_string_b);
    fputs(temp_string_c, stderr);
}

//! logging_report - Log a report message
//! \param msg The report message

void logging_report(char *msg) {
    if (msg != temp_string_a) strcpy(temp_string_a, msg);
    if (DEBUG) {
        sprintf(temp_string_c, "%s%s", "Reporting:\n", temp_string_a);
        logging_info(temp_string_c);
    }
    sprintf(temp_string_c, "%s\n", temp_string_a);
    fputs(temp_string_c, stdout);
}

//! logging_info - Log an information message
//! \param msg The information message

void logging_info(char *msg) {
    static FILE *logfile = NULL;
    static int latch = 0;
    char linebuffer[LSTR_LENGTH];

    if (latch) return; // Do not allow recursive calls, which might be generated by the call to logging_fatal below
    latch = 1;
    if (logfile == NULL) {
        if ((logfile = fopen(OUTPUT_PATH "/pigazing.log", "a")) == NULL) {
            logging_fatal(__FILE__, __LINE__, "Could not open log file to write.");
            exit(1);
        }
        setvbuf(logfile, NULL, _IOLBF, 0); // Set log file to be line-buffered, so that log file is always up-to-date
    }

    if (msg != temp_string_d) strcpy(temp_string_d, msg);
    fprintf(logfile, "[%s c ] %s\n", str_strip(friendly_time_string(0), linebuffer), temp_string_d);
    fflush(logfile);
    latch = 0;
}
