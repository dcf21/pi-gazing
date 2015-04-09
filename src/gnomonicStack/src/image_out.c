// image_out.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdlib.h>
#include <stdio.h>
#include "image.h"
#include <png.h>

/* IMAGE_PUT(): Turns bitmap data into a image file */

int image_put(char *frOut, image_ptr image)
 {
  int code=0;

  const int width = image.xsize;
  const int height= image.ysize;

  FILE *fp;
  png_structp png_ptr;
  png_infop info_ptr = NULL;
  png_bytep row = NULL;

  // Open file for writing (binary mode)
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
  int p=0;
  for (y=0 ; y<height ; y++) {
     for (x=0 ; x<width ; x++) {
        row[x*3+0] = image.data_red[p];
        row[x*3+1] = image.data_grn[p];
        row[x*3+2] = image.data_blu[p];
        p++;
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

  return code;

 }
