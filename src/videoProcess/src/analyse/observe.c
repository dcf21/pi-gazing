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
#include "utils/tools.h"
#include "utils/error.h"
#include "utils/JulianDate.h"

#include "settings.h"

// When testTrigger detects a meteor, this string is set to a filename stub with time stamp of the time when the camera triggered
static char triggerstub[4096];


// Generate a filename stub with a timestamp. Warning: not thread safe. Returns a pointer to static string
char *fNameGenerate(char *tag)
 {
  static char path[4096], output[4096];
  const int t = time(NULL);
  const double JD = t / 86400.0 + 2440587.5;
  int year,month,day,hour,min,status; double sec;
  InvJulianDay(JD-0.5,&year,&month,&day,&hour,&min,&sec,&status,output); // Subtract 0.5 from Julian Day as we want days to start at noon, not midnight
  sprintf(path,"%s/%04d%02d%02d", OUTPUT_PATH, year, month, day);
  sprintf(output, "mkdir -p %s", path); status=system(output);
  InvJulianDay(JD,&year,&month,&day,&hour,&min,&sec,&status,output);
  sprintf(output,"%s/%04d%02d%02d%02d%02d%02d_%s", path, year, month, day, hour, min, (int)sec, tag);
  return output;
 }

// Used by testTrigger. When blocks idOld and idNew are determined to be connected, their pixels counts are added together.
inline void triggerBlocksMerge(int *triggerBlock, int *triggerMap, int len, int idOld, int idNew)
 {
  int i;
  if (idOld==idNew) return;
  for (i=0;i<len;i++) if (triggerMap[i]==idOld) triggerMap[i]=idNew;
  triggerBlock[idNew]+=triggerBlock[idOld];
  return;
 }

// Test stacked images B and A, to see if pixels have brightened in B versus A. Image arrays contain the sum of <coAddedFrames> frames.
int testTrigger(const int width, const int height, const int *imageB, const int *imageA, const int coAddedFrames)
 {
  int x,y,d;
  int output=0;

  const int marginL=12; // Ignore pixels within this distance of the edge
  const int marginR=19;
  const int marginT= 8;
  const int marginB=19;

  const int Npixels=30; // To trigger this number of pixels connected together must have brightened
  const int radius=8; // Pixel must be brighter than test pixels this distance away
  const int threshold=13*coAddedFrames; // Pixel must have brightened by at least 8.
  const int frameSize=width*height;
  int *triggerMap   = calloc(1,frameSize*sizeof(int)); // triggerMap is a 2D array of ints used to mark out pixels which have brightened suspiciously.
  int *triggerBlock = calloc(1,frameSize*sizeof(int)); // triggerBlock is a count of how many pixels are in each numbered connected block
  unsigned char *triggerR = calloc(1,frameSize);
  unsigned char *triggerG = calloc(1,frameSize); // These arrays are used to produce diagnostic images when the camera triggers
  unsigned char *triggerB = calloc(1,frameSize);
  int  blockNum     = 1;

  for (y=marginB; y<height-marginT; y++)
   for (x=marginR;x<width-marginL; x++)
    {
     const int o=x+y*width;
     triggerR[o] = CLIP256( 128+(imageB[o]-imageA[o])*256/threshold ); // RED channel - difference between images B and A
     triggerG[o] = CLIP256( imageB[o] / coAddedFrames ); // GRN channel - a copy of image B
     if (imageB[o]-imageA[o]>threshold) // Search for pixels which have brightened by more than threshold since past image
      {
       int i,j,c=0; // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels. This pixel must be brighter than 6/9 of these pixels were
       for (i=-1;i<=1;i++) for (j=-1;j<=1;j++) if (imageB[o]-imageA[o+(j+i*width)*radius]>threshold) c++;
       if (c>7)
        {
         int i,j,c=0; // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels. This pixel must be brighter than 6/9 of these pixels were
         for (i=-1;i<=1;i++) for (j=-1;j<=1;j++) if (imageB[o]-imageB[o+(j+i*width)*radius]>threshold) c++;
         if (c>6)
          {
           // Put triggering pixel on map. Wait till be have <Npixels> connected pixels.
           triggerB[o] = 128;
           int blockId=0;
           if (triggerMap[o-1      ]) { if (!blockId) { blockId=triggerMap[o-1      ]; } else { triggerBlocksMerge(triggerBlock, triggerMap+(y-1)*width, width*2, triggerMap[o-1      ], blockId); } }
           if (triggerMap[o+1-width]) { if (!blockId) { blockId=triggerMap[o+1-width]; } else { triggerBlocksMerge(triggerBlock, triggerMap+(y-1)*width, width*2, triggerMap[o+1-width], blockId); } }
           if (triggerMap[o-width  ]) { if (!blockId) { blockId=triggerMap[o-width  ]; } else { triggerBlocksMerge(triggerBlock, triggerMap+(y-1)*width, width*2, triggerMap[o-width  ], blockId); } }
           if (triggerMap[o-1-width]) { if (!blockId) { blockId=triggerMap[o-1-width]; } else { triggerBlocksMerge(triggerBlock, triggerMap+(y-1)*width, width*2, triggerMap[o-1-width], blockId); } }
           if (blockId==0           ) blockId=blockNum++;

           triggerBlock[blockId]++;
           triggerMap[o] = blockId;
           if (triggerBlock[blockId]>Npixels)
            {
             triggerB[o]=255;
             if (DEBUG && !output) { sprintf(temp_err_string, "Camera has triggered at (%d,%d).",width-x,height-y); gnom_log(temp_err_string); }
             output=1; // We have triggered!
            }
          }
        }
      }
    }

  // If we have triggered, produce a diagnostic map of why. NB: This step is also necessary to set <triggerstub>.
  if (output)
   {
    strcpy(triggerstub, fNameGenerate("trigger"));
    char fname[4096];
    sprintf(fname, "%s%s",triggerstub,"_MAP.rgb");
    dumpFrameRGB(width, height, triggerR, triggerG, triggerB, fname);
   }

  free(triggerMap); free(triggerBlock); free(triggerR); free(triggerG); free(triggerB);
  return output;
 }

// Read enough video (1 second) to create the stacks used to test for triggers
int readShortBuffer(void *videoHandle, int nfr, int width, int height, unsigned char *buffer, int *stack1, int *stack2, unsigned char *maxMap, unsigned char *medianWorkspace, int (*fetchFrame)(void *,unsigned char *))
 {
  const int frameSize = width*height;
  int i,j;
  for (i=0; i<frameSize; i++) stack1[i]=0;
  for (i=0; i<frameSize; i++) maxMap[i]=0;

  for (j=0;j<nfr;j++)
   {
    unsigned char *tmpc = buffer+j*frameSize;
    if ((*fetchFrame)(videoHandle,tmpc) < 0) { if (DEBUG) gnom_log("Error grabbing"); return 1; }
    for (i=0; i<frameSize; i++) stack1[i]+=tmpc[i]; // Stack1 is wiped prior to each call to this function
    if (stack2) for (i=0; i<frameSize; i++) stack2[i]+=tmpc[i]; // Stack2 can stack output of many calls to this function
    for (i=0; i<frameSize; i++) if (maxMap[i]<tmpc[i]) maxMap[i]=tmpc[i];
   }

  // Add the pixel values in this stack into the histogram in medianWorkspace
  for (i=0; i<frameSize; i++)
   {
    int d, pixelVal = CLIP256(stack1[i]/nfr);
    medianWorkspace[i + pixelVal*frameSize]++;
   }
  return 0;
 }

int observe(void *videoHandle, const int utcoffset, const int tstart, const int tstop, const int width, const int height, int (*fetchFrame)(void *,unsigned char *))
 {
  char line[4096];

  if (DEBUG) { sprintf(line, "Starting observing run at %s.", StrStrip(FriendlyTimestring(tstart),temp_err_string)); gnom_log(line); }
  if (DEBUG) { sprintf(line, "Observing run will end at %s.", StrStrip(FriendlyTimestring(tstop ),temp_err_string)); gnom_log(line); }

  const float fps = VIDEO_FPS;       // Requested frame rate

  const int frameSize = width * height;

  // Trigger buffers. These are used to store 1 second of video for comparison with the next
  const double secondsTriggerBuff = 0.5;
  const int      nfrt    = fps   * secondsTriggerBuff;
  const int      btlen   = nfrt*frameSize;
  unsigned char *bufferA = malloc(btlen); // Two buffers, A and B, each hold alternate seconds of video data which we compare to see if anything has happened
  unsigned char *bufferB = malloc(btlen);
  int           *stackA  = malloc(frameSize*sizeof(int)); // A stacked version of the video data in buffers A and B
  int           *stackB  = malloc(frameSize*sizeof(int));
  unsigned char *maxA    = malloc(frameSize); // Maximum recorded pixel intensity
  unsigned char *maxB    = malloc(frameSize);

  // Timelapse buffers
  int          frameNextTargetTime  = floor(time(NULL)/60+1)*60; // Store exposures once a minute, on the minute
  const double secondsTimelapseBuff = 15;
  const int    nfrtl                = fps * secondsTimelapseBuff;
  int         *stackT               = malloc(frameSize*sizeof(int));

  // Long buffer. Used to store a video after the camera has triggered
  const double secondsLongBuff = 9;
  const int nfrl         = fps * secondsLongBuff;
  const int bllen        = nfrl*frameSize;
  unsigned char *bufferL = malloc(bllen); // A long buffer, used to record 10 seconds of video after we trigger
  int           *stackL  = malloc(frameSize*sizeof(int));
  unsigned char *maxL    = malloc(frameSize);

  // Median maps are used for background subtraction. Maps A and B are used alternately and contain the median value of each pixel.
  unsigned char *medianMapA      = calloc(1,frameSize); // The median value of each pixel, sampled over 255 stacked images
  unsigned char *medianMapB      = calloc(1,frameSize);
  unsigned char *medianWorkspace = calloc(1,frameSize*256); // Workspace which counts the number of times any given pixel has a particular value over 255 images

  if ((!bufferA)||(!bufferB)||(!bufferL) || (!stackA)||(!stackB)||(!stackT)||(!stackL) || (!maxA)||(!maxB)||(!maxL) ||  (!medianMapA)||(!medianMapB)||(!medianWorkspace)) { sprintf(temp_err_string, "ERROR: malloc fail in observe."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  int bufferNum      = 0; // Flag for whether we're using trigger buffer A or B
  int medianNum      = 0; // Flag for whether we're using median map A or B
  int medianCount    = 0; // Count frames from 0 to 255 until we're ready to make a new median map
  int recording      =-1; // Count how many seconds we've been recording for. A value of -1 means we're not recording
  int timelapseCount =-1; // Count used to add up <secondsTimelapseBuff> seconds of data when stacking timelapse frames
  int framesSinceLastTrigger = -260; // Let the camera run for 260 seconds before triggering, as it takes this long to make first median map

  while (1)
   {
    int t = time(NULL) - utcoffset;
    if (t>=tstop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!

    // Work out where we're going to read next second of video to. Either bufferA / bufferB, or the long buffer if we're recording
    unsigned char *buffer = bufferNum?bufferB:bufferA;
    if (recording>-1) buffer = bufferL + frameSize*nfrt*recording;

    // Read the next second of video
    int status = readShortBuffer(videoHandle, nfrt, width, height, buffer, bufferNum?stackB:stackA, (timelapseCount>=0)?stackT:NULL, bufferNum?maxB:maxA, medianWorkspace, fetchFrame);
    if (status) break; // We've run out of video
    framesSinceLastTrigger++;
    if (DEBUG) if (framesSinceLastTrigger==3) { sprintf(line, "Camera is now able to trigger."); gnom_log(line); }

    // If we've stacked 255 frames since we last made a median map, make a new median map
    medianCount++;
    if (medianCount==255) { medianNum=!medianNum; medianCalculate(width, height, medianWorkspace, medianNum?medianMapB:medianMapA); medianCount=0; }

    // If we're recording, test whether we're ready to stop recording
    if (recording>-1)
     {
      int i;
      unsigned char *maxbuf = bufferNum?maxB:maxA;
      int *stackbuf = bufferNum?stackB:stackA;
      recording++;
      for (i=0; i<frameSize; i++) if (maxbuf[i]>maxL[i]) maxL[i]=maxbuf[i];
      for (i=0; i<frameSize; i++) stackL[i]+=stackbuf[i];
      if (recording>=nfrl/nfrt)
       {
        char fname[4096];
        sprintf(fname, "%s%s",triggerstub,"3_MAX.img");
        dumpFrame(width, height, maxL, fname);
        sprintf(fname, "%s%s",triggerstub,"3_BS0.img");
        dumpFrameFromInts(width, height, stackL, nfrt+nfrl, 1, fname);
        sprintf(fname, "%s%s",triggerstub,"3_BS1.img");
        dumpFrameFromISub(width, height, stackL, nfrt+nfrl, STACK_GAIN, medianNum?medianMapB:medianMapA, fname);
        sprintf(fname, "%s%s",triggerstub,".vid");
        dumpVideo(nfrt, nfrl, width, height, bufferNum?bufferA:bufferB, bufferNum?bufferB:bufferA, bufferL, fname);
        recording=-1; framesSinceLastTrigger=0;
     } }

    // Once a minute, dump create a stacked exposure lasting for <secondsTimelapseBuff> seconds
    if (timelapseCount>=0)
      { timelapseCount++; }
    else if (time(NULL)>frameNextTargetTime)
      {
       int i; for (i=0; i<frameSize; i++) stackT[i]=0;
       timelapseCount=0;
      }

    if (timelapseCount>=nfrtl/nfrt)
     {
      char fstub[4096], fname[4096]; strcpy(fstub, fNameGenerate("frame_"));
      sprintf(fname, "%s%s",fstub,"BS0.img");
      dumpFrameFromInts(width, height, stackT, nfrtl, 1, fname);
      sprintf(fname, "%s%s",fstub,"BS1.img");
      dumpFrameFromISub(width, height, stackT, nfrtl, STACK_GAIN, medianNum?medianMapB:medianMapA, fname);
      frameNextTargetTime+=60;
      timelapseCount=-1;
     }

    // If we're not recording, and have not stopped recording within past 2 seconds, test whether motion sensor has triggered
    if ( (recording<0) && (framesSinceLastTrigger>2) )
     {
      if (testTrigger(  width , height , bufferNum?stackB:stackA , bufferNum?stackA:stackB , nfrt  ))
       {
        char fname[4096];
        // if (DEBUG) { sprintf(line, "Camera has triggered."); gnom_log(line); }
        sprintf(fname, "%s%s",triggerstub,"2_BS0.img");
        dumpFrameFromInts(width, height, bufferNum?stackB:stackA, nfrt, 1, fname);
        sprintf(fname, "%s%s",triggerstub,"2_BS1.img");
        dumpFrameFromISub(width, height, bufferNum?stackB:stackA, nfrt, STACK_GAIN, medianNum?medianMapB:medianMapA, fname);
        sprintf(fname, "%s%s",triggerstub,"2_MAX.img");
        dumpFrame        (width, height, bufferNum?maxB:maxA, fname);

        sprintf(fname, "%s%s",triggerstub,"1_BS0.img");
        dumpFrameFromInts(width, height, bufferNum?stackA:stackB, nfrt, 1, fname);
        sprintf(fname, "%s%s",triggerstub,"1_BS1.img");
        dumpFrameFromISub(width, height, bufferNum?stackA:stackB, nfrt, STACK_GAIN, medianNum?medianMapB:medianMapA, fname);
        sprintf(fname, "%s%s",triggerstub,"1_MAX.img");
        dumpFrame        (width, height, bufferNum?maxA:maxB, fname);

        memcpy(maxL  , bufferNum?maxB:maxA    , frameSize);
        memcpy(stackL, bufferNum?stackB:stackA, frameSize*sizeof(int));
        recording=0;
       }
     }

    // If we're not recording, flip buffer numbers. If we are recording, don't do this; keep buffer number pointing at buffer with first second of video
    if (recording<0) bufferNum=!bufferNum;
   }

  free(bufferA); free(bufferB); free(bufferL); free(stackA); free(stackB); free(medianMapA); free(medianMapB); free(medianWorkspace);

  return 0;
 }
