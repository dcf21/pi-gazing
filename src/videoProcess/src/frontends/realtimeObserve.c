// observe.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include "utils/asciidouble.h"
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"
#include "utils/JulianDate.h"
#include "analyse/observe.h"

#include "settings.h"

int utcoffset;

int fetchFrame(void *videoHandle, unsigned char *tmpc, double *utc)
 {
  struct vdIn *videoIn = videoHandle;
  int status = uvcGrab(videoIn);
  if (status) return status;
  Pyuv422toMono(videoIn->framebuffer, tmpc, videoIn->width, videoIn->height);
  if (VIDEO_UPSIDE_DOWN) frameInvert(tmpc, videoIn->width*videoIn->height);
  *utc = time(NULL) + utcoffset;
  return 0;
 }

int main(int argc, char *argv[])
 {
  if (argc!=3)
   {
    sprintf(temp_err_string, "ERROR: Need to specify UTC clock offset and observe run stop time on commandline, e.g. 'observe 1234 567'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

            utcoffset  = (int)GetFloat(argv[1],NULL);
  const int tstart     = time(NULL) + utcoffset;
  const int tstop      = (int)GetFloat(argv[2],NULL);

  struct vdIn *videoIn;

  const char *videodevice=VIDEO_DEV;
  const float fps = VIDEO_FPS;       // Requested frame rate
  const int format = V4L2_PIX_FMT_YUYV;
  const int grabmethod = 1;
  const int queryformats = 0;
  char *avifilename = "/tmp/foo";

  videoIn = (struct vdIn *) calloc(1, sizeof(struct vdIn));

  if (queryformats)
   {
    check_videoIn(videoIn,(char *) videodevice);
    free(videoIn);
    exit(1);
   }

  // Fetch the dimensions of the video stream as returned by V4L (which may differ from what we requested)
  if (init_videoIn(videoIn, (char *) videodevice, VIDEO_WIDTH, VIDEO_HEIGHT, fps, format, grabmethod, avifilename) < 0) exit(1);
  const int width = videoIn->width;
  const int height= videoIn->height;

  initLut();

  observe((void *)videoIn, utcoffset, tstart, tstop, width, height, "live", &fetchFrame);

  return 0;
 }
