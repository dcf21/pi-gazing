/****************************************************************************
#       GspcaGui:  Gspca/Spca5xx Grabber                            #
#       Copyright (C) 2004 2005 2006 Michel Xhaard                  #
#                                                                           #
# This program is free software; you can redistribute it and/or modify      #
# it under the terms of the GNU General Public License as published by      #
# the Free Software Foundation; either version 2 of the License, or         #
# (at your option) any later version.                                       #
#                                                                           #
# This program is distributed in the hope that it will be useful,           #
# but WITHOUT ANY WARRANTY; without even the implied warranty of            #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
# GNU General Public License for more details.                              #
#                                                                           #
# You should have received a copy of the GNU General Public License         #
# along with this program; if not, write to the Free Software               #
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA #
#                                                                           #
****************************************************************************/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h> 
#include "vidtools/color.h"

static int *LutYr = NULL;
static int *LutYg = NULL;;
static int *LutYb = NULL;;
static int *LutVr = NULL;;
static int *LutVrY = NULL;;
static int *LutUb = NULL;;
static int *LutUbY = NULL;;
static int *LutRv = NULL;
static int *LutGu = NULL;
static int *LutGv = NULL;
static int *LutBu = NULL;

#if 0
#define RGB24_TO_Y(r,g,b) LutYr[(r)] + LutYg[(g)] + LutYb[(b)]
#define YR_TO_V(r,y) LutVr[(r)] + LutVrY[(y)]
#define YB_TO_U(b,y) LutUb[(b)] + LutUbY[(y)]

#define R_FROMYV(y,v)  CLIPCHAR((y) + LutRv[(v)])
#define G_FROMYUV(y,u,v) CLIPCHAR((y) + LutGu[(u)] + LutGv[(v)])
#define B_FROMYU(y,u) CLIPCHAR((y) + LutBu[(u)])
#endif

inline unsigned char RGB24_TO_Y(unsigned char r, unsigned char g, unsigned char b) {
    return (LutYr[(r)] + LutYg[(g)] + LutYb[(b)]);
}

inline unsigned char YR_TO_V(unsigned char r, unsigned char y) { return (LutVr[(r)] + LutVrY[(y)]); }

inline unsigned char YB_TO_U(unsigned char b, unsigned char y) { return (LutUb[(b)] + LutUbY[(y)]); }

inline unsigned char R_FROMYV(unsigned char y, unsigned char v) { return CLIPCHAR((y) + LutRv[(v)]); }

inline unsigned char G_FROMYUV(unsigned char y, unsigned char u, unsigned char v) {
    return CLIPCHAR((y) + LutGu[(u)] + LutGv[(v)]);
}

inline unsigned char B_FROMYU(unsigned char y, unsigned char u) { return CLIPCHAR((y) + LutBu[(u)]); }

void initLut(void) {
    int i;
#define Rcoef 299
#define Gcoef 587
#define Bcoef 114
#define Vrcoef 711 //656 //877
#define Ubcoef 560 //500 //493 564

#define CoefRv 1402
#define CoefGu 714 // 344
#define CoefGv 344 // 714
#define CoefBu 1772

    LutYr = malloc(256 * sizeof(int));
    LutYg = malloc(256 * sizeof(int));
    LutYb = malloc(256 * sizeof(int));
    LutVr = malloc(256 * sizeof(int));
    LutVrY = malloc(256 * sizeof(int));
    LutUb = malloc(256 * sizeof(int));
    LutUbY = malloc(256 * sizeof(int));

    LutRv = malloc(256 * sizeof(int));
    LutGu = malloc(256 * sizeof(int));
    LutGv = malloc(256 * sizeof(int));
    LutBu = malloc(256 * sizeof(int));
    for (i = 0; i < 256; i++) {
        LutYr[i] = i * Rcoef / 1000;
        LutYg[i] = i * Gcoef / 1000;
        LutYb[i] = i * Bcoef / 1000;
        LutVr[i] = i * Vrcoef / 1000;
        LutUb[i] = i * Ubcoef / 1000;
        LutVrY[i] = 128 - (i * Vrcoef / 1000);
        LutUbY[i] = 128 - (i * Ubcoef / 1000);
        LutRv[i] = (i - 128) * CoefRv / 1000;
        LutBu[i] = (i - 128) * CoefBu / 1000;
        LutGu[i] = (128 - i) * CoefGu / 1000;
        LutGv[i] = (128 - i) * CoefGv / 1000;
    }
}


void freeLut(void) {
    free(LutYr);
    free(LutYg);
    free(LutYb);
    free(LutVr);
    free(LutVrY);
    free(LutUb);
    free(LutUbY);

    free(LutRv);
    free(LutGu);
    free(LutGv);
    free(LutBu);
}

void Pyuv422torgbstack(unsigned char *input_ptr, int *outR, int *outG, int *outB, unsigned int width,
                       unsigned int height, const int upsideDown) {
    unsigned int i;
    const int size = width * height;
#pragma omp parallel for private(i)
    for (i = 0; i < size / 2; i++) {
        unsigned char *b = input_ptr + i * 4;
        unsigned char Y = b[0];
        unsigned char U = b[1];
        unsigned char Y1 = b[2];
        unsigned char V = b[3];

        if (upsideDown) {
            int *R = outR + (size - 1) - i * 2;
            int *G = outG + (size - 1) - i * 2;
            int *B = outB + (size - 1) - i * 2;

            *R-- += R_FROMYV(Y, V);
            *G-- += G_FROMYUV(Y, U, V); //b
            *B-- += B_FROMYU(Y, U); //v

            *R += R_FROMYV(Y1, V);
            *G += G_FROMYUV(Y1, U, V); //b
            *B += B_FROMYU(Y1, U); //v
        } else {
            int *R = outR + i * 2;
            int *G = outG + i * 2;
            int *B = outB + i * 2;

            *R++ += R_FROMYV(Y, V);
            *G++ += G_FROMYUV(Y, U, V); //b
            *B++ += B_FROMYU(Y, U); //v

            *R += R_FROMYV(Y1, V);
            *G += G_FROMYUV(Y1, U, V); //b
            *B += B_FROMYU(Y1, U); //v
        }
    }
}

void Pyuv420torgb(unsigned char *Ydata, unsigned char *Udata, unsigned char *Vdata, unsigned char *outR,
                  unsigned char *outG, unsigned char *outB, const unsigned int width, const unsigned int height) {
    unsigned int i, j;

    const int stride0 = width;
    const int stride1 = width / 2;
    const int stride2 = width / 2;
#pragma omp parallel for private(i,j)
    for (i = 0; i < height; i++)
        for (j = 0; j < width; j++) {
            unsigned char Y = Ydata[i * stride0 + j];
            unsigned char U = Udata[(i / 2) * stride1 + (j / 2)];
            unsigned char V = Vdata[(i / 2) * stride2 + (j / 2)];
            *(outR + i * width + j) = R_FROMYV(Y, V);
            *(outG + i * width + j) = ALLDATAMONO ? 128 : G_FROMYUV(Y, U,
                                                                    V); // ALLDATAMONO is a compile-time flag which saves on CPU as this loop processes a lot of data
            *(outB + i * width + j) = ALLDATAMONO ? 128 : B_FROMYU(Y, U);
        }
}

void Pyuv422toMono(unsigned char *input_ptr, unsigned char *output_ptr, const unsigned int width,
                   const unsigned int height, const int upsideDown) {
    unsigned int i;
    const int size = width * height / 2;
#pragma omp parallel for private(i)
    for (i = 0; i < size; i++) {
        unsigned char *b = input_ptr + 4 * (upsideDown ? i : (size - 1 - i));
        unsigned char Y = b[0];
        unsigned char Y1 = b[2];
        unsigned char *output_pt = output_ptr + 2 * i;
        if (!upsideDown) {
            *output_pt++ = Y;
            *output_pt = Y1;
        }
        else {
            *output_pt++ = Y1;
            *output_pt = Y;
        }
    }
}

void Pyuv422to420(unsigned char *input_ptr, unsigned char *output_ptr, const unsigned int width,
                  const unsigned int height, const int upsideDown) {
    int i;
    const int size = width * height;

#pragma omp parallel for private(i)
    for (i = 0; i < height; i++) {
        unsigned char *b;
        unsigned char *outY = output_ptr + i * width;
        unsigned char *outU = output_ptr + (i / 2) * (width / 2) + size;
        unsigned char *outV = output_ptr + (i / 2) * (width / 2) + size * 5 / 4;
        if (!upsideDown) b = input_ptr + 2 * width * i;
        else b = input_ptr - 2 * width * i + 2 * width * height - 4;

        int j;
        for (j = 0; j < width / 2; j++) {
            unsigned char Y = b[0];
            unsigned char U = ALLDATAMONO ? 128 : b[1];
            unsigned char Y1 = b[2];
            unsigned char V = ALLDATAMONO ? 128 : b[3];

            if (!upsideDown) {
                *(outY++) = Y;
                *(outY++) = Y1;
                b += 4;
            } else {
                *(outY++) = Y1;
                *(outY++) = Y;
                b -= 4;
            }
            *(outU++) = U;
            *(outV++) = V;
        }
    }
}

