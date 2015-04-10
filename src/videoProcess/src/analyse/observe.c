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
#include "vidtools/color.h"

#include "settings.h"

#define medianMapUseEveryNthStack              8
#define framesSinceLastTrigger_INITIAL      -260*medianMapUseEveryNthStack
#define framesSinceLastTrigger_REWIND         -2
#define framesSinceLastTrigger_ALLOWTRIGGER    3

#define YUV420  3/2 /* Each pixel is 1.5 bytes in YUV420 stream */

// When testTrigger detects a meteor, this string is set to a filename stub with time stamp of the time when the camera triggered
static char triggerstub[FNAME_BUFFER];


// Generate a filename stub with a timestamp. Warning: not thread safe. Returns a pointer to static string
char *fNameGenerate(int utc, char *tag, const char *dirname, const char *label)
 {
  static char path[FNAME_BUFFER], output[FNAME_BUFFER];
  const double JD = utc / 86400.0 + 2440587.5;
  int year,month,day,hour,min,status; double sec;
  InvJulianDay(JD-0.5,&year,&month,&day,&hour,&min,&sec,&status,output); // Subtract 0.5 from Julian Day as we want days to start at noon, not midnight
  sprintf(path,"%s/%s_%s/%04d%02d%02d", OUTPUT_PATH, dirname, label, year, month, day);
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
int testTrigger(const double utc, const int width, const int height, const int *imageB, const int *imageA, const int coAddedFrames, const char *label)
 {
  int x,y,d;
  int output=0;

  const int marginL=12; // Ignore pixels within this distance of the edge
  const int marginR=19;
  const int marginT= 8;
  const int marginB=19;

  const int Npixels=30; // To trigger this number of pixels connected together must have brightened
  const int radius=8; // Pixel must be brighter than test pixels this distance away
  const int threshold=13*coAddedFrames; // Pixel must have brightened by at least this amount.
  const int frameSize=width*height;
  int *triggerMap   = calloc(1,frameSize*sizeof(int)); // triggerMap is a 2D array of ints used to mark out pixels which have brightened suspiciously.
  int *triggerBlock = calloc(1,frameSize*sizeof(int)); // triggerBlock is a count of how many pixels are in each numbered connected block
  unsigned char *triggerRGB = calloc(1,frameSize*3);
  unsigned char *triggerR = triggerRGB;
  unsigned char *triggerG = triggerRGB + frameSize*1; // These arrays are used to produce diagnostic images when the camera triggers
  unsigned char *triggerB = triggerRGB + frameSize*2;
  int  blockNum     = 1;

  for (y=marginT; y<height-marginB; y++)
   for (x=marginL;x<width-marginR; x++)
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
             if (DEBUG && !output)
              {
               int year,month,day,hour,min,status; double sec;
               double JD = (utc/86400.0) + 2440587.5;
               InvJulianDay(JD, &year, &month, &day, &hour, &min, &sec, &status, temp_err_string);
               sprintf(temp_err_string, "Camera has triggered at (%04d/%02d/%02d %02d:%02d:%02d -- x=%d,y=%d).",year,month,day,hour,min,(int)sec,width-x,height-y); gnom_log(temp_err_string);
              }
             output=1; // We have triggered!
            }
          }
        }
      }
    }

  // If we have triggered, produce a diagnostic map of why. NB: This step is also necessary to set <triggerstub>.
  if (output)
   {
    strcpy(triggerstub, fNameGenerate(utc,"trigger","triggers_raw",label));
    char fname[FNAME_BUFFER];
    sprintf(fname, "%s%s",triggerstub,"_MAP.rgb");
    dumpFrameRGB(width, height, triggerRGB, fname);
   }

  free(triggerMap); free(triggerBlock); free(triggerRGB);
  return output;
 }

// Read enough video (1 second) to create the stacks used to test for triggers
int readShortBuffer(void *videoHandle, int nfr, int width, int height, unsigned char *buffer, int *stack1, int *stack2, unsigned char *maxMap, unsigned char *medianWorkspace, double *utc, int (*fetchFrame)(void *,unsigned char *,double *))
 {
  const int frameSize = width*height;
  int i,j;
  for (i=0; i<frameSize*3; i++) stack1[i]=0;
  for (i=0; i<frameSize*3; i++) maxMap[i]=0;

  unsigned char *tmprgb = malloc(3*frameSize);

  for (j=0;j<nfr;j++)
   {
    unsigned char *tmpc = buffer+j*frameSize*YUV420;
    if ((*fetchFrame)(videoHandle,tmpc,utc) != 0) { if (DEBUG) gnom_log("Error grabbing"); return 1; }
    Pyuv420torgb(tmpc,tmpc+frameSize,tmpc+frameSize*5/4,tmprgb,tmprgb+frameSize,tmprgb+frameSize*2,width,height);
#pragma omp parallel for private(i)
    for (i=0; i<frameSize*3; i++) stack1[i]+=tmprgb[i]; // Stack1 is wiped prior to each call to this function
    if (stack2)
     {
#pragma omp parallel for private(i)
      for (i=0; i<frameSize*3; i++) stack2[i]+=tmprgb[i]; // Stack2 can stack output of many calls to this function
     }
#pragma omp parallel for private(i)
    for (i=0; i<frameSize*3; i++) if (maxMap[i]<tmprgb[i]) maxMap[i]=tmprgb[i];
   }

  // Add the pixel values in this stack into the histogram in medianWorkspace
  if (medianWorkspace)
   for (j=0; j<3; j++)
    for (i=0; i<frameSize*3; i++)
     {
      int d, pixelVal = CLIP256(stack1[i]/nfr);
      medianWorkspace[j*frameSize*256 + i + pixelVal*frameSize]++;
     }
  free(tmprgb);
  return 0;
 }

int observe(void *videoHandle, const int utcoffset, const int tstart, const int tstop, const int width, const int height, const char *label, int (*fetchFrame)(void *,unsigned char *,double *), int (*rewindVideo)(void *, double *))
 {
  char line[FNAME_BUFFER],line2[FNAME_BUFFER],line3[FNAME_BUFFER];
  double utc;

  if (DEBUG) { sprintf(line, "Starting observing run at %s; observing run will end at %s.", StrStrip(FriendlyTimestring(tstart),line2),StrStrip(FriendlyTimestring(tstop),line3)); gnom_log(line); }

  const float fps = VIDEO_FPS;       // Requested frame rate

  const int frameSize = width * height;

  // Trigger buffers. These are used to store 1 second of video for comparison with the next
  const double secondsTriggerBuff = TRIGGER_COMPARELEN;
  const int      nfrt    = fps   * secondsTriggerBuff;
  const int      btlen   = nfrt*frameSize*YUV420;
  unsigned char *bufferA = malloc(btlen); // Two buffers, A and B, each hold alternate seconds of video data which we compare to see if anything has happened
  unsigned char *bufferB = malloc(btlen);
  int           *stackA  = malloc(frameSize*sizeof(int)*3); // A stacked version of the video data in buffers A and B
  int           *stackB  = malloc(frameSize*sizeof(int)*3);
  unsigned char *maxA    = malloc(frameSize*3); // Maximum recorded pixel intensity
  unsigned char *maxB    = malloc(frameSize*3);

  // Timelapse buffers
  double       frameNextTargetTime  = 1e40; // Store exposures once a minute, on the minute. This is UTC of next frame, but we don't start until we've done a run-in period
  const double secondsTimelapseBuff = TIMELAPSE_EXPOSURE;
  const int    nfrtl                = nearestMultiple(fps * secondsTimelapseBuff, nfrt); // Number of frames stacked in all buffers must be a multiple of shortest buffer length
  int         *stackT               = malloc(frameSize*sizeof(int)*3);

  // Long buffer. Used to store a video after the camera has triggered
  const double secondsLongBuff = TRIGGER_RECORDLEN;
  const int nfrl         = nearestMultiple(fps * secondsLongBuff, nfrt); // Number of frames stacked in all buffers must be a multiple of shortest buffer length
  const int bllen        = nfrl*frameSize*YUV420;
  unsigned char *bufferL = malloc(bllen); // A long buffer, used to record 10 seconds of video after we trigger
  int           *stackL  = malloc(frameSize*sizeof(int)*3);
  unsigned char *maxL    = malloc(frameSize*3);

  // Median maps are used for background subtraction. Maps A and B are used alternately and contain the median value of each pixel.
  unsigned char *medianMapA      = calloc(1,frameSize*3); // The median value of each pixel, sampled over 255 stacked images
  unsigned char *medianMapB      = calloc(1,frameSize*3);
  unsigned char *medianWorkspace = calloc(1,frameSize*3*256); // Workspace which counts the number of times any given pixel has a particular value over 255 images

  if ((!bufferA)||(!bufferB)||(!bufferL) || (!stackA)||(!stackB)||(!stackT)||(!stackL) || (!maxA)||(!maxB)||(!maxL) ||  (!medianMapA)||(!medianMapB)||(!medianWorkspace)) { sprintf(temp_err_string, "ERROR: malloc fail in observe."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  int bufferNum      = 0; // Flag for whether we're using trigger buffer A or B
  int medianNum      = 0; // Flag for whether we're using median map A or B
  int medianCount    = 0; // Count frames from 0 to 255 until we're ready to make a new median map
  int recording      =-1; // Count how many seconds we've been recording for. A value of -1 means we're not recording
  int timelapseCount =-1; // Count used to add up <secondsTimelapseBuff> seconds of data when stacking timelapse frames
  int framesSinceLastTrigger = framesSinceLastTrigger_INITIAL; // Let the camera run for a period before triggering, as it takes this long to make first median map

  // Trigger throttling
  const int triggerThrottleCycles = (TRIGGER_THROTTLE_PERIOD * 60. / secondsTriggerBuff);
  int       triggerThrottleTimer  = 0;
  int       triggerThrottleCounter= 0;

  while (1)
   {
    int t = time(NULL) + utcoffset;
    if (t>=tstop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!

    // Once we've done initial run-in period, rewind the tape to the beginning if we can
    if (framesSinceLastTrigger==framesSinceLastTrigger_REWIND)
     {
      (*rewindVideo)(videoHandle,&utc);
      frameNextTargetTime = ceil(utc/60)*60; // Start making timelapse video
     }

    // Work out where we're going to read next second of video to. Either bufferA / bufferB, or the long buffer if we're recording
    unsigned char *buffer = bufferNum?bufferB:bufferA;
    if (recording>-1) buffer = bufferL + frameSize*YUV420*nfrt*recording;

    // Read the next second of video
    int status = readShortBuffer(videoHandle, nfrt, width, height, buffer, bufferNum?stackB:stackA, (timelapseCount>=0)?stackT:NULL, bufferNum?maxB:maxA, ((medianCount%medianMapUseEveryNthStack)==0)?medianWorkspace:NULL, &utc, fetchFrame);
    if (status) break; // We've run out of video
    framesSinceLastTrigger++;
    if (DEBUG) if (framesSinceLastTrigger==framesSinceLastTrigger_ALLOWTRIGGER) { sprintf(line, "Camera is now able to trigger."); gnom_log(line); }

    // If we've stacked 255 frames since we last made a median map, make a new median map
    medianCount++;
    if (medianCount==255*medianMapUseEveryNthStack) { medianNum=!medianNum; medianCalculate(width, height, medianWorkspace, medianNum?medianMapB:medianMapA); medianCount=0; }

    // If we're recording, test whether we're ready to stop recording
    if (recording>-1)
     {
      int i;
      unsigned char *maxbuf = bufferNum?maxB:maxA;
      int *stackbuf = bufferNum?stackB:stackA;
      recording++;
#pragma omp parallel for private(i)
      for (i=0; i<frameSize*3; i++) if (maxbuf[i]>maxL[i]) maxL[i]=maxbuf[i];
#pragma omp parallel for private(i)
      for (i=0; i<frameSize*3; i++) stackL[i]+=stackbuf[i];
      if (recording>=nfrl/nfrt)
       {
        char fname[FNAME_BUFFER];
        sprintf(fname, "%s%s",triggerstub,"3_MAX.rgb");
        dumpFrameRGB(width, height, maxL, fname);
        sprintf(fname, "%s%s",triggerstub,"3_BS0.rgb");
        dumpFrameRGBFromInts(width, height, stackL, nfrt+nfrl, 1, fname);
        sprintf(fname, "%s%s",triggerstub,"3_BS1.rgb");
        dumpFrameRGBFromISub(width, height, stackL, nfrt+nfrl, STACK_GAIN, medianNum?medianMapB:medianMapA, fname);
        sprintf(fname, "%s%s",triggerstub,".vid");
        dumpVideo(nfrt, nfrl, width, height, bufferNum?bufferA:bufferB, bufferNum?bufferB:bufferA, bufferL, fname);
        recording=-1; framesSinceLastTrigger=0;
     } }

    // Once a minute, dump create a stacked exposure lasting for <secondsTimelapseBuff> seconds
    if (timelapseCount>=0)
      { timelapseCount++; }
    else if (utc>frameNextTargetTime)
      {
       int i; for (i=0; i<frameSize*3; i++) stackT[i]=0;
       timelapseCount=0;
      }

    if (timelapseCount>=nfrtl/nfrt)
     {
      char fstub[FNAME_BUFFER], fname[FNAME_BUFFER]; strcpy(fstub, fNameGenerate(utc,"frame_","timelapse_raw",label));
      sprintf(fname, "%s%s",fstub,"BS0.rgb");
      dumpFrameRGBFromInts(width, height, stackT, nfrtl, 1, fname);
      sprintf(fname, "%s%s",fstub,"BS1.rgb");
      dumpFrameRGBFromISub(width, height, stackT, nfrtl, STACK_GAIN, medianNum?medianMapB:medianMapA, fname);
      frameNextTargetTime+=TIMELAPSE_INTERVAL;
      timelapseCount=-1;
     }

    // Update counters for trigger throttling
    triggerThrottleTimer++;
    if (triggerThrottleTimer >= triggerThrottleCycles) { triggerThrottleTimer=0; triggerThrottleCounter=0; }

    // If we're not recording, and have not stopped recording within past 2 seconds, test whether motion sensor has triggered
    if ( (recording<0) && (framesSinceLastTrigger>=framesSinceLastTrigger_ALLOWTRIGGER) && (triggerThrottleCounter<TRIGGER_THROTTLE_MAXEVT) )
     {
      if (testTrigger(  utc , width , height , bufferNum?stackB:stackA , bufferNum?stackA:stackB , nfrt , label ))
       {
        // Camera has triggered
        char fname[FNAME_BUFFER];
        triggerThrottleCounter++;
        sprintf(fname, "%s%s",triggerstub,"2_BS0.rgb");
        dumpFrameRGBFromInts(width, height, bufferNum?stackB:stackA, nfrt, 1, fname);
        sprintf(fname, "%s%s",triggerstub,"2_BS1.rgb");
        dumpFrameRGBFromISub(width, height, bufferNum?stackB:stackA, nfrt, STACK_GAIN, medianNum?medianMapB:medianMapA, fname);
        sprintf(fname, "%s%s",triggerstub,"2_MAX.rgb");
        dumpFrameRGB        (width, height, bufferNum?maxB:maxA, fname);

        sprintf(fname, "%s%s",triggerstub,"1_BS0.rgb");
        dumpFrameRGBFromInts(width, height, bufferNum?stackA:stackB, nfrt, 1, fname);
        sprintf(fname, "%s%s",triggerstub,"1_BS1.rgb");
        dumpFrameRGBFromISub(width, height, bufferNum?stackA:stackB, nfrt, STACK_GAIN, medianNum?medianMapB:medianMapA, fname);
        sprintf(fname, "%s%s",triggerstub,"1_MAX.rgb");
        dumpFrameRGB        (width, height, bufferNum?maxA:maxB, fname);

        memcpy(maxL  , bufferNum?maxB:maxA    , frameSize*3);
        memcpy(stackL, bufferNum?stackB:stackA, frameSize*3*sizeof(int));
        recording=0;
       }
     }

    // If we're not recording, flip buffer numbers. If we are recording, don't do this; keep buffer number pointing at buffer with first second of video
    if (recording<0) bufferNum=!bufferNum;
   }

  free(bufferA); free(bufferB); free(bufferL); free(stackA); free(stackB); free(medianMapA); free(medianMapB); free(medianWorkspace);

  return 0;
 }
