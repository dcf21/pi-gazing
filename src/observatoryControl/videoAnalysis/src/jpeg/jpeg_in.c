// jpeg_in.c
// $Id: jpeg_in.c 1137 2014-11-24 22:18:14Z pyxplot $

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <gsl/gsl_math.h>
#include "jpeg.h"
#include <jpeglib.h>

void jpeg_alloc(jpeg_ptr *out, int x, int y) {
    int i, j = x * y;

    out->xsize = x;
    out->ysize = y;
    out->data_red = (double *) malloc(x * y * sizeof(double));
    out->data_grn = (double *) malloc(x * y * sizeof(double));
    out->data_blu = (double *) malloc(x * y * sizeof(double));
    out->data_w = (double *) malloc(x * y * sizeof(double));
    for (i = 0; i < j; i++) out->data_red[i] = 0.0;
    for (i = 0; i < j; i++) out->data_grn[i] = 0.0;
    for (i = 0; i < j; i++) out->data_blu[i] = 0.0;
    for (i = 0; i < j; i++) out->data_w[i] = 0.0;
    return;
}

void jpeg_dealloc(jpeg_ptr *in) {
    if (in->data_red != NULL) free(in->data_red);
    if (in->data_grn != NULL) free(in->data_grn);
    if (in->data_blu != NULL) free(in->data_blu);
    if (in->data_w != NULL) free(in->data_w);
    return;
}

void jpeg_cp(jpeg_ptr *in, jpeg_ptr *out) {
    jpeg_alloc(out, in->xsize, in->ysize);
    memcpy(out->data_red, in->data_red, in->xsize * in->ysize * sizeof(double));
    memcpy(out->data_grn, in->data_grn, in->xsize * in->ysize * sizeof(double));
    memcpy(out->data_blu, in->data_blu, in->xsize * in->ysize * sizeof(double));
    memcpy(out->data_w, in->data_w, in->xsize * in->ysize * sizeof(double));
    return;
}

void jpeg_deweight(jpeg_ptr *out) {
    int i, j = out->xsize * out->ysize;
    for (i = 0; i < j; i++) {
        out->data_red[i] /= out->data_w[i];
        if (!gsl_finite(out->data_red[i])) out->data_red[i] = 0.0;
    }
    for (i = 0; i < j; i++) {
        out->data_grn[i] /= out->data_w[i];
        if (!gsl_finite(out->data_grn[i])) out->data_grn[i] = 0.0;
    }
    for (i = 0; i < j; i++) {
        out->data_blu[i] /= out->data_w[i];
        if (!gsl_finite(out->data_blu[i])) out->data_blu[i] = 0.0;
    }
    return;
}

/* JPEG_IN(): Read in JPEG file, and return image structure */

jpeg_ptr jpeg_get(char *filename) {
    jpeg_ptr output;
    output.xsize = output.ysize = -1;
    output.data_red = output.data_grn = output.data_blu = output.data_w = NULL;
    JSAMPARRAY buffer;    /* Output row buffer */
    unsigned char *buffer_scan;
    double *red_scan, *grn_scan, *blu_scan;
    int x;

    FILE *infile;

    if ((infile = fopen(filename, "rb")) == NULL) {
        fprintf(stderr, "ERROR: Cannot open input file %s\n", filename);
        return output;
    }

    /* This struct contains the JPEG compression parameters and pointers to
     * working space (which is allocated as needed by the JPEG library).
     * It is possible to have several such structures, representing multiple
     * compression/decompression processes, in existence at once.  We refer
     * to any one struct (and its associated working data) as a "JPEG object".
     */
    struct jpeg_decompress_struct cinfo;
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
    int row_stride;    /* physical row width in image buffer */

    /* Step 1: allocate and initialize JPEG compression object */

    /* We have to set up the error handler first, in case the initialization
     * step fails.  (Unlikely, but it could happen if you are out of memory.)
     * This routine fills in the contents of struct jerr, and returns jerr's
     * address which we place into the link field in cinfo.
     */
    cinfo.err = jpeg_std_error(&jerr);
    /* Now we can initialize the JPEG compression object. */
    jpeg_create_decompress(&cinfo);
    jpeg_stdio_src(&cinfo, infile);
    (void) jpeg_read_header(&cinfo, TRUE);
    (void) jpeg_start_decompress(&cinfo);
    row_stride = cinfo.output_width * cinfo.output_components;

    buffer = (*cinfo.mem->alloc_sarray)((j_common_ptr) &cinfo, JPOOL_IMAGE, row_stride, 1);

    output.xsize = cinfo.output_width;
    output.ysize = cinfo.output_height;
    red_scan = output.data_red = (double *) (malloc(output.xsize * output.ysize * sizeof(double)));
    grn_scan = output.data_grn = (double *) (malloc(output.xsize * output.ysize * sizeof(double)));
    blu_scan = output.data_blu = (double *) (malloc(output.xsize * output.ysize * sizeof(double)));

    while (cinfo.output_scanline < cinfo.output_height) {
        (void) jpeg_read_scanlines(&cinfo, buffer, 1);

        buffer_scan = buffer[0];
        for (x = 0; x < output.xsize; x++) {
            *(red_scan++) = (double) *(buffer_scan++);
            *(grn_scan++) = (double) *(buffer_scan++);
            *(blu_scan++) = (double) *(buffer_scan++);
        }
    }

    (void) jpeg_finish_decompress(&cinfo);
    jpeg_destroy_decompress(&cinfo);
    fclose(infile);
    return (output);
}

