// jpeg_out.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdlib.h>
#include <stdio.h>
#include "jpeg/jpeg.h"
#include <jpeglib.h>

/* JPEG_PUT(): Turns bitmap data into a jpeg file */

int jpeg_put(char *filename, image_ptr image)
{
  unsigned char *line_buffer = malloc(3*image.xsize);
  unsigned char *line_scan;
  double *red_scan, *grn_scan, *blu_scan;
  int x;

  /* This struct contains the JPEG compression parameters and pointers to
   * working space (which is allocated as needed by the JPEG library).
   * It is possible to have several such structures, representing multiple
   * compression/decompression processes, in existence at once.  We refer
   * to any one struct (and its associated working data) as a "JPEG object".
   */
  struct jpeg_compress_struct cinfo;
  /* This struct represents a JPEG error handler.  It is declared separately
   * because applications often want to supply a specialized error handler
   * (see the second half of this file for an example).  But here we just
   * take the easy way out and use the standard error handler, which will
   * print a message on stderr and call exit() if compression fails.
   * Note that this struct must live as long as the main JPEG parameter
   * struct, to avoid dangling-pointer problems.
   */
  struct jpeg_error_mgr jerr;
  /* More stuff */
  FILE * outfile;		/* target file */
  JSAMPROW row_pointer[1];	/* pointer to JSAMPLE row[s] */
  // int row_stride;		/* physical row width in image buffer */
  
  /* Step 1: allocate and initialize JPEG compression object */

  /* We have to set up the error handler first, in case the initialization
   * step fails.  (Unlikely, but it could happen if you are out of memory.)
   * This routine fills in the contents of struct jerr, and returns jerr's
   * address which we place into the link field in cinfo.
   */
  cinfo.err = jpeg_std_error(&jerr);
  /* Now we can initialize the JPEG compression object. */
  jpeg_create_compress(&cinfo);

  /* Step 2: specify data destination (eg, a file) */
  /* Note: steps 2 and 3 can be done in either order. */

  /* Here we use the library-supplied code to send compressed data to a
   * stdio stream.  You can also write your own code to do something else.
   * VERY IMPORTANT: use "b" option to fopen() if you are on a machine that
   * requires it in order to write binary files.
   */
  if ((outfile = fopen(filename, "wb")) == NULL) {
    fprintf(stderr, "ERROR: Cannot open output JPEG file %s.\n", filename);
    free(line_buffer);
    return(FALSE);
  }
  jpeg_stdio_dest(&cinfo, outfile);

  /* Step 3: set parameters for compression */

  /* First we supply a description of the input image.
   * Four fields of the cinfo struct must be filled in:
   */
  cinfo.image_width = image.xsize; 	/* image width and height, in pixels */
  cinfo.image_height = image.ysize;
  cinfo.input_components = 3;			/* # of color components per pixel */
  cinfo.in_color_space = JCS_RGB; 	/* colorspace of input image */
  /* Now use the library's routine to set default compression parameters.
   * (You must set at least cinfo.in_color_space before calling this,
   * since the defaults depend on the source color space.)
   */
  jpeg_set_defaults(&cinfo);
  /* Now you can set any non-default parameters you wish to.
   * Here we just illustrate the use of quality (quantization table) scaling:
   */
  jpeg_set_quality(&cinfo, 100, TRUE);

  /* Step 4: Start compressor */

  /* TRUE ensures that we will write a complete interchange-JPEG file.
   * Pass TRUE unless you are very sure of what you're doing.
   */
  jpeg_start_compress(&cinfo, TRUE);

  /* Step 5: while (scan lines remain to be written) */
  /*           jpeg_write_scanlines(...); */

  /* Here we use the library's state variable cinfo.next_scanline as the
   * loop counter, so that we don't have to keep track ourselves.
   * To keep things simple, we pass one scanline per call; you can pass
   * more if you wish, though.
   */
  // row_stride = image.xsize;	/* JSAMPLEs per row in image_buffer */

  red_scan = image.data_red;
  grn_scan = image.data_grn;
  blu_scan = image.data_blu;

  while (cinfo.next_scanline < cinfo.image_height) {
    /* jpeg_write_scanlines expects an array of pointers to scanlines.
     * Here the array is only one element long, but you could pass
     * more than one scanline at a time if that's more convenient.
     */
     
    line_scan = line_buffer;
    //y = cinfo.next_scanline; 
    for (x=0; x<image.xsize; x++)
    {
          if (*red_scan <   0.0) *(line_scan  ) =   0;
     else if (*red_scan > 255.0) *(line_scan  ) = 255;
     else                        *(line_scan  ) = (int)(*red_scan);

          if (*grn_scan <   0.0) *(line_scan+1) =   0;
     else if (*grn_scan > 255.0) *(line_scan+1) = 255;
     else                        *(line_scan+1) = (int)(*grn_scan);

          if (*blu_scan <   0.0) *(line_scan+2) =   0;
     else if (*blu_scan > 255.0) *(line_scan+2) = 255;
     else                        *(line_scan+2) = (int)(*blu_scan);

     line_scan+=3;
     red_scan++; grn_scan++; blu_scan++;
    }
    row_pointer[0] = line_buffer;
    (void) jpeg_write_scanlines(&cinfo, row_pointer, 1);
  }

  /* Step 6: Finish compression */

  jpeg_finish_compress(&cinfo);
  /* After finish_compress, we can close the output file. */
  fclose(outfile);

  /* Step 7: release JPEG compression object */

  /* This is an important step since it will release a good deal of memory. */
  jpeg_destroy_compress(&cinfo);

  /* And we're done! */
  
  free(line_buffer);
  return(0);
}
