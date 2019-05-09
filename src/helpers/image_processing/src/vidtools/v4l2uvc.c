/*******************************************************************************
#       uvcview: Sdl video Usb Video Class grabber           .         #
#This package work with the Logitech UVC based webcams with the mjpeg feature. #
#All the decoding is in user space with the embedded jpeg decoder              #
#.                                                                             #
#       Copyright (C) 2005 2006 Laurent Pinchart &&  Michel Xhaard     #
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

#include <stdlib.h>
#include <math.h>
#include <float.h>

#include <time.h>

#include <libv4l2.h>

#include "vidtools/v4l2uvc.h"

#define ARRAY_SIZE(a)      (sizeof(a) / sizeof((a)[0]))
#define FOURCC_FORMAT      "%c%c%c%c"
#define FOURCC_ARGS(c)      (c) & 0xFF, ((c) >> 8) & 0xFF, ((c) >> 16) & 0xFF, ((c) >> 24) & 0xFF

static int debug = 0;

static int init_v4l2(struct video_info *vd);

static int float_to_fraction_recursive(double f, double p, int *num, int *den) {
    int whole = (int) f;
    f = fabs(f - whole);

    if (f > p) {
        int n, d;
        int a = float_to_fraction_recursive(1 / f, p + p / f, &n, &d);
        *num = d;
        *den = d * a + n;
    } else {
        *num = 0;
        *den = 1;
    }
    return whole;
}

static void float_to_fraction(float f, int *num, int *den) {
    int whole = float_to_fraction_recursive(f, FLT_EPSILON, num, den);
    *num += whole * *den;
}

int check_videoIn(struct video_info *vd, char *device) {
    int ret;
    if (vd == NULL || device == NULL)
        return -1;
    vd->video_device = (char *) calloc(1, 16 * sizeof(char));
    snprintf(vd->video_device, 12, "%s", device);
    printf("Device information:\n");
    printf("  Device path:  %s\n", vd->video_device);
    if ((vd->fd = v4l2_open(vd->video_device, O_RDWR)) == -1) {
        perror("ERROR opening V4L interface");
        exit(1);
    }
    memset(&vd->cap, 0, sizeof(struct v4l2_capability));
    ret = v4l2_ioctl(vd->fd, VIDIOC_QUERYCAP, &vd->cap);
    if (ret < 0) {
        printf("Error opening device %s: unable to query device.\n",
               vd->video_device);
        goto fatal;
    }
    if ((vd->cap.capabilities & V4L2_CAP_VIDEO_CAPTURE) == 0) {
        printf("Error opening device %s: video capture not supported.\n",
               vd->video_device);
    }
    if (!(vd->cap.capabilities & V4L2_CAP_STREAMING)) {
        printf("%s does not support streaming i/o\n", vd->video_device);
    }
    if (!(vd->cap.capabilities & V4L2_CAP_READWRITE)) {
        printf("%s does not support read i/o\n", vd->video_device);
    }
    enum_frame_formats(vd->fd, NULL, 0);
    fatal:
    v4l2_close(vd->fd);
    free(vd->video_device);
    return 0;
}

int init_videoIn(struct video_info *vd, char *device, int width, int height, float fps, int format, int grab_method) {
    if (vd == NULL || device == NULL)return -1;
    if (width == 0 || height == 0) return -1;
    if (grab_method < 0 || grab_method > 1) grab_method = 1;      //mmap by default;
    vd->video_device = NULL;
    vd->status = NULL;
    vd->pict_name = NULL;
    vd->video_device = (char *) calloc(1, 16 * sizeof(char));
    vd->status = (char *) calloc(1, 100 * sizeof(char));
    vd->pict_name = (char *) calloc(1, 80 * sizeof(char));
    snprintf(vd->video_device, 12, "%s", device);
    printf("Device information:\n");
    printf("  Device path:  %s\n", vd->video_device);
    vd->width = width;
    vd->height = height;
    vd->fps = fps;
    vd->format_in = format;
    vd->grab_method = grab_method;
    if (init_v4l2(vd) < 0) {
        printf(" Init v4L2 failed !! exit fatal\n");
        goto error;;
    }
    /* alloc a temp buffer to reconstruct the pict */
    vd->frame_size_in = (vd->width * vd->height << 1);
    switch (vd->format_in) {
        case V4L2_PIX_FMT_MJPEG:
            vd->tmp_buffer =
                    (unsigned char *) calloc(1, (size_t) vd->frame_size_in);
            if (!vd->tmp_buffer)
                goto error;
            vd->frame_buffer =
                    (unsigned char *) calloc(1,
                                             (size_t) vd->width * (vd->height +
                                                                   8) * 2);
            break;
        case V4L2_PIX_FMT_YUYV:
        case V4L2_PIX_FMT_UYVY:
            vd->frame_buffer =
                    (unsigned char *) calloc(1, (size_t) vd->frame_size_in);
            break;
        default:
            printf(" should never arrive exit fatal !!\n");
            goto error;
            break;
    }
    if (!vd->frame_buffer)
        goto error;
    return 0;
    error:
    free(vd->video_device);
    free(vd->status);
    free(vd->pict_name);
    v4l2_close(vd->fd);
    return -1;
}

static int init_v4l2(struct video_info *vd) {
    int i;
    int ret = 0;

    if ((vd->fd = v4l2_open(vd->video_device, O_RDWR)) == -1) {
        perror("ERROR opening V4L interface");
        exit(1);
    }
    memset(&vd->cap, 0, sizeof(struct v4l2_capability));
    ret = v4l2_ioctl(vd->fd, VIDIOC_QUERYCAP, &vd->cap);
    if (ret < 0) {
        printf("Error opening device %s: unable to query device.\n",
               vd->video_device);
        goto fatal;
    }

    if ((vd->cap.capabilities & V4L2_CAP_VIDEO_CAPTURE) == 0) {
        printf("Error opening device %s: video capture not supported.\n",
               vd->video_device);
        goto fatal;;
    }
    if (vd->grab_method) {
        if (!(vd->cap.capabilities & V4L2_CAP_STREAMING)) {
            printf("%s does not support streaming i/o\n", vd->video_device);
            goto fatal;
        }
    } else {
        if (!(vd->cap.capabilities & V4L2_CAP_READWRITE)) {
            printf("%s does not support read i/o\n", vd->video_device);
            goto fatal;
        }
    }

    printf("Stream settings:\n");

    // Enumerate the supported formats to check whether the requested one
    // is available. If not, we try to fall back to YUYV.
    unsigned int device_formats[16] = {0};   // Assume no device supports more than 16 formats
    int requested_format_found = 0, fallback_format = -1;
    if (enum_frame_formats(vd->fd, device_formats, ARRAY_SIZE(device_formats))) {
        printf("Unable to enumerate frame formats");
        goto fatal;
    }
    for (i = 0; i < ARRAY_SIZE(device_formats) && device_formats[i]; i++) {
        if (device_formats[i] == vd->format_in) {
            requested_format_found = 1;
            break;
        }
        if (device_formats[i] == V4L2_PIX_FMT_MJPEG || device_formats[i] == V4L2_PIX_FMT_YUYV
            || device_formats[i] == V4L2_PIX_FMT_UYVY)

            fallback_format = i;
    }
    if (requested_format_found) {
        // The requested format is supported
        printf("  Frame format: "FOURCC_FORMAT"\n", FOURCC_ARGS(vd->format_in));
    } else if (fallback_format >= 0) {
        // The requested format is not supported but there's a fallback format
        printf("  Frame format: "FOURCC_FORMAT" ("FOURCC_FORMAT
               " is not supported by device)\n",
               FOURCC_ARGS(device_formats[0]), FOURCC_ARGS(vd->format_in));
        vd->format_in = device_formats[0];
    } else {
        // The requested format is not supported and no fallback format is available
        printf("ERROR: Requested frame format "FOURCC_FORMAT" is not available "
               "and no fallback format was found.\n", FOURCC_ARGS(vd->format_in));
        goto fatal;
    }

    // Set pixel format and frame size
    memset(&vd->fmt, 0, sizeof(struct v4l2_format));
    vd->fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    vd->fmt.fmt.pix.width = vd->width;
    vd->fmt.fmt.pix.height = vd->height;
    vd->fmt.fmt.pix.pixelformat = vd->format_in;
    vd->fmt.fmt.pix.field = V4L2_FIELD_ANY;
    ret = v4l2_ioctl(vd->fd, VIDIOC_S_FMT, &vd->fmt);
    if (ret < 0) {
        perror("Unable to set format");
        goto fatal;
    }
    if ((vd->fmt.fmt.pix.width != vd->width) ||
        (vd->fmt.fmt.pix.height != vd->height)) {
        printf("  Frame size:   %ux%u (requested size %ux%u is not supported by device)\n",
               vd->fmt.fmt.pix.width, vd->fmt.fmt.pix.height, vd->width, vd->height);
        vd->width = vd->fmt.fmt.pix.width;
        vd->height = vd->fmt.fmt.pix.height;
        /* look the format is not part of the deal ??? */
        //vd->format_in = vd->fmt.fmt.pix.pixelformat;
    } else {
        printf("  Frame size:   %dx%d\n", vd->width, vd->height);
    }

    /* set framerate */
    struct v4l2_streamparm *setfps;
    setfps = (struct v4l2_streamparm *) calloc(1, sizeof(struct v4l2_streamparm));
    memset(setfps, 0, sizeof(struct v4l2_streamparm));
    setfps->type = V4L2_BUF_TYPE_VIDEO_CAPTURE;

    // Convert the frame rate into a fraction for V4L2
    int n = 0, d = 0;
    float_to_fraction(vd->fps, &n, &d);
    setfps->parm.capture.timeperframe.numerator = d;
    setfps->parm.capture.timeperframe.denominator = n;

    //ret = v4l2_ioctl(vd->fd, VIDIOC_S_PARM, setfps);
    //if(ret == -1) {
    //   perror("Unable to set frame rate");
    //   goto fatal;
    //}
    ret = v4l2_ioctl(vd->fd, VIDIOC_G_PARM, setfps);
    if (ret == 0) {
        float confirmed_fps = (float) setfps->parm.capture.timeperframe.denominator /
                              (float) setfps->parm.capture.timeperframe.numerator;
        if (confirmed_fps != (float) n / (float) d) {
            printf("  Frame rate:   %g fps (requested frame rate %g fps is "
                   "not supported by device)\n",
                   confirmed_fps,
                   vd->fps);
            vd->fps = confirmed_fps;
        } else {
            printf("  Frame rate:   %g fps\n", vd->fps);
        }
    } else {
        perror("Unable to read out current frame rate");
        goto fatal;
    }

    /* request buffers */
    memset(&vd->rb, 0, sizeof(struct v4l2_requestbuffers));
    vd->rb.count = NB_BUFFER;
    vd->rb.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    vd->rb.memory = V4L2_MEMORY_MMAP;

    ret = v4l2_ioctl(vd->fd, VIDIOC_REQBUFS, &vd->rb);
    if (ret < 0) {
        perror("Unable to allocate buffers");
        goto fatal;
    }
    /* map the buffers */
    for (i = 0; i < NB_BUFFER; i++) {
        memset(&vd->buf, 0, sizeof(struct v4l2_buffer));
        vd->buf.index = i;
        vd->buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        vd->buf.memory = V4L2_MEMORY_MMAP;
        ret = v4l2_ioctl(vd->fd, VIDIOC_QUERYBUF, &vd->buf);
        if (ret < 0) {
            perror("Unable to query buffer");
            goto fatal;
        }
        if (debug)
            printf("length: %u offset: %u\n", vd->buf.length,
                   vd->buf.m.offset);
        vd->mem[i] = v4l2_mmap(0 /* start anywhere */ ,
                               vd->buf.length, PROT_READ, MAP_SHARED, vd->fd,
                               vd->buf.m.offset);
        if (vd->mem[i] == MAP_FAILED) {
            perror("Unable to map buffer");
            goto fatal;
        }
        if (debug)
            printf("Buffer mapped at address %p.\n", vd->mem[i]);
    }
    /* Queue the buffers. */
    for (i = 0; i < NB_BUFFER; ++i) {
        memset(&vd->buf, 0, sizeof(struct v4l2_buffer));
        vd->buf.index = i;
        vd->buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        vd->buf.memory = V4L2_MEMORY_MMAP;
        ret = v4l2_ioctl(vd->fd, VIDIOC_QBUF, &vd->buf);
        if (ret < 0) {
            perror("Unable to queue buffer");
            goto fatal;;
        }
    }
    return 0;
    fatal:
    return -1;

}

static int video_enable(struct video_info *vd) {
    int type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    int ret;

    ret = v4l2_ioctl(vd->fd, VIDIOC_STREAMON, &type);
    if (ret < 0) {
        perror("Unable to start capture");
        return ret;
    }
    vd->is_streaming = 1;
    return 0;
}

static int video_disable(struct video_info *vd) {
    int type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    int ret;

    ret = v4l2_ioctl(vd->fd, VIDIOC_STREAMOFF, &type);
    if (ret < 0) {
        perror("Unable to stop capture");
        return ret;
    }
    vd->is_streaming = 0;
    return 0;
}


int uvcGrab(struct video_info *vd) {
#define HEADERFRAME1 0xaf
    int ret;

    if (!vd->is_streaming)
        if (video_enable(vd))
            goto err;
    memset(&vd->buf, 0, sizeof(struct v4l2_buffer));
    vd->buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    vd->buf.memory = V4L2_MEMORY_MMAP;
    ret = v4l2_ioctl(vd->fd, VIDIOC_DQBUF, &vd->buf);
    if (ret < 0) {
        perror("Unable to dequeue buffer");
        goto err;
    }

    switch (vd->format_in) {
        case V4L2_PIX_FMT_YUYV:
        case V4L2_PIX_FMT_UYVY:
            if (vd->buf.bytesused > vd->frame_size_in)
                memcpy(vd->frame_buffer, vd->mem[vd->buf.index],
                       (size_t) vd->frame_size_in);
            else
                memcpy(vd->frame_buffer, vd->mem[vd->buf.index],
                       (size_t) vd->buf.bytesused);
            break;
        default:
            goto err;
            break;
    }
    ret = v4l2_ioctl(vd->fd, VIDIOC_QBUF, &vd->buf);
    if (ret < 0) {
        perror("Unable to requeue buffer");
        goto err;
    }

    return 0;
    err:
    return -1;
}

int close_v4l2(struct video_info *vd) {
    if (vd->is_streaming) video_disable(vd);
    if (vd->tmp_buffer) free(vd->tmp_buffer);
    vd->tmp_buffer = NULL;
    free(vd->frame_buffer);
    vd->frame_buffer = NULL;
    free(vd->video_device);
    free(vd->status);
    free(vd->pict_name);
    vd->video_device = NULL;
    vd->status = NULL;
    vd->pict_name = NULL;
    return 0;
}

int enum_frame_intervals(int dev, __u32 pixfmt, __u32 width, __u32 height) {
    int ret;
    struct v4l2_frmivalenum fival;

    memset(&fival, 0, sizeof(fival));
    fival.index = 0;
    fival.pixel_format = pixfmt;
    fival.width = width;
    fival.height = height;
    printf("\tTime interval between frame: ");
    while ((ret = v4l2_ioctl(dev, VIDIOC_ENUM_FRAMEINTERVALS, &fival)) == 0) {
        if (fival.type == V4L2_FRMIVAL_TYPE_DISCRETE) {
            printf("%u/%u, ",
                   fival.discrete.numerator, fival.discrete.denominator);
        } else if (fival.type == V4L2_FRMIVAL_TYPE_CONTINUOUS) {
            printf("{min { %u/%u } .. max { %u/%u } }, ",
                   fival.stepwise.min.numerator, fival.stepwise.min.numerator,
                   fival.stepwise.max.denominator, fival.stepwise.max.denominator);
            break;
        } else if (fival.type == V4L2_FRMIVAL_TYPE_STEPWISE) {
            printf("{min { %u/%u } .. max { %u/%u } / "
                   "stepsize { %u/%u } }, ",
                   fival.stepwise.min.numerator, fival.stepwise.min.denominator,
                   fival.stepwise.max.numerator, fival.stepwise.max.denominator,
                   fival.stepwise.step.numerator, fival.stepwise.step.denominator);
            break;
        }
        fival.index++;
    }
    printf("\n");
    if (ret != 0 && errno != EINVAL) {
        perror("ERROR enumerating frame intervals");
        return errno;
    }

    return 0;
}

int enum_frame_sizes(int dev, __u32 pixfmt) {
    int ret;
    struct v4l2_frmsizeenum fsize;

    memset(&fsize, 0, sizeof(fsize));
    fsize.index = 0;
    fsize.pixel_format = pixfmt;
    while ((ret = v4l2_ioctl(dev, VIDIOC_ENUM_FRAMESIZES, &fsize)) == 0) {
        if (fsize.type == V4L2_FRMSIZE_TYPE_DISCRETE) {
            printf("{ discrete: width = %u, height = %u }\n",
                   fsize.discrete.width, fsize.discrete.height);
            ret = enum_frame_intervals(dev, pixfmt,
                                       fsize.discrete.width, fsize.discrete.height);
            if (ret != 0)
                printf("  Unable to enumerate frame sizes.\n");
        } else if (fsize.type == V4L2_FRMSIZE_TYPE_CONTINUOUS) {
            printf("{ continuous: min { width = %u, height = %u } .. "
                   "max { width = %u, height = %u } }\n",
                   fsize.stepwise.min_width, fsize.stepwise.min_height,
                   fsize.stepwise.max_width, fsize.stepwise.max_height);
            printf("  Refusing to enumerate frame intervals.\n");
            break;
        } else if (fsize.type == V4L2_FRMSIZE_TYPE_STEPWISE) {
            printf("{ stepwise: min { width = %u, height = %u } .. "
                   "max { width = %u, height = %u } / "
                   "stepsize { width = %u, height = %u } }\n",
                   fsize.stepwise.min_width, fsize.stepwise.min_height,
                   fsize.stepwise.max_width, fsize.stepwise.max_height,
                   fsize.stepwise.step_width, fsize.stepwise.step_height);
            printf("  Refusing to enumerate frame intervals.\n");
            break;
        }
        fsize.index++;
    }
    if (ret != 0 && errno != EINVAL) {
        perror("ERROR enumerating frame sizes");
        return errno;
    }

    return 0;
}

int enum_frame_formats(int dev, unsigned int *supported_formats, unsigned int max_formats) {
    int ret;
    struct v4l2_fmtdesc fmt;

    memset(&fmt, 0, sizeof(fmt));
    fmt.index = 0;
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    while ((ret = v4l2_ioctl(dev, VIDIOC_ENUM_FMT, &fmt)) == 0) {
        if (supported_formats == NULL) {
            printf("{ pixelformat = '%c%c%c%c', description = '%s' }\n",
                   fmt.pixelformat & 0xFF, (fmt.pixelformat >> 8) & 0xFF,
                   (fmt.pixelformat >> 16) & 0xFF, (fmt.pixelformat >> 24) & 0xFF,
                   fmt.description);
            ret = enum_frame_sizes(dev, fmt.pixelformat);
            if (ret != 0)
                printf("  Unable to enumerate frame sizes.\n");
        } else if (fmt.index < max_formats) {
            supported_formats[fmt.index] = fmt.pixelformat;
        }

        fmt.index++;
    }
    if (errno != EINVAL) {
        perror("ERROR enumerating frame formats");
        return errno;
    }

    return 0;
}
