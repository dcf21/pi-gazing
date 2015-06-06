// trigger.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef TRIGGER_H
#define TRIGGER_H 1

int   checkForTriggers(const double utc, const int width, const int height, const int *imageB, const int *imageA, const unsigned char *mask, const int coAddedFrames, const char *label);

#endif

