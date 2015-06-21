// observe.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef OBSERVE_H
#define OBSERVE_H 1

#define MAX_DETECTIONS 1024 /* Maximum detections of a single event; about 40 seconds of frames */
#define MAX_EVENTS        3 /* Number of simultaneous events */

#define MAX_TRIGGER_BLOCKS 65536

#include "str_constants.h"
#include "settings.h"

typedef struct detection
 {
  int    frameCount;
  int    x,y,npixels,amplitude;
  double utc;
 } detection;

typedef struct event
 {
  int  active;
  int  Ndetections;
  char filenameStub[FNAME_LENGTH]; // When testTrigger detects a meteor, this string is set to a filename stub with time stamp of the time when the camera triggered
  int *stackedImage; // Stacked image, averaged over whole duration of event
  int *maxStack; // Maximum pixel values over whole duration of event
  detection detections[MAX_DETECTIONS];
 } event;

typedef struct observeStatus
 {
  void *videoHandle;
  int width,height;
  const unsigned char *mask;
  const char *label;
  int (*fetchFrame)(void *,unsigned char *,double *);
  float fps;
  int frameSize;
  const char *cameraId;

  double utc;
  int triggeringAllowed;
  double noiseLevel;

  // Trigger buffers. These are used to store 1 second of video for comparison with the next
  int            buffNGroups;
  int            buffGroupBytes;
  int            buffNFrames;
  int            bufflen;
  unsigned char *buffer;
  int           *stack[STACK_COMPARISON_INTERVAL+1];
  int            triggerPrefixNGroups;
  int            triggerSuffixNGroups;

  // Timelapse buffers
  double  timelapseUTCStart;
  int     framesTimelapse;
  int    *stackT;

  // Median maps are used for background subtraction. Maps A and B are used alternately and contain the median value of each pixel.
  unsigned char *medianMap;
  int           *medianWorkspace;

  // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
  int           *pastTriggerMap;

  // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
  int  Nblocks;
  int *triggerMap;
  int *triggerBlock_N, *triggerBlock_top, *triggerBlock_bot, *triggerBlock_sumx, *triggerBlock_sumy, *triggerBlock_suml, *triggerBlock_redirect;
  unsigned char *triggerRGB;

  int groupNum; // Flag for whether we're feeding images into stackA or stackB
  int medianCount; // Count how many frames we've fed into the brightness histograms in medianWorkspace
  int timelapseCount; // Count how many frames have been stacked into the timelapse buffer (stackT)
  int frameCounter;
  int runInCountdown; // Let the camera run for a period before triggering, as it takes this long to make first median map

  int triggerThrottlePeriod; // Reset trigger throttle counter after this many frame groups have been processed
  int triggerThrottleTimer;
  int triggerThrottleCounter;

  event eventList[MAX_EVENTS];
 } observeStatus;

char *fNameGenerate  (char *output, const char *cameraId, double utc, char *tag, const char *dirname, const char *label);
int   readFrameGroup (observeStatus *os, unsigned char *buffer, int *stack1, int *stack2);
int   observe        (void *videoHandle, const char *cameraId, const int utcoffset, const int tstart, const int tstop, const int width, const int height, const char *label, const unsigned char *mask, int (*fetchFrame)(void *,unsigned char *,double *), int (*rewindVideo)(void *, double *));
void registerTrigger(observeStatus *os, const int blockId, const int xpos, const int ypos, const int npixels, const int amplitude, const int *image1, const int *image2, const int coAddedFrames);
void registerTriggerEnds(observeStatus *os);

#endif

