// asciiDouble.h
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2021 Dominic Ford.

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

#ifndef _ASCIIDOUBLE_H
#define _ASCIIDOUBLE_H 1

#include <stdio.h>

double get_float(const char *str, int *Nchars);

int valid_float(const char *str, int *end);

char *numeric_display(double in, int N, int SigFig, int latex);

unsigned char double_equal(double a, double b);

void file_readline(FILE *file, char *output, int MaxLength);

void get_word(char *out, const char *in, int max);

char *next_word(char *in);

char *friendly_time_string(double t);

char *str_strip(const char *in, char *out);

char *str_upper(const char *in, char *out);

char *str_lower(const char *in, char *out);

char *str_underline(const char *in, char *out);

char *strRemoveCompleteLine(char *in, char *out);

char *str_slice(const char *in, char *out, int start, int end);

char *str_comma_separated_list_scan(char **inscan, char *out);

void str_word_wrap(const char *in, char *out, int width);

void readConfig_fetchKey(char *line, char *out);

void readConfig_fetchValue(char *line, char *out);

#endif

