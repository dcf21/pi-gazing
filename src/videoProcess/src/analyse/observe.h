// observe.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef OBSERVE_H
#define OBSERVE_H 1

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

typedef struct observeStatus
 {
  void *videoHandle;
  int width,height;
  unsigned char *mask;
  int (*fetchFrame)(void *,unsigned char *,double *);
  float fps;
  int frameSize;
  char *cameraId;

  double utc;
  int triggeringAllowed;
  double noiseLevel;

  // Trigger buffers. These are used to store 1 second of video for comparison with the next
  int            buffNGroups;
  int            buffGroupBytes;
  int            buffNFrames;
  int            bufflen;
  unsigned char *buffer;
  int           *stackA;
  int           *stackB;
  int            triggerPrefixNGroups;
  int            triggerSuffixNGroups;

  // Timelapse buffers
  double  timelapseFrameStart;
  int     framesTimelapse;
  int    *stackT;

  // Median maps are used for background subtraction. Maps A and B are used alternately and contain the median value of each pixel.
  unsigned char *medianMap;
  int           *medianWorkspace;

  // Map of past triggers, used to weight against pixels that trigger too often (they're probably trees...)
  int           *pastTriggerMap;

  // Buffers used while checking for triggers, to give a visual report on why triggers occur when they do
  int *triggerMap;
  int *triggerBlock;
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

char *fNameGenerate  (int utc, const char *cameraId, char *tag, const char *dirname, const char *label);
void  readFrameGroup (void *videoHandle, int nfr, int width, int height, unsigned char *buffer, int *stack1, int *stack2, unsigned char *maxMap, unsigned char *medianWorkspace, double *utc, int (*fetchFrame)(void *,unsigned char *,double *));
int   observe        (void *videoHandle, const char *cameraId, const int utcoffset, const int tstart, const int tstop, const int width, const int height, const char *label, const unsigned char *mask, int (*fetchFrame)(void *,unsigned char *,double *), int (*rewindVideo)(void *, double *));

#endif

