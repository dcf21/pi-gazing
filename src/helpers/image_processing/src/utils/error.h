// error.h
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

// Functions for returning messages to the user

#ifndef ERROR_H
#define ERROR_H 1

#define ERR_INTERNAL 100
#define ERR_GENERAL  101
#define ERR_SYNTAX   102
#define ERR_NUMERIC  103
#define ERR_FILE     104
#define ERR_MEMORY   105
#define ERR_STACKED  106
#define ERR_PREFORMED 107

extern char temp_err_string[];

void logging_error_setstreaminfo(int linenumber, char *filename);

void logging_error(int ErrType, char *msg);

void logging_fatal(char *file, int line, char *msg);

void logging_warning(int ErrType, char *msg);

void logging_report(char *msg);

void logging_info(char *msg);

void dcf_fread(void *ptr, size_t size, size_t nmemb, FILE *stream);

#endif

