// asciidouble.h
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

double GetFloat(const char *str, int *Nchars);

int ValidFloat(const char *str, int *end);

char *NumericDisplay(double in, int N, int SigFig, int latex);

unsigned char DblEqual(double a, double b);

void file_readline(FILE *file, char *output, int MaxLength);

void GetWord(char *out, const char *in, int max);

char *NextWord(char *in);

char *FriendlyTimestring();

char *StrStrip(const char *in, char *out);

char *StrUpper(const char *in, char *out);

char *StrLower(const char *in, char *out);

char *StrUnderline(const char *in, char *out);

char *StrRemoveCompleteLine(char *in, char *out);

char *StrSlice(const char *in, char *out, int start, int end);

char *StrCommaSeparatedListScan(char **inscan, char *out);

int StrAutocomplete(const char *candidate, char *test, int Nmin);

void StrWordWrap(const char *in, char *out, int width);

void StrBracketMatch(const char *in, int *CommaPositions, int *Nargs, int *ClosingBracketPos, int MaxCommaPoses);

char *StrEscapify(const char *in, char *out);

int StrWildcardTest(const char *test, const char *wildcard);

void ReadConfig_FetchKey(char *line, char *out);

void ReadConfig_FetchValue(char *line, char *out);

#endif

