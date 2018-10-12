// asciiDouble.h
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

// -------------------------------------------------
// Copyright 2016 Cambridge Science Centre.

// This file is part of Meteor Pi.

// Meteor Pi is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Meteor Pi is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

#ifndef _ASCIIDOUBLE_H
#define _ASCIIDOUBLE_H 1

#include <stdio.h>

double getFloat(const char *str, int *Nchars);

int validFloat(const char *str, int *end);

char *numericDisplay(double in, int N, int SigFig, int latex);

unsigned char dblEqual(double a, double b);

void file_readline(FILE *file, char *output, int MaxLength);

void getWord(char *out, const char *in, int max);

char *nextWord(char *in);

char *friendlyTimestring();

char *strStrip(const char *in, char *out);

char *strUpper(const char *in, char *out);

char *strLower(const char *in, char *out);

char *strUnderline(const char *in, char *out);

char *strRemoveCompleteLine(char *in, char *out);

char *strSlice(const char *in, char *out, int start, int end);

char *strCommaSeparatedListScan(char **inscan, char *out);

int strAutocomplete(const char *candidate, char *test, int Nmin);

void strWordWrap(const char *in, char *out, int width);

void strBracketMatch(const char *in, int *CommaPositions, int *Nargs, int *ClosingBracketPos, int MaxCommaPoses);

char *strEscapify(const char *in, char *out);

int strWildcardTest(const char *test, const char *wildcard);

void readConfig_FetchKey(char *line, char *out);

void readConfig_FetchValue(char *line, char *out);

#endif

