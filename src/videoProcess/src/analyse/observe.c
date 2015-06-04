// observe.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
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

#define Nchannels ( ALLDATAMONO ? 1 : 3 ) /* Number of colour channels to process. *Much* faster to process only one */

#define medianMapUseEveryNthStack     1
#define medianMapUseNImages        2400

#define YUV420  3/2 /* Each pixel is 1.5 bytes in YUV420 stream */

#define MAX_DETECTIONS 1024 /* Maximum detections of a single event; about 40 seconds of frames */
#define MAX_EVENTS        3 /* Number of simultaneous events */

typedef struct detection
 {
  int frameCount;
  int x,y;
 } detection;

typedef struct event
 {
  int  active;
  int  Ndetections;
  char filenameStub[FNAME_BUFFER]; // When testTrigger detects a meteor, this string is set to a filename stub with time stamp of the time when the camera triggered
  int  stackedImage[frameSize*Nchannels];
  detection detections[MAX_DETECTIONS];
 } event;

char *analysisCameraId;

// Generate a filename stub with a timestamp
char *fNameGenerate(char *output, double utc, char *tag, const char *dirname, const char *label)
 {
  static char path[FNAME_BUFFER], output[FNAME_BUFFER];
  const double JD = utc / 86400.0 + 2440587.5;
  int year,month,day,hour,min,status; double sec;
  InvJulianDay(JD-0.5,&year,&month,&day,&hour,&min,&sec,&status,output); // Subtract 0.5 from Julian Day as we want days to start at noon, not midnight
  sprintf(path,"%s/%s_%s/%04d%02d%02d", OUTPUT_PATH, dirname, label, year, month, day);
  sprintf(output, "mkdir -p %s", path); status=system(output);
  InvJulianDay(JD,&year,&month,&day,&hour,&min,&sec,&status,output);
  sprintf(output,"%s/%04d%02d%02d%02d%02d%02d_%s_%s", path, year, month, day, hour, min, (int)sec, analysisCameraId, tag);
  return output;
 }

// Record metadata to accompany a file. fname must be writable.
void writeMetaData(char *fname, int nItems, ...)
 {
  // Change file extension to .txt
  int flen = strlen(fname);
  int i=flen-1;
  while ((i>0)&&(fname[i]!='.')) i--;
  sprintf(fname+i,".txt");

  // Write metadata
  FILE *f=fopen(fname,"w");
  if (!f) return;
  va_list ap;
  va_start(ap, nItems);
  for (i=0; i<nItems; i++)
   {
    char *x = va_arg(ap, char*);
    char *y = va_arg(ap, char*);
    fprintf(f,"%s %s\n",x,y);
   }
  va_end(ap);
  fclose(f);
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
int testTrigger(const double utc, const int width, const int height, const int *imageB, const int *imageA, const unsigned char *mask, int *pastTriggerMap, const int coAddedFrames, const char *label)
 {
  int x,y,d;
  int output=0;

  const int margin=10; // Ignore pixels within this distance of the edge
  const int Npixels=30; // To trigger this number of pixels connected together must have brightened
  const int radius=8; // Pixel must be brighter than test pixels this distance away
  const int threshold=12*coAddedFrames; // Pixel must have brightened by at least this amount.
  const int frameSize=width*height;
  int *triggerMap   = calloc(1,frameSize*sizeof(int)); // triggerMap is a 2D array of ints used to mark out pixels which have brightened suspiciously.
  int *triggerBlock = calloc(1,frameSize*sizeof(int)); // triggerBlock is a count of how many pixels are in each numbered connected block
  unsigned char *triggerRGB = calloc(1,frameSize*3);
  unsigned char *triggerR = triggerRGB;
  unsigned char *triggerG = triggerRGB + frameSize*1; // These arrays are used to produce diagnostic images when the camera triggers
  unsigned char *triggerB = triggerRGB + frameSize*2;
  int  blockNum     = 1;

  static unsigned long long pastTriggerMapAverage = 1;
  unsigned int              nPixelsWithinMask = 1;
  unsigned long long        pastTriggerMapAverageNew = 0;

  for (y=margin; y<height-margin; y++)
   for (x=margin;x<width-margin; x++)
    {
     const int o=x+y*width;
     pastTriggerMapAverageNew+=pastTriggerMap[o];
     if (mask[o]) nPixelsWithinMask++;
     triggerR[o] = CLIP256( (imageB[o]-imageA[o])*64/threshold ); // RED channel - difference between images B and A
     triggerG[o] = CLIP256( pastTriggerMap[o] * 256 / (2*pastTriggerMapAverage) ); // GRN channel - map of pixels which are excluded for triggering too often
     if (mask[o] && (imageB[o]-imageA[o]>threshold)) // Search for pixels which have brightened by more than threshold since past image
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
           pastTriggerMap[o]++;
           triggerB[o] = 128;
           int blockId=0;
           if (triggerMap[o-1      ]) { if (!blockId) { blockId=triggerMap[o-1      ]; } else { triggerBlocksMerge(triggerBlock, triggerMap+(y-1)*width, width*2, triggerMap[o-1      ], blockId); } }
           if (triggerMap[o+1-width]) { if (!blockId) { blockId=triggerMap[o+1-width]; } else { triggerBlocksMerge(triggerBlock, triggerMap+(y-1)*width, width*2, triggerMap[o+1-width], blockId); } }
           if (triggerMap[o-width  ]) { if (!blockId) { blockId=triggerMap[o-width  ]; } else { triggerBlocksMerge(triggerBlock, triggerMap+(y-1)*width, width*2, triggerMap[o-width  ], blockId); } }
           if (triggerMap[o-1-width]) { if (!blockId) { blockId=triggerMap[o-1-width]; } else { triggerBlocksMerge(triggerBlock, triggerMap+(y-1)*width, width*2, triggerMap[o-1-width], blockId); } }
           if (blockId==0           ) blockId=blockNum++;

           if (pastTriggerMap[o]<2*pastTriggerMapAverage) triggerBlock[blockId]++;
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
    sprintf(fname, "%s%s",triggerstub,"_MAP.sep");
    dumpFrameRGB(width, height, triggerRGB, fname);
    writeMetaData(fname, 1, "cameraId", analysisCameraId);
   }

  free(triggerMap); free(triggerBlock); free(triggerRGB);
  pastTriggerMapAverage = pastTriggerMapAverageNew / nPixelsWithinMask + 1;
  return output;
 }

// Read enough video (1 second) to create the stacks used to test for triggers
int readFrameGroup(void *videoHandle, int nfr, int width, int height, unsigned char *buffer, int *stack1, int *stack2, int *medianWorkspace, double *utc, int (*fetchFrame)(void *,unsigned char *,double *))
 {
  const int frameSize = width*height;
  int i,j;
  memset(stack1, 0, frameSize*Nchannels*sizeof(int)); // Stack1 is wiped prior to each call to this function

  unsigned char *tmprgb;
  if (ALLDATAMONO) tmprgb = tmpc;
  else             tmprgb = malloc(Nchannels*frameSize);

  for (j=0;j<nfr;j++)
   {
    unsigned char *tmpc = buffer+j*frameSize*YUV420;
    if ((*fetchFrame)(videoHandle,tmpc,utc) != 0) { if (DEBUG) gnom_log("Error grabbing"); return 1; }
    if (!ALLDATAMONO) Pyuv420torgb(tmpc,tmpc+frameSize,tmpc+frameSize*5/4,tmprgb,tmprgb+frameSize,tmprgb+frameSize*2,width,height);
#pragma omp parallel for private(i)
    for (i=0; i<frameSize*Nchannels; i++) stack1[i]+=tmprgb[i];
   }

  if (stack2)
   {
#pragma omp parallel for private(i)
    for (i=0; i<frameSize*Nchannels; i++) stack2[i]+=stack1[i]; // Stack2 can stack output of many calls to this function
   }

  // Add the pixel values in this stack into the histogram in medianWorkspace
  if (medianWorkspace)
   {
#pragma omp parallel for private(j)
    for (j=0; j<frameSize*Nchannels; j++)
     {
      int d;
      int pixelVal = CLIP256(stack1[j]/nfr);
      medianWorkspace[j*256 + pixelVal]++;
     }
   }
  if (!ALLDATAMONO) free(tmprgb);
  return 0;
 }

int observe(void *videoHandle, const int utcoffset, const int tstart, const int tstop, const int width, const int height, const char *label, const unsigned char *mask, int (*fetchFrame)(void *,unsigned char *,double *), int (*rewindVideo)(void *, double *))
 {
  char line[FNAME_BUFFER],line2[FNAME_BUFFER],line3[FNAME_BUFFER];
  double utc;

  if (DEBUG) { sprintf(line, "Starting observing run at %s; observing run will end at %s.", StrStrip(FriendlyTimestring(tstart),line2),StrStrip(FriendlyTimestring(tstop),line3)); gnom_log(line); }

  const float fps = VIDEO_FPS;       // Requested frame rate

  const int frameSize = width * height;

  // List of moving objects we are currently tracking
  event          eventList  = calloc(MAX_EVENTS, sizeof(event));

  // Trigger buffers. These are used to store 1 second of video for comparison with the next
  const int      buffNGroups    = fps * TRIGGER_MAXRECORDLEN / TRIGGER_FRAMEGROUP;
  const int      buffGroupBytes = TRIGGER_FRAMEGROUP*frameSize*YUV420;
  const int      buffNFrames    = buffNGroups * TRIGGER_FRAMEGROUP;
  const int      bufflen        = buffNGroups * buffGroupBytes;
  unsigned char *buffer         = malloc(bufflen);
  int           *stackA         = malloc(frameSize*sizeof(int)*Nchannels); // A stacked version of the current and preceding frame group; used to form a difference image
  int           *stackB         = malloc(frameSize*sizeof(int)*Nchannels);

  // Timelapse buffers
  double        timelapseFrameStart = 1e40; // Store timelapse exposures at set intervals. This is UTC of next frame, but we don't start until we've done a run-in period
  const int     framesTimelapse     = fps * TIMELAPSE_EXPOSURE;
  int          *stackT              = malloc(frameSize*sizeof(int)*Nchannels);

  // Median maps are used for background subtraction. Maps A and B are used alternately and contain the median value of each pixel.
  unsigned char *medianMap       = calloc(1,frameSize*Nchannels); // The median value of each pixel, sampled over 255 stacked images
  int           *medianWorkspace = calloc(1,frameSize*Nchannels*256*sizeof(int)); // Workspace which counts the number of times any given pixel has a particular value

  // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
  int           *pastTriggerMap  = calloc(1,frameSize*sizeof(int));

  if ((!events)||(!buffer) || (!stackA)||(!stackB)||(!stackT) || (!medianMap)||(!medianWorkspace) || (!pastTriggerMap) ) { sprintf(temp_err_string, "ERROR: malloc fail in observe."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  int groupNum       = 0; // Flag for whether we're feeding images into stackA or stackB
  int medianCount    = 0; // Count how many frames we've fed into the brightness histograms in medianWorkspace
  int timelapseCount =-1; // Count how many frames have been stacked into the timelapse buffer (stackT)
  int frameCounter   = 0;
  int runInCountdown = 8 + medianMapUseEveryNthStack*medianMapUseNImages; // Let the camera run for a period before triggering, as it takes this long to make first median map

  // Trigger throttling
  const int triggerThrottlePeriod = (TRIGGER_THROTTLE_PERIOD * 60. * fps / TRIGGER_FRAMEGROUP); // Reset trigger throttle counter after this many frame groups have been processed
  int       triggerThrottleTimer  = 0;
  int       triggerThrottleCounter= 0;

  // Processing loop
  while (1)
   {
    int t = time(NULL) + utcoffset;
    if (t>=tstop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!

    // Once we've done initial run-in period, rewind the tape to the beginning if we can
    if (runInCountdown && !--runInCountdown)
     {
      if (DEBUG) { sprintf(line, "Run-in period completed."); gnom_log(line); }
      (*rewindVideo)(videoHandle,&utc);
      timelapseFrameStart = ceil(utc/60)*60; // Start making timelapse video
     }

    // Work out where we're going to read next second of video to. Either bufferA / bufferB, or the long buffer if we're recording
    unsigned char *bufferPos = buffer + (frameCounter % buffNGroups)*buffGroupBytes;

    // Read the next second of video
    const int includeInMedianHistograms = ((medianCount%medianMapUseEveryNthStack)==0);
    int status = readFrameGroup(videoHandle, TRIGGER_FRAMEGROUP, width, height, bufferPos, groupNum?stackB:stackA, (timelapseCount>=0)?stackT:NULL, includeInMedianHistograms?medianWorkspace:NULL, &utc, fetchFrame);
    if (status) break; // We've run out of video
    frameCounter++;

    // If we've stacked enough frames since we last made a median map, make a new median map
    medianCount++;
    if (medianCount==medianMapUseNImages*medianMapUseEveryNthStack)
     {
      medianCalculate(width, height, medianWorkspace, medianMap);
      medianCount=0;
     }

    // If we're recording, test whether we're ready to stop recording
    if (recording>-1)
     {
      int i;
      int *stackbuf = bufferNum?stackB:stackA;
      recording++;
#pragma omp parallel for private(i)
      for (i=0; i<frameSize*3; i++) stackL[i]+=stackbuf[i];
      if (recording>=nfrl/nfrt)
       {
        char fname[FNAME_BUFFER];
        sprintf(fname, "%s%s",triggerstub,"3_BS0.rgb");
        dumpFrameRGBFromInts(width, height, stackL, nfrt+nfrl, 1, fname);
        writeMetaData(fname, 1, "cameraId", analysisCameraId);
        sprintf(fname, "%s%s",triggerstub,"3_BS1.rgb");
        dumpFrameRGBFromISub(width, height, stackL, nfrt+nfrl, STACK_GAIN, medianMap, fname);
        writeMetaData(fname, 1, "cameraId", analysisCameraId);
        sprintf(fname, "%s%s",triggerstub,".vid");
        dumpVideo(nfrt, nfrl, width, height, bufferNum?bufferA:bufferB, bufferNum?bufferB:bufferA, bufferL, fname);
        writeMetaData(fname, 1, "cameraId", analysisCameraId);
        recording=-1; 
     } }

    // Once a minute, dump create a stacked exposure lasting for <secondsTimelapseBuff> seconds
    if (timelapseCount>=0)
      { timelapseCount++; }
    else if (utc>timelapseFrameStart)
      {
       memset(stackT, 0, frameSize*3*sizeof(int));
       timelapseCount=0;
      }

    if (timelapseCount>=nfrtl/nfrt)
     {
      char fstub[FNAME_BUFFER], fname[FNAME_BUFFER]; strcpy(fstub, fNameGenerate(utc,"frame_","timelapse_raw",label));
      sprintf(fname, "%s%s",fstub,"BS0.rgb");
      dumpFrameRGBFromInts(width, height, stackT, nfrtl, 1, fname);
      writeMetaData(fname, 1, "cameraId", analysisCameraId);
      sprintf(fname, "%s%s",fstub,"BS1.rgb");
      dumpFrameRGBFromISub(width, height, stackT, nfrtl, STACK_GAIN, medianMap, fname);
      writeMetaData(fname, 1, "cameraId", analysisCameraId);
      timelapseFrameStart+=TIMELAPSE_INTERVAL;
      timelapseCount=-1;
     }

    // Update counters for trigger throttling
    triggerThrottleTimer++;
    if (triggerThrottleTimer >= triggerThrottleCycles) { triggerThrottleTimer=0; triggerThrottleCounter=0; }

    // If we're not recording, and have not stopped recording within past 2 seconds, test whether motion sensor has triggered
    if (recording<0)
     {
      if (testTrigger(  utc , width , height , bufferNum?stackB:stackA , bufferNum?stackA:stackB , mask , pastTriggerMap , nfrt , label ) && (!runInCountdown) && (triggerThrottleCounter<TRIGGER_THROTTLE_MAXEVT) )
       {
        // Camera has triggered
        char fname[FNAME_BUFFER];
        triggerThrottleCounter++;
        sprintf(fname, "%s%s",triggerstub,"2_BS0.rgb");
        dumpFrameRGBFromInts(width, height, bufferNum?stackB:stackA, nfrt, 1, fname);
        writeMetaData(fname, 1, "cameraId", analysisCameraId);
        sprintf(fname, "%s%s",triggerstub,"2_BS1.rgb");
        dumpFrameRGBFromISub(width, height, bufferNum?stackB:stackA, nfrt, STACK_GAIN, medianMap, fname);
        writeMetaData(fname, 1, "cameraId", analysisCameraId);
        sprintf(fname, "%s%s",triggerstub,"1_BS0.rgb");
        dumpFrameRGBFromInts(width, height, bufferNum?stackA:stackB, nfrt, 1, fname);
        writeMetaData(fname, 1, "cameraId", analysisCameraId);
        sprintf(fname, "%s%s",triggerstub,"1_BS1.rgb");
        dumpFrameRGBFromISub(width, height, bufferNum?stackA:stackB, nfrt, STACK_GAIN, medianMap, fname);
        writeMetaData(fname, 1, "cameraId", analysisCameraId);
        memcpy(stackL, bufferNum?stackB:stackA, frameSize*3*sizeof(int));
        recording=0;
       }
     }

    groupNum=!groupNum;
   }

  free(buffer); free(events); free(stackA); free(stackB); free(stackT); free(medianMap); free(medianWorkspace); free(pastTriggerMap);

  return 0;
 }
