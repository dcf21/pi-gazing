// jpeg.h
// $Id: jpeg.h 1137 2014-11-24 22:18:14Z pyxplot $

#ifndef JPEG_H
#define JPEG_H 1

/* Variable format used to store images */

typedef struct {
                int xsize;
                int ysize;
                double *data_red;
                double *data_grn;
                double *data_blu;
                double *data_w;
               } jpeg_ptr;

/* Functions defined in jpeg_in.c */
void jpeg_alloc(jpeg_ptr *out, int x, int y);
void jpeg_dealloc(jpeg_ptr *in);
void jpeg_cp(jpeg_ptr *in, jpeg_ptr *out);
void jpeg_deweight(jpeg_ptr *out);
jpeg_ptr jpeg_get(char *filename);

/* Functions defined in jpeg_out.c */
int jpeg_put(char *filename, jpeg_ptr image);

#endif

