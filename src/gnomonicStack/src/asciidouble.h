// asciidouble.h
// $Id: asciidouble.h 1122 2014-10-23 21:33:05Z pyxplot $

#ifndef _ASCIIDOUBLE_H
#define _ASCIIDOUBLE_H 1

#include <stdio.h>

double GetFloat                 (const char *str, int *Nchars);
int    ValidFloat               (const char *str, int *end);
char  *NumericDisplay           (double in, int N, int SigFig, int latex);
unsigned char DblEqual          (double a, double b);
void   file_readline            (FILE *file, char *output, int MaxLength);
void   GetWord                  (char *out, const char *in, int max);
char  *NextWord                 (char *in);
char  *FriendlyTimestring       ();
char  *StrStrip                 (const char *in, char *out);
char  *StrUpper                 (const char *in, char *out);
char  *StrLower                 (const char *in, char *out);
char  *StrUnderline             (const char *in, char *out);
char  *StrRemoveCompleteLine    (char *in, char *out);
char  *StrSlice                 (const char *in, char *out, int start, int end);
char  *StrCommaSeparatedListScan(char **inscan, char *out);
int    StrAutocomplete          (const char *candidate, char *test, int Nmin);
void   StrWordWrap              (const char *in, char *out, int width);
void   StrBracketMatch          (const char *in, int *CommaPositions, int *Nargs, int *ClosingBracketPos, int MaxCommaPoses);
char  *StrEscapify              (const char *in, char *out);
int    StrWildcardTest          (const char *test, const char *wildcard);
void   ReadConfig_FetchKey      (char *line, char *out);
void   ReadConfig_FetchValue    (char *line, char *out);
#endif

