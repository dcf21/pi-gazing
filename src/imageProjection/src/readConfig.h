// readConfig.h
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

#ifndef READCONF_H
#define READCONF_H 1

#include "settings.h"

int readConfig(char *filename, settings *feed_s, settingsIn *si, settingsIn *s_in_default, int *nImages);

#endif

