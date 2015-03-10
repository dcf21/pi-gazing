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

unsigned char
RGB24_TO_Y(unsigned char r, unsigned char g, unsigned char b)
{
return (LutYr[(r)] + LutYg[(g)] + LutYb[(b)]);
}
unsigned char
YR_TO_V(unsigned char r, unsigned char y)
{
return (LutVr[(r)] + LutVrY[(y)]);
}
unsigned char
YB_TO_U(unsigned char b, unsigned char y)
{
return (LutUb[(b)] + LutUbY[(y)]);
}
unsigned char
R_FROMYV(unsigned char y, unsigned char v)
{
return CLIPCHAR((y) + LutRv[(v)]);
}
unsigned char
G_FROMYUV(unsigned char y, unsigned char u, unsigned char v)
{
return CLIPCHAR((y) + LutGu[(u)] + LutGv[(v)]);
}
unsigned char
B_FROMYU(unsigned char y, unsigned char u)
{
return CLIPCHAR((y) + LutBu[(u)]);
}

void initLut(void)
{
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
   
   LutYr = malloc(256*sizeof(int));
   LutYg = malloc(256*sizeof(int));
   LutYb = malloc(256*sizeof(int));
   LutVr = malloc(256*sizeof(int));
   LutVrY = malloc(256*sizeof(int));
   LutUb = malloc(256*sizeof(int));
   LutUbY = malloc(256*sizeof(int));
   
   LutRv = malloc(256*sizeof(int));
   LutGu = malloc(256*sizeof(int));
   LutGv = malloc(256*sizeof(int));
   LutBu = malloc(256*sizeof(int));
   for (i= 0;i < 256;i++){
       LutYr[i] = i*Rcoef/1000 ;
       LutYg[i] = i*Gcoef/1000 ;
       LutYb[i] = i*Bcoef/1000 ;
       LutVr[i] = i*Vrcoef/1000;
       LutUb[i] = i*Ubcoef/1000;
       LutVrY[i] = 128 -(i*Vrcoef/1000);
       LutUbY[i] = 128 -(i*Ubcoef/1000);
       LutRv[i] = (i-128)*CoefRv/1000;
       LutBu[i] = (i-128)*CoefBu/1000;
       LutGu[i] = (128-i)*CoefGu/1000;
       LutGv[i] = (128-i)*CoefGv/1000;
   }   
}


void freeLut(void){
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

void Pyuv422torgb24(unsigned char * input_ptr, unsigned char * output_ptr, unsigned int image_width, unsigned int image_height)
 {
   unsigned int i, size;
   unsigned char Y, Y1, U, V;
   unsigned char *buff = input_ptr;
   unsigned char *output_pt = output_ptr;
   size = image_width * image_height /2;
   for (i = size; i > 0; i--) {
      /* bgr instead rgb ?? */
      Y = buff[0] ;
      U = buff[1] ;
      Y1 = buff[2];
      V = buff[3];
      buff += 4;
      *output_pt++ = R_FROMYV(Y,V);
      *output_pt++ = G_FROMYUV(Y,U,V); //b
      *output_pt++ = B_FROMYU(Y,U); //v

      *output_pt++ = R_FROMYV(Y1,V);
      *output_pt++ = G_FROMYUV(Y1,U,V); //b
      *output_pt++ = B_FROMYU(Y1,U); //v
   }
 }

void Pyuv422toMono(unsigned char * input_ptr, unsigned char * output_ptr, unsigned int image_width, unsigned int image_height)
 {
   unsigned int i, size;
   unsigned char Y, Y1;
   unsigned char *buff = input_ptr;
   unsigned char *output_pt = output_ptr;
   size = image_width * image_height /2;
   for (i = size; i > 0; i--) {
      Y = buff[0] ;
      Y1 = buff[2];
      buff += 4;
      *output_pt++ = Y;
      *output_pt++ = Y1;
   }
 }

