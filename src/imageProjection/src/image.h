// image.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef JPEG_H
#define JPEG_H 1

/* Variable format used to store images */

typedef struct {
    int xsize;
    int ysize;
    double *data_w;
    double *data_red;
    double *data_grn;
    double *data_blu;
} image_ptr;

/* Variable format used to image pixels */

typedef struct {
    double red;
    double grn;
    double blu;
} pixel;

/* Functions defined in image_in.c */
void image_alloc(image_ptr *out, int x, int y);

void image_dealloc(image_ptr *in);

void image_cp(image_ptr *in, image_ptr *out);

void image_deweight(image_ptr *out);

image_ptr image_get(char *filename);

/* Functions defined in image_out.c */
int image_put(char *filename, image_ptr image);

#endif

