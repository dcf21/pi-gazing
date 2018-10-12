// jpeg.h
// $Id: jpeg.h 1137 2014-11-24 22:18:14Z pyxplot $

// -------------------------------------------------
// Copyright 2016 Cambridge Science Centre.

// This file is part of Meteor Pi.

// Meteor Pi is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Meteor Pi is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

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

