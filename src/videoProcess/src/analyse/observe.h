// observe.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef OBSERVE_H
#define OBSERVE_H 1

char *fNameGenerate  (char *tag);
int   testTrigger    (const int width, const int height, const int *imageB, const int *imageA, const int coAddedFrames);
void  readShortBuffer(void *videoHandle, int nfr, int width, int height, unsigned char *buffer, int *stack1, int *stack2, unsigned char *maxMap, unsigned char *medianWorkspace, int (*fetchFrame)(void *,unsigned char *));
int   observe        (void *videoHandle, const int utcoffset, const int tstart, const int tstop, const int width, const int height, int (*fetchFrame)(void *,unsigned char *));

#endif

