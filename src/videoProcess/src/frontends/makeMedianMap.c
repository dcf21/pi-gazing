// makeMedianMap.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "utils/asciidouble.h"
#include "vidtools/v4l2uvc.h"
#include "utils/tools.h"
#include "vidtools/color.h"
#include "utils/error.h"

#include "settings.h"

int main(int argc, char *argv[])
 {
  if (argc!=2)
   {
    sprintf(temp_err_string, "ERROR: Need to specify output filename for median map on commandline, e.g. 'makeMedianMap tmp.raw'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  char line[FNAME_BUFFER];

  struct vdIn *videoIn;

  const char *videodevice=VIDEO_DEV;
  float fps = nearestMultiple(VIDEO_FPS,1);       // Requested frame rate
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
  const int width = videoIn->width;
  const int height= videoIn->height;
  const int frameSize = width*height;

  initLut();

  int tstart = time(NULL);
  if (DEBUG) { sprintf(line, "Commencing makeMedianMap at %s.", FriendlyTimestring(tstart)); gnom_log(line); }

  unsigned char *tmpc = malloc(frameSize*1.5);
  if (!tmpc) { sprintf(temp_err_string, "ERROR: malloc fail in makeMedianMap."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }
  int *tmpi = malloc(frameSize*1.5*sizeof(int));
  if (!tmpi) { sprintf(temp_err_string, "ERROR: malloc fail in makeMedianMap."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  unsigned char *medianWorkspace = calloc(1,3*frameSize*256);
  unsigned char *medianMap       = calloc(1,3*frameSize);
  if ((!medianWorkspace)||(!medianMap)) { sprintf(temp_err_string, "ERROR: malloc fail in makeMedianMap."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  int f;
  for (f=0; f<256; f++)
   {
    const int nfr=25; // Stack 25 frames
    int i,j;
    for (i=0; i<frameSize; i++) tmpi[i]=0;

    for (j=0;j<nfr;j++)
     {
      if (uvcGrab(videoIn) < 0) { printf("Error grabbing\n"); break; }
      Pyuv422torgbstack(videoIn->framebuffer, tmpi, tmpi+frameSize, tmpi+frameSize*2, videoIn->width, videoIn->height, VIDEO_UPSIDE_DOWN);
     }

#pragma omp parallel for private(i,j)
    for (j=0; j<3; j++)
     for (i=0; i<frameSize; i++)
      {
       int pixelVal = tmpi[i+j*frameSize]/nfr;
       if (pixelVal<0  ) pixelVal=0;
       if (pixelVal>255) pixelVal=255;
       medianWorkspace[j*frameSize*256 + i + pixelVal*frameSize]++;
      }
   }

  medianCalculate(width, height, medianWorkspace, medianMap);
  dumpFrame(width, height, medianMap, avifilename);
  free(medianWorkspace); free(medianMap);

  int tstop = time(NULL);
  if (DEBUG) { sprintf(line, "Finishing making median map at %s.", FriendlyTimestring(tstop)); gnom_log(line); }

  return 0;
 }
