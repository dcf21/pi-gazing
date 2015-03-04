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
               } image_ptr;

/* Variable format used to image pixels */

typedef struct {
                double red;
                double grn;
                double blu;
               } pixel;

/* Functions defined in jpeg_in.c */
void jpeg_alloc(image_ptr *out, int x, int y);
void jpeg_dealloc(image_ptr *in);
void jpeg_cp(image_ptr *in, image_ptr *out);
void jpeg_deweight(image_ptr *out);
image_ptr jpeg_get(char *filename);

/* Functions defined in jpeg_out.c */
int jpeg_put(char *filename, image_ptr image);

#endif

