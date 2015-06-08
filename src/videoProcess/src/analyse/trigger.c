// trigger.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include "str_constants.h"
#include "analyse/observe.h"
#include "analyse/trigger.h"
#include "utils/asciidouble.h"
#include "utils/tools.h"
#include "utils/error.h"
#include "utils/JulianDate.h"
#include "vidtools/color.h"

#include "settings.h"

// Used by testTrigger. When blocks idOld and idNew are determined to be connected, their pixels counts are added together.
inline void triggerBlocksMerge(observeStatus *os, int idOld, int idNew)
 {
  while (os->triggerBlock_redirect[idOld]>0) idOld=os->triggerBlock_redirect[idOld];
  while (os->triggerBlock_redirect[idNew]>0) idNew=os->triggerBlock_redirect[idNew];
  if (idOld==idNew) return;
  os->triggerBlock_N   [idNew] += os->triggerBlock_N   [idOld];
  os->triggerBlock_sumx[idNew] += os->triggerBlock_sumx[idOld];
  os->triggerBlock_sumy[idNew] += os->triggerBlock_sumy[idOld];
  os->triggerBlock_suml[idNew] += os->triggerBlock_suml[idOld];
  os->triggerBlock_N   [idOld]     = 0;
  os->triggerBlock_redirect[idOld] = idNew;
  return;
 }

// Test stacked images B and A, to see if pixels have brightened in B versus A. Image arrays contain the sum of <coAddedFrames> frames.
int checkForTriggers(observeStatus *os, const int *image1, const int *image2, const int coAddedFrames)
 {
  int y;
  int output=0;

  const int margin=10; // Ignore pixels within this distance of the edge
  const int threshold_blockSize=10; // To trigger this number of pixels connected together must have brightened
  const int radius=8; // Pixel must be brighter than test pixels this distance away
        int threshold=1.5*os->noiseLevel*sqrt(coAddedFrames); // Pixel must have brightened by at least N standard deviations
  if (threshold<1) threshold=1;
  unsigned char *triggerR = os->triggerRGB;
  unsigned char *triggerG = os->triggerRGB + os->frameSize*1; // These arrays are used to produce diagnostic images when the camera triggers
  unsigned char *triggerB = os->triggerRGB + os->frameSize*2;
  memset(os->triggerMap, 0, os->frameSize*sizeof(int));
  int Nblocks = 0;

  static unsigned long long pastTriggerMapAverage = 1;
  unsigned int              nPixelsWithinMask = 1;
  unsigned long long        pastTriggerMapAverageNew = 0;

#pragma omp parallel for private(y)
  for (y=margin; y<os->height-margin; y++)
   {
    int x,d;
    int triggerMap_linesum=0, nPixelsWithinMask_linesum=0;
    for (x=margin;x<os->width-margin; x++)
     {
      const int o=x+y*os->width;
      triggerMap_linesum += os->pastTriggerMap[o];
      if (os->mask[o]) nPixelsWithinMask_linesum++;
      triggerR[o] = CLIP256( (image1[o]-image2[o])*64/threshold ); // RED channel - difference between images B and A
      triggerG[o] = CLIP256( os->pastTriggerMap[o] * 256 / (2*pastTriggerMapAverage) ); // GRN channel - map of pixels which are excluded for triggering too often
      triggerB[o] = 0;
      if (os->mask[o] && (image1[o]-image2[o]>threshold)) // Search for pixels which have brightened by more than threshold since past image
       {
        int i,j,c=0; // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels. This pixel must be brighter than 6/9 of these pixels were
        for (i=-1;i<=1;i++) for (j=-1;j<=1;j++) if (image1[o]-image2[o+(j+i*os->width)*radius]>threshold) c++;
        if (c>7)
         {
          int i,j,c=0; // Make a 3x3 grid of pixels of pixels at a spacing of radius pixels. This pixel must be brighter than 6/9 of these pixels were
          for (i=-1;i<=1;i++) for (j=-1;j<=1;j++) if (image1[o]-image1[o+(j+i*os->width)*radius]>threshold) c++;
#pragma omp critical (add_trigger)
          if (c>6)
           {
            // Put triggering pixel on map. Wait till be have <Npixels> connected pixels.
            os->pastTriggerMap[o]++;
            triggerB[o] = 128;
            int blockId=0;
            if (os->triggerMap[o-1          ]) { if (!blockId) { blockId=os->triggerMap[o-1          ]; } else { triggerBlocksMerge(os, os->triggerMap[o-1          ], blockId); } }
            if (os->triggerMap[o+1-os->width]) { if (!blockId) { blockId=os->triggerMap[o+1-os->width]; } else { triggerBlocksMerge(os, os->triggerMap[o+1-os->width], blockId); } }
            if (os->triggerMap[o-os->width  ]) { if (!blockId) { blockId=os->triggerMap[o-os->width  ]; } else { triggerBlocksMerge(os, os->triggerMap[o-os->width  ], blockId); } }
            if (os->triggerMap[o-1-os->width]) { if (!blockId) { blockId=os->triggerMap[o-1-os->width]; } else { triggerBlocksMerge(os, os->triggerMap[o-1-os->width], blockId); } }
            while (blockId && (os->triggerBlock_redirect[blockId]>0)) blockId=os->triggerBlock_redirect[blockId];
            if (blockId==0)
             {
              if (Nblocks<MAX_TRIGGER_BLOCKS-1) Nblocks++;
              blockId=Nblocks;
              os->triggerBlock_N[blockId]=0; os->triggerBlock_sumx[blockId]=0; os->triggerBlock_sumy[blockId]=0; os->triggerBlock_suml[blockId]=0;
              os->triggerBlock_redirect[blockId]=0;
             }

            if (os->pastTriggerMap[o]<2*pastTriggerMapAverage) os->triggerBlock_N[blockId]++; 
            os->triggerBlock_sumx[blockId] += x;
            os->triggerBlock_sumy[blockId] += y;
            os->triggerBlock_suml[blockId] += image1[o]-image2[o];
            os->triggerMap       [o]        = blockId;
           }
         }
       }
     }
#pragma omp critical (trigger_cleanup)
     {
      pastTriggerMapAverageNew += triggerMap_linesum;
      nPixelsWithinMask        += nPixelsWithinMask_linesum;
     }
   }

  int i;
  for (i=1; i<=Nblocks; i++)
   {
    if (i==MAX_TRIGGER_BLOCKS-1) break;
    if (os->triggerBlock_N[i]>threshold_blockSize)
     {
      const int n = os->triggerBlock_N[i];
      const int x = (os->triggerBlock_sumx[i] / n); // average x position of moving object
      const int y = (os->triggerBlock_sumy[i] / n); // average y position of moving object
      const int l = os->triggerBlock_suml[i]; // total excess brightness
      const int o=x+y*os->width;
      triggerB[o]=255;
      output=1; // We have triggered!
      registerTrigger(os, x, y, n, l, image1, image2, coAddedFrames);
     }
   }
  pastTriggerMapAverage = pastTriggerMapAverageNew / nPixelsWithinMask + 1;
  return output;
 }

