// vidRec.c
// $Id: vidRec.c 1180 2015-02-06 23:01:45Z pyxplot $

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "v4l2uvc.h"
#include "tools.h"
#include "color.h"
#include "error.h"

#include "settings.h"

int main(int argc, char *argv[])
 {
  if (argc!=2)
   {
    sprintf(temp_err_string, "ERROR: Need to specify output filename for raw video dump on commandline, e.g. 'vidRec foo.raw'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  struct vdIn *videoIn;

  const char *videodevice=VIDEO_DEV;
  float fps = VIDEO_FPS;       // Requested frame rate
  int format = V4L2_PIX_FMT_YUYV;
  int grabmethod = 1;
  int queryformats = 0;
  char *avifilename = argv[1];

  videoIn = (struct vdIn *) calloc(1, sizeof(struct vdIn));

  if (queryformats)
   {
    check_videoIn(videoIn,(char *) videodevice);
    free(videoIn);
    exit(1);
   }

  if (init_videoIn(videoIn, (char *) videodevice, VIDEO_WIDTH, VIDEO_HEIGHT, fps, format, grabmethod, avifilename) < 0) exit(1);

  initLut();

  void *vidRaw = videoRecord(videoIn,4);

  FILE *outfile;
  if ((outfile = fopen(avifilename,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW video file %s.\n", avifilename); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  fwrite(vidRaw,1,*(int *)vidRaw,outfile);
  fclose(outfile);
  free(vidRaw);

  return 0;
 }
