// readConfig.h
// $Id: readConfig.h 1131 2014-11-18 01:34:26Z pyxplot $

#ifndef READCONF_H
#define READCONF_H 1

#include "settings.h"

int readConfig(char *filename, settings *feed_s, settingsIn *si, settingsIn *s_in_default, int *nImages);

#endif

