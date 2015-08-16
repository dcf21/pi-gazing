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
#include "settings_webcam.h"

#define medianMapUseEveryNthStack     1
#define medianMapUseNImages         100

int main(int argc, char *argv[])
 {
  if (argc!=2)
   {
    sprintf(temp_err_string, "ERROR: Need to specify output filename for median map on commandline, e.g. 'makeMedianMap tmp'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  char line[FNAME_BUFFER];

  struct vdIn *videoIn;

  const char *videodevice=VIDEO_DEV;
  float fps = nearestMultiple(VIDEO_FPS,1);       // Requested frame rate
  int format = V4L2_PIX_FMT_YUYV;
  int grabmethod = 1;
  int queryformats = 0;
  char *stub = argv[1];

  char rawfname[FNAME_BUFFER], frOut[FNAME_BUFFER];
  sprintf(rawfname, "%s.rgb", stub);
  sprintf(frOut   , "%s.png", stub);

  videoIn = (struct vdIn *) calloc(1, sizeof(struct vdIn));

  if (queryformats)
   {
    check_videoIn(videoIn,(char *) videodevice);
    free(videoIn);
    exit(1);
   }

  if (init_videoIn(videoIn, (char *) videodevice, VIDEO_WIDTH, VIDEO_HEIGHT, fps, format, grabmethod, rawfname) < 0) exit(1);
  const int width = videoIn->width;
  const int height= videoIn->height;
  const int frameSize = width*height;

  initLut();

  int tstart = time(NULL);
  if (DEBUG) { sprintf(line, "Commencing makeMedianMap at %s.", FriendlyTimestring(tstart)); gnom_log(line); }

  unsigned char *tmpc = malloc(frameSize*1.5);
  if (!tmpc) { sprintf(temp_err_string, "ERROR: malloc fail in makeMedianMap."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }
  int *tmpi = malloc(frameSize*3*sizeof(int));
  if (!tmpi) { sprintf(temp_err_string, "ERROR: malloc fail in makeMedianMap."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  int           *medianWorkspace = calloc(1,frameSize*3*256*sizeof(int));
  unsigned char *medianMap       = calloc(1,3*frameSize);
  if ((!medianWorkspace)||(!medianMap)) { sprintf(temp_err_string, "ERROR: malloc fail in makeMedianMap."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  int f,i;

  const int totalRequiredStacks = medianMapUseEveryNthStack*medianMapUseNImages;
  for (f=0; f<totalRequiredStacks; f++)
   {
    const int nfr=12; // Stack 12 frames
    int j;
    memset(tmpi, 0, 3*frameSize*sizeof(int));

    // Make a stack of nfr frames
    for (j=0;j<nfr;j++)
     {
      if (uvcGrab(videoIn) < 0) { printf("Error grabbing\n"); break; }
      Pyuv422torgbstack(videoIn->framebuffer, tmpi, tmpi+frameSize, tmpi+frameSize*2, videoIn->width, videoIn->height, VIDEO_UPSIDE_DOWN);
     }

    if ((f % medianMapUseEveryNthStack) != 0) continue;

    // Add stacked image into median map
#pragma omp parallel for private(j)
    for (j=0; j<Nchannels*frameSize; j++)
     {
      int d;
      int pixelVal = CLIP256( tmpi[j]/nfr );
      medianWorkspace[j*256 + pixelVal]++;
     }
   }

  // Calculate median map
  medianCalculate(width, height, Nchannels, 0, 1, medianWorkspace, medianMap);
  dumpFrame(width, height, Nchannels, medianMap, rawfname);

  // Make a PNG version for diagnostic use
  image_ptr OutputImage;
  image_alloc(&OutputImage, width, height);
  OutputImage.data_w = 1;
  if (Nchannels>=3)
   {
    for (i=0; i<frameSize; i++) OutputImage.data_red[i] = medianMap[i              ];
    for (i=0; i<frameSize; i++) OutputImage.data_grn[i] = medianMap[i + frameSize  ];
    for (i=0; i<frameSize; i++) OutputImage.data_blu[i] = medianMap[i + frameSize*2];
   } else {
    for (i=0; i<frameSize; i++) OutputImage.data_red[i] = medianMap[i];
    for (i=0; i<frameSize; i++) OutputImage.data_grn[i] = medianMap[i];
    for (i=0; i<frameSize; i++) OutputImage.data_blu[i] = medianMap[i];
   }
  image_put(frOut, OutputImage, ALLDATAMONO);

  // Clean up
  free(medianWorkspace); free(medianMap);

  int tstop = time(NULL);
  if (DEBUG) { sprintf(line, "Finishing making median map at %s.", FriendlyTimestring(tstop)); gnom_log(line); }

  return 0;
 }
