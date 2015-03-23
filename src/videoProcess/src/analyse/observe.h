// observe.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef OBSERVE_H
#define OBSERVE_H 1

char *fNameGenerate  (int utc, char *tag, const char *dirname, const char *label);
int   testTrigger    (const double utc, const int width, const int height, const int *imageB, const int *imageA, const int coAddedFrames, const char *label);
void  readShortBuffer(void *videoHandle, int nfr, int width, int height, unsigned char *buffer, int *stack1, int *stack2, unsigned char *maxMap, unsigned char *medianWorkspace, double *utc, int (*fetchFrame)(void *,unsigned char *,double *));
int   observe        (void *videoHandle, const int utcoffset, const int tstart, const int tstop, const int width, const int height, const char *label, int (*fetchFrame)(void *,unsigned char *, double *), int (*rewindVideo)(void *, double *));

#endif

