// raw2rgbpng.c
// $Id$

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "tools.h"
#include "jpeg.h"
#include "error.h"
#include "png.h"
#include "settings.h"

int main(int argc, char *argv[])
 {
  int i;

  if (argc!=3)
   {
    sprintf(temp_err_string, "ERROR: Need to specify raw image filename on commandline, followed by output frame filename, e.g. 'raw2rgbjpeg foo.raw frame.jpg'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  char *rawFname = argv[1];
  char *fname = argv[2];
  char frOut[4096];

  FILE *infile;
  if ((infile = fopen(rawFname,"rb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output raw image file %s.\n", rawFname); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  int width, height;
  i=fread(&width ,sizeof(int),1,infile);
  i=fread(&height,sizeof(int),1,infile);

  const int frameSize=width*height;
  unsigned char *vidRawR = malloc(frameSize);
  unsigned char *vidRawG = malloc(frameSize);
  unsigned char *vidRawB = malloc(frameSize);
  if ( (vidRawR==NULL) || (vidRawG==NULL) || (vidRawB==NULL) ) { sprintf(temp_err_string, "ERROR: malloc fail in raw2rgbjpeg."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }
  i=fread(vidRawR,1,frameSize,infile);
  i=fread(vidRawG,1,frameSize,infile);
  i=fread(vidRawB,1,frameSize,infile);
  fclose(infile);

  int code = 0;

  for (i=0; i<3; i++)
   {
    if (code) break;

    unsigned char *vidRaw = NULL;
    if      (i==0) vidRaw=vidRawR;
    else if (i==1) vidRaw=vidRawG;
    else           vidRaw=vidRawB;

    FILE *fp;
    png_structp png_ptr;
    png_infop info_ptr = NULL;
    png_bytep row = NULL;

    // Open file for writing (binary mode)
    sprintf(frOut,"%s.%d",fname,i);
    fp = fopen(frOut, "wb");
    if (fp == NULL) {
       fprintf(stderr, "Could not open file %s for writing\n", frOut);
       code = 1;
       goto finalise;
    }

    // Initialize write structure
    png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    if (png_ptr == NULL) {
       fprintf(stderr, "Could not allocate write struct\n");
       code = 1;
       goto finalise;
    }

    // Initialize info structure
    info_ptr = png_create_info_struct(png_ptr);
    if (info_ptr == NULL) {
       fprintf(stderr, "Could not allocate info struct\n");
       code = 1;
       goto finalise;
    }

    // Setup Exception handling
    if (setjmp(png_jmpbuf(png_ptr))) {
       fprintf(stderr, "Error during png creation\n");
       code = 1;
       goto finalise;
    }

    png_init_io(png_ptr, fp);

    // Write header (8 bit colour depth)
    png_set_IHDR(png_ptr, info_ptr, width, height,
          8, PNG_COLOR_TYPE_RGB, PNG_INTERLACE_NONE,
          PNG_COMPRESSION_TYPE_BASE, PNG_FILTER_TYPE_BASE);

    // Set title
    png_text title_text;
    title_text.compression = PNG_TEXT_COMPRESSION_NONE;
    title_text.key = "Title";
    title_text.text = frOut;
    png_set_text(png_ptr, info_ptr, &title_text, 1);

    png_write_info(png_ptr, info_ptr);

    // Allocate memory for one row (3 bytes per pixel - RGB)
    row = (png_bytep) malloc(3 * width * sizeof(png_byte));

    // Write image data
    int x, y;
    int p = VIDEO_UPSIDE_DOWN ? (frameSize-1) : 0; // Raw frames are upside down, so we read them backwards from last pixel to first
    for (y=0 ; y<height ; y++) {
       for (x=0 ; x<width ; x++) {
          row[x*3+0] = vidRaw[p];
          row[x*3+1] = vidRaw[p];
          row[x*3+2] = vidRaw[p];
          if (VIDEO_UPSIDE_DOWN) { p--; } else { p++; }
       }
       png_write_row(png_ptr, row);
    }

    // End write
    png_write_end(png_ptr, NULL);

    finalise:
    if (fp != NULL) fclose(fp);
    if (info_ptr != NULL) png_free_data(png_ptr, info_ptr, PNG_FREE_ALL, -1);
    if (png_ptr != NULL) png_destroy_write_struct(&png_ptr, (png_infopp)NULL);
    if (row != NULL) free(row);
   }

  free(vidRawR); free(vidRawG); free(vidRawB);
  return code;
 }

