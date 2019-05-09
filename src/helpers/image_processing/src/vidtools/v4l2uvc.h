/*******************************************************************************
#	 	luvcview: Sdl video Usb Video Class grabber          .         #
#This package work with the Logitech UVC based webcams with the mjpeg feature. #
#All the decoding is in user space with the embedded jpeg decoder              #
#.                                                                             #
# 		Copyright (C) 2005 2006 Laurent Pinchart &&  Michel Xhaard     #
#                                                                              #
# This program is free software; you can redistribute it and/or modify         #
# it under the terms of the GNU General Public License as published by         #
# the Free Software Foundation; either version 2 of the License, or            #
# (at your option) any later version.                                          #
#                                                                              #
# This program is distributed in the hope that it will be useful,              #
# but WITHOUT ANY WARRANTY; without even the implied warranty of               #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                #
# GNU General Public License for more details.                                 #
#                                                                              #
# You should have received a copy of the GNU General Public License            #
# along with this program; if not, write to the Free Software                  #
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA    #
#                                                                              #
*******************************************************************************/

#ifndef _HAVE_V4L_H
#define _HAVE_V4L_H 1

#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/select.h>
#include <linux/videodev2.h>

#include "uvcvideo.h"

#define NB_BUFFER 4

struct video_info {
    int fd;
    char *video_device;
    char *status;
    char *pict_name;
    struct v4l2_capability cap;
    struct v4l2_format fmt;
    struct v4l2_buffer buf;
    struct v4l2_requestbuffers rb;
    void *mem[NB_BUFFER];
    unsigned char *tmp_buffer;
    unsigned char *frame_buffer;
    int is_streaming;
    int grab_method;
    int width;
    int height;
    float fps;
    int format_in;
    int frame_size_in;
    int upside_down;
};

int check_videoIn(struct video_info *vd, char *device);

int init_videoIn(struct video_info *vd, char *device, int width, int height, float fps, int format, int grab_method);

int uvcGrab(struct video_info *vd);

int enum_frame_intervals(int dev, __u32 pixfmt, __u32 width, __u32 height);

int enum_frame_sizes(int dev, __u32 pixfmt);

int enum_frame_formats(int dev, unsigned int *supported_formats, unsigned int max_formats);

#endif
