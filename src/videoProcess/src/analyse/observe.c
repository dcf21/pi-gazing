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
#include "analysis/observe.h"
#include "analysis/trigger.h"
#include "utils/asciidouble.h"
#include "utils/tools.h"
#include "utils/error.h"
#include "utils/JulianDate.h"
#include "vidtools/color.h"

#include "settings.h"

#define medianMapUseEveryNthStack     1
#define medianMapUseNImages        2400

#define YUV420  3/2 /* Each pixel is 1.5 bytes in YUV420 stream */

// Generate a filename stub with a timestamp
char *fNameGenerate(char *output, const char *cameraId, double utc, char *tag, const char *dirname, const char *label)
 {
  static char path[FNAME_BUFFER], output[FNAME_BUFFER];
  const double JD = utc / 86400.0 + 2440587.5;
  int year,month,day,hour,min,status; double sec;
  InvJulianDay(JD-0.5,&year,&month,&day,&hour,&min,&sec,&status,output); // Subtract 0.5 from Julian Day as we want days to start at noon, not midnight
  sprintf(path,"%s/%s_%s/%04d%02d%02d", OUTPUT_PATH, dirname, label, year, month, day);
  sprintf(output, "mkdir -p %s", path); status=system(output);
  InvJulianDay(JD,&year,&month,&day,&hour,&min,&sec,&status,output);
  sprintf(output,"%s/%04d%02d%02d%02d%02d%02d_%s_%s", path, year, month, day, hour, min, (int)sec, cameraId, tag);
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

// Read enough video (1 second) to create the stacks used to test for triggers
int readFrameGroup(observeStatus *os, unsigned char *buffer, int *stack1, int *stack2)
 {
  int i,j;
  memset(stack1, 0, os->frameSize*Nchannels*sizeof(int)); // Stack1 is wiped prior to each call to this function

  unsigned char *tmprgb;
  if (ALLDATAMONO) tmprgb = tmpc;
  else             tmprgb = malloc(Nchannels*os->frameSize);

  for (j=0;j<TRIGGER_FRAMEGROUP;j++)
   {
    unsigned char *tmpc = buffer+j*os->frameSize*YUV420;
    if ((*fetchFrame)(os->videoHandle,tmpc,&os->utc) != 0) { if (DEBUG) gnom_log("Error grabbing"); return 1; }
    if (!ALLDATAMONO) Pyuv420torgb(tmpc,tmpc+os->frameSize,tmpc+os->frameSize*5/4,tmprgb,tmprgb+os->frameSize,tmprgb+os->frameSize*2,os->width,os->height);
#pragma omp parallel for private(i)
    for (i=0; i<os->frameSize*Nchannels; i++) stack1[i]+=tmprgb[i];
   }

  if (stack2)
   {
#pragma omp parallel for private(i)
    for (i=0; i<os->frameSize*Nchannels; i++) stack2[i]+=stack1[i]; // Stack2 can stack output of many calls to this function
   }

  // Add the pixel values in this stack into the histogram in medianWorkspace
  const int includeInMedianHistograms = ((medianCount%medianMapUseEveryNthStack)==0);
  if (includeInMedianHistograms)
   {
#pragma omp parallel for private(j)
    for (j=0; j<os->frameSize*Nchannels; j++)
     {
      int d;
      int pixelVal = CLIP256(stack1[j]/TRIGGER_FRAMEGROUP);
      medianWorkspace[j*256 + pixelVal]++;
     }
   }
  if (!ALLDATAMONO) free(tmprgb);
  return 0;
 }

int observe(void *videoHandle, const char *cameraId, const int utcoffset, const int tstart, const int tstop, const int width, const int height, const char *label, const unsigned char *mask, int (*fetchFrame)(void *,unsigned char *,double *), int (*rewindVideo)(void *, double *))
 {
  char line[FNAME_BUFFER],line2[FNAME_BUFFER],line3[FNAME_BUFFER];

  if (DEBUG) { sprintf(line, "Starting observing run at %s; observing run will end at %s.", StrStrip(FriendlyTimestring(tstart),line2),StrStrip(FriendlyTimestring(tstop),line3)); gnom_log(line); }

  observeStatus *os = calloc(1, sizeof(observeStatus);
  if (!os) { sprintf(temp_err_string, "ERROR: malloc fail in observe."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  os->videoHandle = videoHandle;
  os->width = width;
  os->height = height;
  os->mask = mask;
  os->fetchFrame = fetchFrame;
  os->fps = VIDEO_FPS;       // Requested frame rate
  os->frameSize = width * height;


  // Trigger buffers. These are used to store 1 second of video for comparison with the next
  os->buffNGroups    = os->fps * TRIGGER_MAXRECORDLEN / TRIGGER_FRAMEGROUP;
  os->buffGroupBytes = TRIGGER_FRAMEGROUP*os->frameSize*YUV420;
  os->buffNFrames    = os->buffNGroups * TRIGGER_FRAMEGROUP;
  os->bufflen        = os->buffNGroups * os->buffGroupBytes;
  os->buffer         = malloc(os->bufflen);
  os->stackA         = malloc(os->frameSize*sizeof(int)*Nchannels); // A stacked version of the current and preceding frame group; used to form a difference image
  os->stackB         = malloc(os->frameSize*sizeof(int)*Nchannels);

  os->triggerPrefixNGroups = TRIGGER_PREFIX_TIME * os->fps / TRIGGER_FRAMEGROUP;
  os->triggerSuffixNGroups = TRIGGER_SUFFIX_TIME * os->fps / TRIGGER_FRAMEGROUP;

  // Timelapse buffers
  os->utc                 = 0;
  os->timelapseFrameStart = 1e40; // Store timelapse exposures at set intervals. This is UTC of next frame, but we don't start until we've done a run-in period
  os->framesTimelapse     = os->fps * TIMELAPSE_EXPOSURE;
  os->stackT              = malloc(os->frameSize*sizeof(int)*Nchannels);

  // Median maps are used for background subtraction. Maps A and B are used alternately and contain the median value of each pixel.
  os->medianMap       = calloc(1,os->frameSize*Nchannels); // The median value of each pixel, sampled over 255 stacked images
  os->medianWorkspace = calloc(1,os->frameSize*Nchannels*256*sizeof(int)); // Workspace which counts the number of times any given pixel has a particular value

  // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
  os->pastTriggerMap  = calloc(1,os->frameSize*sizeof(int));

  // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
  os->triggerMap   = calloc(1,os->frameSize*sizeof(int)); // triggerMap is a 2D array of ints used to mark out pixels which have brightened suspiciously.
  os->triggerBlock = calloc(1,os->frameSize*sizeof(int)); // triggerBlock is a count of how many pixels are in each numbered connected block
  os->triggerRGB   = calloc(1,os->frameSize*3);


  if ((!os->buffer) || (!os->stackA)||(!os->stackB)||(!os->stackT) || (!os->medianMap)||(!os->medianWorkspace) || (!os->pastTriggerMap) || (!os->triggerMap)||(!os->triggerBlock)||(!os->triggerRGB) )
   { sprintf(temp_err_string, "ERROR: malloc fail in observe."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  os->groupNum       = 0; // Flag for whether we're feeding images into stackA or stackB
  os->medianCount    = 0; // Count how many frames we've fed into the brightness histograms in medianWorkspace
  os->timelapseCount =-1; // Count how many frames have been stacked into the timelapse buffer (stackT)
  os->frameCounter   = 0;
  os->runInCountdown = 8 + medianMapUseEveryNthStack*medianMapUseNImages; // Let the camera run for a period before triggering, as it takes this long to make first median map
  os->noiseLevel     = 128;

  // Trigger throttling
  os->triggerThrottlePeriod = (TRIGGER_THROTTLE_PERIOD * 60. * os->fps / TRIGGER_FRAMEGROUP); // Reset trigger throttle counter after this many frame groups have been processed
  os->triggerThrottleTimer  = 0;
  os->triggerThrottleCounter= 0;

  // Processing loop
  while (1)
   {
    int t = time(NULL) + utcoffset;
    if (t>=tstop) break; // Check how we're doing for time; if we've reached the time to stop, stop now!

    // Once we've done initial run-in period, rewind the tape to the beginning if we can
    if (os->runInCountdown && !--os->runInCountdown)
     {
      if (DEBUG) { sprintf(line, "Run-in period completed."); gnom_log(line); }
      (*rewindVideo)(os->videoHandle,&os->utc);
      os->timelapseFrameStart = ceil(os->utc/60)*60; // Start making timelapse video
     }

    // Work out where we're going to read next second of video to. Either bufferA / bufferB, or the long buffer if we're recording
    unsigned char *bufferPos = os->buffer + (os->frameCounter % os->buffNGroups)*os->buffGroupBytes;

    // Once on each cycle through the video buffer, estimate the thermal noise of the camera
    if (bufferPos==os->buffer) os->noiseLevel = estimateNoiseLevel(os->width,os->height,os->buffer,16);

    // Read the next second of video
    int status = readFrameGroup(os, bufferPos, groupNum?stackB:stackA, (timelapseCount>=0)?stackT:NULL);
    if (status) break; // We've run out of video
    os->frameCounter++;

    // If we've stacked enough frames since we last made a median map, make a new median map
    os->medianCount++;
    if (os->medianCount==medianMapUseNImages*medianMapUseEveryNthStack)
     {
      medianCalculate(os->width, os->height, Nchannels, os->medianWorkspace, os->medianMap);
      os->medianCount=0;
     }

    // Periodically, dump a stacked timelapse exposure lasting for <secondsTimelapseBuff> seconds
    if (os->timelapseCount>=0) { os->timelapseCount++; }
    else if (os->utc > os->timelapseFrameStart)
      {
       memset(os->stackT, 0, os->frameSize*3*sizeof(int));
       os->timelapseCount=0;
      }

    // If timelapse exposure is finished, dump it
    if (os->timelapseCount>=os->framesTimelapse/TRIGGER_FRAMEGROUP)
     {
      char fstub[FNAME_BUFFER], fname[FNAME_BUFFER]; strcpy(fstub, fNameGenerate(utc,cameraId,"frame_","timelapse_raw",label));
      sprintf(fname, "%s%s",fstub,"BS0.rgb");
      dumpFrameFromInts(os->width, os->height, Nchannels, os->stackT, os->framesTimelapse, 1, fname);
      writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel", os->noiseLevel/sqrt(os->framesTimelapse), "stackedFrames", os->framesTimelapse);
      sprintf(fname, "%s%s",fstub,"BS1.rgb");
      dumpFrameFromISub(os->width, os->height, Nchannels, os->stackT, os->framesTimelapse, STACK_GAIN, os->medianMap, fname);
      writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel", os->noiseLevel/sqrt(os->framesTimelapse)*STACK_GAIN, "stackedFrames", os->framesTimelapse);
      os->timelapseFrameStart+=TIMELAPSE_INTERVAL;
      os->timelapseCount=-1;
     }

    // Update counters for trigger throttling
    triggerThrottleTimer++;
    if (triggerThrottleTimer >= triggerThrottleCycles) { triggerThrottleTimer=0; triggerThrottleCounter=0; }

    // Test whether motion sensor has triggered
    os->triggeringAllowed = ((!runInCountdown) && (triggerThrottleCounter<TRIGGER_THROTTLE_MAXEVT) );
    registerTriggerEnds(os);
    checkForTriggers(  os, bufferNum?stackB:stackA , bufferNum?stackA:stackB , TRIGGER_FRAMEGROUP , label );

    os->groupNum=!os->groupNum;
   }

  free(os->triggerMap); free(os->triggerBlock); free(os->triggerRGB);
  free(os->buffer); free(os->stackA); free(os->stackB); free(os->stackT); free(os->medianMap); free(os->medianWorkspace); free(os->pastTriggerMap); free(os);
  return 0;
 }

// Register a new trigger event
void registerTriggerStart(observeStatus *os, const int *image1, const int *image2, const int coAddedFrames, int x, int y)
 {
  int i;
  if (!os->triggeringAllowed) return;
  for (i=0; i<MAX_EVENTS; i++) if (!os->eventList[i].active) break;
  if (i>=MAX_EVENTS) return; // No free trigger storage space
  os->triggerThrottleCounter++;

  os->eventList[i].active = 1;
  os->eventList[i].Ndetections = 1;
  os->eventList[i].detections[0].frameCount = os->frameCounter;
  os->eventList[i].detections[0].x          = x;
  os->eventList[i].detections[0].y          = y;

  char fname[FNAME_BUFFER];
  strcpy(os->eventList[i].filenameStub, fNameGenerate(utc,"trigger","triggers_raw",label));
  sprintf(fname, "%s%s",os->eventList[i].filenameStub,"_MAP.sep");
  dumpFrame(os->width, os->height, 3, os->triggerRGB, fname);
  writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel);

  sprintf(fname, "%s%s",os->eventList[i].filenameStub,"2_BS0.rgb");
  dumpFrameFromInts(os->width, os->height, Nchannels, stack1, coAddedFrames, 1, fname);
  writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel", os->noiseLevel/sqrt(coAddedFrames), "stackedFrames", coAddedFrames);
  sprintf(fname, "%s%s",os->eventList[i].filenameStub,"2_BS1.rgb");
  dumpFrameFromISub(os->width, os->height, Nchannels, stack1, coAddedFrames, STACK_GAIN, os->medianMap, fname);
  writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel", os->noiseLevel/sqrt(coAddedFrames)*STACK_GAIN, "stackedFrames", coAddedFrames);
  sprintf(fname, "%s%s",os->eventList[i].filenameStub,"1_BS0.rgb");
  dumpFrameFromInts(os->width, os->height, Nchannels, stack2, coAddedFrames, 1, fname);
  writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel", os->noiseLevel/sqrt(coAddedFrames), "stackedFrames", coAddedFrames);
  sprintf(fname, "%s%s",os->eventList[i].filenameStub,"1_BS1.rgb");
  dumpFrameFromISub(os->width, os->height, Nchannels, stack2, nfr, STACK_GAIN, os->medianMap, fname);
  writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel", os->noiseLevel/sqrt(coAddedFrames)*STACK_GAIN, "stackedFrames", coAddedFrames);
  memcpy(os->eventList[i].stackedImage, stack1, os->frameSize*Nchannels*sizeof(int));
 }

// Check through list of events we are currently tracking. Weed out any which haven't been seen for a long time, or are exceeding maximum allowed recording time.
void registerTriggerEnds(observeStatus *os)
 {
  int i;
  int *stackbuf = os->bufferNum?os->stackB:os->stackA;
  for (i=0; i<MAX_EVENTS; i++)
   if (os->eventList[i].active)
    {
     int j;
     const int N0 = 0;
     const int N1 = os->eventList[i].Ndetections/2;
     const int N2 = os->eventList[i].Ndetections-1;
#pragma omp parallel for private(i)
     for (j=0; j<os->frameSize*Nchannels; j++) eventList[i].stackL[j]+=stackbuf[j];

     if ( ( os->eventList[i].detections[N0].frameCount < (os->frameCounter-(os->buffNGroups-os->triggerPrefixNGroups)) ) || // Event is exceeding TRIGGER_MAXRECORDLEN?
          ( os->eventList[i].detections[N2].frameCount < (os->frameCounter-os->triggerSuffixNGroups)) ) ) // ... or event hasn't been seen for TRIGGER_SUFFIXTIME?
      {
        os->eventList[i].active=0;

        int coAddedFrames = (os->frameCounter - os->eventList[i].detections[0].frameCount) * TRIGGER_FRAMEGROUP;
        char fname[FNAME_BUFFER], pathJSON[LSTR_LENGTH];
        sprintf(fname, "%s%s",os->eventList[i].filenameStub,"3_BS0.rgb");
        dumpFrameFromInts(os->width, os->height, Nchannels, os->eventList[i].stackedImage, coAddedFrames, 1, fname);
        writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel", os->noiseLevel/sqrt(coAddedFrames), "stackedFrames", coAddedFrames);
        sprintf(fname, "%s%s",os->eventList[i].filenameStub,"3_BS1.rgb");
        dumpFrameFromISub(os->width, os->height, Nchannels, os->eventList[i].stackedImage, coAddedFrames, os->medianMap, fname);
        writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "stackNoiseLevel", os->noiseLevel/sqrt(coAddedFrames)*STACK_GAIN, "stackedFrames", coAddedFrames);

        // Dump a video of the meteor from our video buffer
        int            videoBytes  = (os->frameCounter - os->eventList[i].detections[N0].frameCount + os->triggerPrefixNGroups)*os->buffGroupBytes;
        unsigned char *bufferPos   = os->buffer + (os->frameCounter % os->buffNGroups)*os->buffGroupBytes;
        unsigned char *video1      = NULL;
        int            video1bytes = 0;
        unsigned char *video2      = bufferPos - videoBytes;
        int            video2bytes = videoBytes;

        // Video spans a buffer wrap-around, so need to include two chunks of video data
        if (video2<os->buffer)
         {
          video1bytes = os->buffer - video2;
          video1      = os->buffer + os->bufflen - video1bytes;
          video2bytes-= video1bytes;
          video2      = os->buffer;
         }

        // Write path of event as JSON string
        {
         int j=0,k=0;
         sprintf(pathJSON+k,"["); k+=strlen(pathJSON+k);
         for (j=0; j<os->eventList[i].Ndetections; j++)
          {
           sprintf(pathJSON+k,"%s[%d,%d,%.3f]", j?",":"", os->eventList[i].detections[j].x, os->eventList[i].detections[j].y, os->eventList[i].detections[j].utc); k+=strlen(pathJSON+k);
          }
         sprintf(pathJSON+k,"]"); k+=strlen(pathJSON+k);
        }

        sprintf(fname, "%s%s",os->eventList[i].filenameStub,".vid");
        dumpVideo(nfrt, nfrl, os->width, os->height, Nchannels, video1, video1bytes, video2, video2bytes, fname);
        writeMetaData(fname, 1, "cameraId", os->cameraId, "inputNoiseLevel", os->noiseLevel, "path", meteorPath,
                                "x0", os->eventList[i].detections[N0].x, "y0", os->eventList[i].detections[N0].y, "t0", os->eventList[i].detections[N0].utc,
                                "x1", os->eventList[i].detections[N1].x, "y1", os->eventList[i].detections[N1].y, "t1", os->eventList[i].detections[N1].utc,
                                "x2", os->eventList[i].detections[N2].x, "y2", os->eventList[i].detections[N2].y, "t2", os->eventList[i].detections[N2].utc,
                     );
     }
   }
 }
