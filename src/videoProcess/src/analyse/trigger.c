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
int checkForTriggers(observeStatus *os, const int *image1, const int *image2, const int coAddedFrames, const char *label)
 {
  int x,y,d;
  int output=0;

  const int margin=10; // Ignore pixels within this distance of the edge
  const int Npixels=30; // To trigger this number of pixels connected together must have brightened
  const int radius=8; // Pixel must be brighter than test pixels this distance away
  const int threshold=12*coAddedFrames; // Pixel must have brightened by at least this amount.
  unsigned char *triggerR = os->triggerRGB;
  unsigned char *triggerG = os->triggerRGB + os->frameSize*1; // These arrays are used to produce diagnostic images when the camera triggers
  unsigned char *triggerB = os->triggerRGB + os->frameSize*2;
  memset(os->triggerMap, 0, os->frameSize*sizeof(int));
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
     triggerR[o] = CLIP256( (image1[o]-image2[o])*64/threshold ); // RED channel - difference between images B and A
     triggerG[o] = CLIP256( os->pastTriggerMap[o] * 256 / (2*os->pastTriggerMapAverage) ); // GRN channel - map of pixels which are excluded for triggering too often
     triggerB[o] = 0;
     if (os->mask[o] && (image1[o]-image2[o]>threshold)) // Search for pixels which have brightened by more than threshold since past image
      {
       int i,j,c=0; // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels. This pixel must be brighter than 6/9 of these pixels were
       for (i=-1;i<=1;i++) for (j=-1;j<=1;j++) if (image1[o]-image2[o+(j+i*os->width)*radius]>threshold) c++;
       if (c>7)
        {
         int i,j,c=0; // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels. This pixel must be brighter than 6/9 of these pixels were
         for (i=-1;i<=1;i++) for (j=-1;j<=1;j++) if (image1[o]-image1[o+(j+i*os->width)*radius]>threshold) c++;
         if (c>6)
          {
           // Put triggering pixel on map. Wait till be have <Npixels> connected pixels.
           os->pastTriggerMap[o]++;
           triggerB[o] = 128;
           int blockId=0;
           if (os->triggerMap[o-1      ]) { if (!blockId) { blockId=os->triggerMap[o-1      ]; } else { triggerBlocksMerge(os->triggerBlock, os->triggerMap+(y-1)*width, width*2, os->triggerMap[o-1      ], blockId); } }
           if (os->triggerMap[o+1-width]) { if (!blockId) { blockId=os->triggerMap[o+1-width]; } else { triggerBlocksMerge(os->triggerBlock, os->triggerMap+(y-1)*width, width*2, os->triggerMap[o+1-width], blockId); } }
           if (os->triggerMap[o-width  ]) { if (!blockId) { blockId=os->triggerMap[o-width  ]; } else { triggerBlocksMerge(os->triggerBlock, os->triggerMap+(y-1)*width, width*2, os->triggerMap[o-width  ], blockId); } }
           if (os->triggerMap[o-1-width]) { if (!blockId) { blockId=os->triggerMap[o-1-width]; } else { triggerBlocksMerge(os->triggerBlock, os->triggerMap+(y-1)*width, width*2, os->triggerMap[o-1-width], blockId); } }
           if (blockId==0               ) blockId=blockNum++;

           if (pastTriggerMap[o]<2*pastTriggerMapAverage) os->triggerBlock[blockId]++;
           os->triggerMap[o] = blockId;
           if (os->triggerBlock[blockId]>Npixels)
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
             registerTriggerStart(os, image1, image2, coAddedFrames, label);
            }
          }
        }
      }
    }

  os->pastTriggerMapAverage = pastTriggerMapAverageNew / nPixelsWithinMask + 1;
  return output;
 }

