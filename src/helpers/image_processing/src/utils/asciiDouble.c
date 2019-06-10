// asciiDouble.c
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

#define _ASCIIDOUBLE_C 1

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <string.h>
#include <ctype.h>

#include "utils/julianDate.h"

//! getFloat - Extract a floating point number from a string
//! \param [in] str The input string
//! \param [out] Nchars Return the number of characters occupied by the float returned (optional)
//! \return The floating point value extracted

double getFloat(const char *str, int *Nchars) {
    double accumulator = 0;
    int decimals = 0;
    unsigned char past_decimal_point = 0;
    unsigned char negative = 0;
    int pos = 0;
    int pos2 = 0;

    if (str[pos] == '-') {
        negative = 1;
        pos++;
    }  /* Deal with negatives */
    else if (str[pos] == '+') { pos++; }  /* Deal with e.g. 1E+09 */

    while (((str[pos] >= '0') && (str[pos] <= '9')) || (str[pos] == '.')) {
        if (str[pos] == '.') {
            past_decimal_point = 1;
        } else {
            accumulator = ((10 * accumulator) + (((int) str[pos]) - 48));
            if (past_decimal_point == 1) decimals++;
        }
        pos++;
    }

    while (decimals != 0)                                         /* Deals with decimals */
    {
        decimals--;
        accumulator /= 10;
    }

    if (negative == 1) accumulator *= -1;                         /* Deals with negatives */

    if ((str[pos] == 'e') || (str[pos] == 'E'))
        accumulator *= pow(10.0, getFloat(str + pos + 1, &pos2)); /* Deals with exponents */

    if (pos2 > 0) pos += (1 + pos2); // Add on characters taken up by exponent, including one for the 'e' character.
    if (pos == 0) pos = -1; // Alert the user that this was a blank string!
    if (Nchars != NULL) *Nchars = pos;
    return (accumulator);
}

//! validFloat - See whether candidate string is a valid float
//! \param [in] str The input string
//! \param [out] end The number of characters occupied by the floating point value (optional)
//! \return Boolean flag indicating whether a valid floating-point value was found.

int validFloat(const char *str, int *end) {
    unsigned char past_decimal_point = 0, had_number = 0, expvalid = 1;
    int pos = 0;
    int pos2 = 0;

    if (str[pos] == '-') { pos++; }  /* Deal with negatives */
    else if (str[pos] == '+') { pos++; }  /* Deal with e.g. 1E+09 */

    while (((str[pos] >= '0') && (str[pos] <= '9')) || (str[pos] == '.')) {
        if (str[pos] == '.') {
            if (past_decimal_point) goto VALID_FLOAT_ENDED;
            else past_decimal_point = 1;
        } else { had_number = 1; }
        pos++;
    }

    if (!had_number) return 0;

    if ((str[pos] == 'e') || (str[pos] == 'E')) /* Deals with exponents */
    {
        expvalid = validFloat(str + pos + 1, &pos2);
        pos += pos2 + 1;
    }

    while ((str[pos] != '\0') && (str[pos] <= ' ')) pos++; /* Fast-forward over spaces at end */

    VALID_FLOAT_ENDED:
    if ((!had_number) || (!expvalid)) return 0;
    if (end == NULL) return 1;
    if ((*end >= 0) && (pos < *end)) return 0;
    *end = pos;
    return 1;
}

//! numericDisplay - Render a string-representation of a double in either %f or %e formats
//! \param in The floating point value to render
//! \param N Choose one of four internal static char buffers to hold the result (N=0...3)
//! \param SigFig The number of significant figures to display
//! \param latex Boolean flag indicating whether we should produce LaTeX output (true) or human-readable output (false)
//! \return String-representation, contained in a static char buffer which may be overwritten by subsequent calls

char *numericDisplay(double in, int N, int SigFig, int latex) {
    static char format[16], outputA[128], outputB[128], outputC[128], outputD[128];
    double x, AccLevel;
    char *output;
    int DecimalLevel, DPmax, i, j, k, l;
    if (N == 0) output = outputA;
    else if (N == 1) output = outputB;
    else if (N == 2) output = outputC;
    else output = outputD;
    if ((fabs(in) < 1e10) && (fabs(in) > 1e-3)) {
        x = fabs(in);
        AccLevel = x * (1.0 + pow(10, -SigFig));
        DPmax = SigFig - log10(x);
        for (DecimalLevel = 0; DecimalLevel < DPmax; DecimalLevel++)
            if ((x - ((floor(x * pow(10, DecimalLevel)) / pow(10, DecimalLevel)) - x)) < AccLevel)break;
        sprintf(format, "%%.%df", DecimalLevel);
        sprintf(output, format, in);
    } else {
        if (in == 0) { sprintf(output, "0"); }
        else {
            x = fabs(in);
            x /= pow(10, (int) log10(x));
            AccLevel = x * (1.0 + pow(10, -SigFig));
            for (DecimalLevel = 0; DecimalLevel < SigFig; DecimalLevel++)
                if ((x - ((floor(x * pow(10, DecimalLevel)) / pow(10, DecimalLevel)) - x)) < AccLevel)break;
            sprintf(format, "%%.%de", DecimalLevel);
            sprintf(output, format, in);
            if (latex) // Turn 1e10 into nice latex
            {
                for (i = 0; ((output[i] != '\0') && (output[i] != 'e') && (output[i] != 'E')); i++);
                if (output[i] != '\0') {
                    for (j = i, k = i + 32; output[j] != '\0'; j++) output[j + 32] = output[j];
                    output[j + 32] = '\0';
                    if ((i == 1) && (output[0] == '1')) {
                        strcpy(output, "10^{");
                        i = strlen(output);
                    } // Don't output 1 times 10^3
                    else {
                        strcpy(output + i, "\\times10^{");
                        i += strlen(output + i);
                    } // Replace e with times ten to the...
                    k++; // FFW over the E
                    if (output[k] == '+') k++; // We don't need to say +8... 8 will do
                    for (l = 0, j = k; output[j] != '\0'; j++) {
                        if ((output[j] > '0') && (output[j] <= '9')) l = 1;
                        if ((l == 1) || (output[j] != '0')) output[i++] = output[j];
                    } // Turn -08 into -8
                    output[i++] = '}';
                    output[i++] = '\0';
                }
            }
        }
    }
    for (i = 0; ((output[i] != '\0') && (output[i] != '.')); i++); // If we have trailing decimal zeros, get rid of them
    if (output[i] != '.') return output;
    for (j = i + 1; isdigit(output[j]); j++);
    if (i == j) return output;
    for (k = j - 1; output[k] == '0'; k--);
    if (k == i) k--;
    k++;
    if (k == j) return output;
    for (l = 0; output[j + l] != '\0'; l++) output[k + l] = output[j + l];
    output[k + l] = '\0';
    return output;
}

//! dblEqual - Test whether two floating-point values are approximately equal, to within one part in 10^7
//! \param a First value
//! \param b Second value
//! \return Boolean flag indicating equality

unsigned char dblEqual(double a, double b) {
    if ((fabs(a) < 1e-100) && (fabs(b) < 1e-100)) return 1;
    if ((fabs(a - b) < fabs(1e-7 * a)) && (fabs(a - b) < fabs(1e-7 * b))) return 1;
    return 0;
}

//! file_readline - Read a line from a file into a character buffer, up until the next newline character. A maximum
//! of MaxLength characters are read. The output character buffer is always null-terminated. The file handle is
//! fast-forwarded to the next newline, or by MaxLength characters, whichever happens sooner.
//! \param file The file handle to read from
//! \param output The character buffer into which to write the characters read
//! \param MaxLength The maximum number of characters to write to output, including null termination

void file_readline(FILE *file, char *output, int MaxLength) {
    char c = '\x07';
    char *outputscan = output;
    int i = 0;

    while (((int) c != '\n') && (!feof(file)) && (!ferror(file)))
        if ((fscanf(file, "%c", &c) >= 0) && ((c > 31) || (c == 9)) && (i < MaxLength - 2)) {
            i++;
            *(outputscan++) = c;
        } // ASCII 9 is a tab
    *(outputscan++) = '\0';
}

//! getWord - Returns the first word from <in>, terminated by any whitespace. Returns a maximum of <max> characters.
//! \param out The character buffer into which to write the extracted word. Always null terminated.
//! \param in The input character stream
//! \param max The maximum number of characters to write to out, including null termination.

void getWord(char *out, const char *in, int max) {
    int count = 0;
    while ((*in <= ' ') && (*in > '\0')) in++; /*!< Fastforward over preceding whitespace */
    while (((*in > ' ') || (*in < '\0')) && (count < (max - 1))) {
        *(out++) = *(in++);
        count++;
    }
    *out = '\0'; /*!< Terminate output */
}

//! nextWord - Fast forward a character pointer over one word, and return pointer to next word.
//! \param in The pointer to the character array we are to advance by one word
//! \return The pointer to the first non-whitespace character of the second word in the input string

char *nextWord(char *in) {
    while ((*in <= ' ') && (*in > '\0')) in++; /*!< Fast-forward over preceding whitespace */
    while ((*in > ' ') || (*in < '\0')) in++; /*!< Fast-forward over one word */
    while ((*in <= ' ') && (*in > '\0')) in++; /*!< Fast-forward over whitespace before next word */
    return in; /*!< Return pointer to next word */
}

//! friendly_time_string - Return pointer to time string in standard format, stored in a static string buffer which will
//! by overwritten by subsequent function calls.
//! \param t The unix time stamp to represent. If zero, then the current time is represented.
//! \return A time string

char *friendly_time_string(double t) {
    static char output[256];

    if (!t) t = time(NULL);

    const double JD = t / 86400.0 + 2440587.5;
    int year, month, day, hour, min, status;
    double sec;
    inv_julian_day(JD, &year, &month, &day, &hour, &min, &sec, &status, output);
    char *mn = get_month_name(month);
    sprintf(output, "%c%c%c %02d %04d %02d:%02d:%02d", mn[0], mn[1], mn[2], day, year, hour, min, (int) sec);

    return output;
}

//! str_strip - Strip whitespace from both ends of a string and copy to a new character array
//! \param [in] in The input string to strip
//! \param [out] out Character buffer into which to write the stripped string
//! \return Pointer to <out>

char *str_strip(const char *in, char *out) {
    char *scan = out;
    while ((*in <= ' ') && (*in > '\0')) in++;
    while (*in != '\0') *(scan++) = *(in++);
    scan--;
    while ((scan > out) && (*scan >= '\0') && (*scan <= ' ')) scan--;
    *++scan = '\0';
    return out;
}

//! str_upper - Copy to capitalised version of a string into a new character buffer
//! \param [in] in The input string to be capitalised
//! \param [out] out The character buffer into which to write the capitalised version
//! \return Pointer to <out>

char *str_upper(const char *in, char *out) {
    char *scan = out;
    while (*in != '\0')
        if ((*in >= 'a') && (*in <= 'z')) *scan++ = *in++ + 'A' - 'a';
        else *scan++ = *in++;
    *scan = '\0';
    return out;
}


//! str_lower - Copy to lower-case version of a string into a new character buffer
//! \param [in] in The input string to be converted to lower-case
//! \param [out] out The character buffer into which to write the lower-case version
//! \return Pointer to <out>

char *str_lower(const char *in, char *out) {
    char *scan = out;
    while (*in != '\0')
        if ((*in >= 'A') && (*in <= 'Z')) *scan++ = *in++ + 'a' - 'A';
        else *scan++ = *in++;
    *scan = '\0';
    return out;
}


//! str_underline - Write a string of -s which is long enough to underline a string
//! \param [in] in The input string to be underlined
//! \param [out] out The character buffer into which to write the -s to underline <in>
//! \return Pointer to <out>

char *str_underline(const char *in, char *out) {
    char *scan = out;
    while (*in != '\0') {
        if ((*in >= ' ') || (*in < '\0')) *scan++ = '-';
        in++;
    }
    *scan = '\0';
    return out;
}

//! str_slice - Take a slice out of a string and copy it into a new character buffer
//! \param [in] in The input string to take a slice from
//! \param [out] out A character buffer into which to write the slice
//! \param [in] start The first character to copy into a slice
//! \param [in] end The character after the last one to copy into the slice
//! \return Pointer to <out>

char *str_slice(const char *in, char *out, int start, int end) {
    char *scan = out;
    int pos = 0;
    while ((pos < start) && (in[pos] != '\0')) pos++;
    while ((pos < end) && (in[pos] != '\0')) *(scan++) = in[pos++];
    *scan = '\0';
    return out;
}

//! str_comma_separated_list_scan - Extract the next item from a comma-separated list, and copy it to <out>
//! \param inscan A pointer to the input string. This is advanced to point to the character after the next comma.
//! \param out Character buffer into which to copy a stripped version of the next comma-separated value
//! \return Pointer to <out>

char *str_comma_separated_list_scan(char **inscan, char *out) {
    char *outscan = out;
    while ((**inscan != '\0') && (**inscan != ',')) *(outscan++) = *((*inscan)++);
    if (**inscan == ',') (*inscan)++; // Fast-forward over comma character
    *outscan = '\0';
    str_strip(out, out);
    return out;
}

//! str_word_wrap - Word wrap a piece of text to a certain width and copy it into a new character buffer
//! \param [in] in The input text
//! \param [out] out The character buffer into which to write the word-wrapped output
//! \param width The width of the column into which to fit the text

void str_word_wrap(const char *in, char *out, int width) {
    int WhiteSpace = 1;
    int LastSpace = -1;
    int LineStart = 0;
    int LineFeeds = 0; // If we meet > 1 linefeed during a period of whitespace, it marks the beginning of a new paragraph
    int i, j;
    for (i = 0, j = 0; in[i] != '\0'; i++) {
        if ((WhiteSpace == 1) && (in[i] <= ' ')) // Once we've encountered one space, ignore any further whitespaceness
        {
            if (j == 0)
                j++; // If we open document with a new paragraph, we haven't already put down a space character to overwrite
            if ((in[i] == '\n') && (++LineFeeds == 2)) {
                out[j - 1] = '\n';
                out[j] = '\n';
                LineStart = j++;
                LastSpace = -1;
            } // Two linefeeds in a period of whitespace means a new paragraph
            continue;
        }
        if ((WhiteSpace == 0) && (in[i] <= ' ')) // First whitespace character after a string of letters
        {
            if (in[i] == '\n') LineFeeds = 1;
            out[j] = ' ';
            LastSpace = j++;
            WhiteSpace = 1;
            continue;
        }
        if ((in[i] == '\\') && (in[i + 1] == '\\')) {
            i++;
            out[j] = '\n';
            LineStart = j++;
            LastSpace = -1;
            WhiteSpace = 1;
            continue;
        } // Double-backslash implies a hard linebreak.
        if (in[i] == '#') {
            out[j++] = ' ';
            WhiteSpace = 1;
            continue;
        } // A hash character implies a hard space character, used to tabulate data
        WhiteSpace = 0;
        LineFeeds = 0;
        if (((j - LineStart) > width) && (LastSpace != -1)) {
            out[LastSpace] = '\n';
            LineStart = LastSpace;
            LastSpace = -1;
        } // If line is too line, insert a linebreak
        if (strncmp(in + i, "\\lab", 4) == 0) {
            i += 3;
            out[j++] = '<';
            continue;
        } // Macros for left-angle-brackets, etc.
        if (strncmp(in + i, "\\rab", 4) == 0) {
            i += 3;
            out[j++] = '>';
            continue;
        }
        if (strncmp(in + i, "\\VERSION", 8) == 0) {
            i += 7;
            strcpy(out + j, VERSION);
            j += strlen(out + j);
            continue;
        }
        if (strncmp(in + i, "\\DATE", 5) == 0) {
            i += 4;
            strcpy(out + j, DATE);
            j += strlen(out + j);
            continue;
        }
        out[j++] = in[i];
    }
    out[j] = '\0';
}

//! str_cmp_no_case - A case-insensitive version of the standard strcmp() function
//! \param a First string
//! \param b Second string
//! \return Comparison between strings

int str_cmp_no_case(const char *a, const char *b) {
    char aU, bU;
    while (1) {
        if ((*a == '\0') && (*b == '\0')) return 0;
        if (*a == *b) {
            a++;
            b++;
            continue;
        }
        if ((*a >= 'a') && (*a <= 'z')) aU = *a - 'a' + 'A'; else aU = *a;
        if ((*b >= 'a') && (*b <= 'z')) bU = *b - 'a' + 'A'; else bU = *b;
        if (aU == bU) {
            a++;
            b++;
            continue;
        }
        if (aU < bU) return -1;
        return 1;
    }
}

//! readConfig_FetchKey - Read a line of a configuration file, in the format <key=value>. Extract the key and copy it
//! into the character buffer <out>.
//! \param [in] line The input line of the configuration file
//! \param [out] out The character buffer into which to write the key

void readConfig_FetchKey(char *line, char *out) {
    char *scan = out;
    while ((*line != '\0') && ((*(scan) = *(line++)) != '=')) scan++;
    *scan = '\0';
    str_strip(out, out);
}

//! readConfig_FetchValue - Read a line of a configuration file, in the format <key=value>. Extract the value and copy
//! it into the character buffer <out>.
//! \param [in] line The input line of the configuration file
//! \param [out] out The character buffer into which to write the value

void readConfig_FetchValue(char *line, char *out) {
    char *scan = out;
    while ((*line != '\0') && (*(line++) != '='));
    while (*line != '\0') *(scan++) = *(line++);
    *scan = '\0';
    str_strip(out, out);
}

