// tools.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef TOOLS_H
#define TOOLS_H 1

#include "vidtools/v4l2uvc.h"

#define CLIP256(X) ( d=X , ((d<0)?0: ((d>255)?255:d) ))

void  frameInvert      (unsigned char *buffer, int len);
void *videoRecord      (struct vdIn *videoIn, double seconds);
void  snapshot         (struct vdIn *videoIn, int nfr, int zero, double expComp, char *fname, unsigned char *medianRaw);
void  medianCalculate  (int width, int height, unsigned char *medianWorkspace, unsigned char *medianMap);
int   dumpFrame        (int width, int height, unsigned char *buffer, char *fName);
int   dumpFrameRGB     (int width, int height, unsigned char *bufferR, unsigned char *bufferG, unsigned char *bufferB, char *fName);
int   dumpFrameFromInts(int width, int height, int *buffer, int nfr, int gain, char *fName);
int   dumpFrameFromISub(int width, int height, int *buffer, int nfr, int gain, unsigned char *buffer2, char *fName);
int   dumpVideo        (int nfr1, int nfr2, int width, int height, unsigned char *buffer1, unsigned char *buffer2, unsigned char *buffer3, char *fName);

#endif

