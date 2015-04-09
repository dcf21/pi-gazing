// tools.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <unistd.h>
#include "vidtools/v4l2uvc.h"
#include "png/image.h"
#include "vidtools/color.h"
#include "utils/error.h"
#include "utils/tools.h"

#include "settings.h"

void writeMetadata(videoMetadata v)
 {
  char fname[FNAME_BUFFER];
  sprintf(fname,"%s.txt",v.filename);
  FILE *f = fopen(fname,"w");
  if (!f) return;
  fprintf(f,"cameraId %s\n",v.cameraId);
  fprintf(f,"tstart %.1f\n",v.tstart);
  fprintf(f,"tstop %.1f\n",v.tstop);
  fprintf(f,"nframe %d\n",v.nframe);
  fprintf(f,"fps %.6f\n",v.nframe / (v.tstop-v.tstart));
  fprintf(f,"flagGPS %d\n",v.flagGPS);
  fprintf(f,"lat %.6f\n",v.lat);
  fprintf(f,"lng %.6f\n",v.lng);
  fclose(f);
 }

int nearestMultiple(double in, int factor)
 {
  return (int)(round(in/factor)*factor);
 }

void frameInvert(unsigned char *buffer, int len)
 {
  int i; int imax=len/2;
#pragma omp parallel for private(i)
  for (i=0 ; i<imax ; i++)
   {
    int j=len-1-i;
    unsigned char tmp = buffer[i]; buffer[i]=buffer[j]; buffer[j]=tmp;
   }
  return;
 }

void *videoRecord(struct vdIn *videoIn, double seconds)
 {
  int i;
  const int frameSize = videoIn->width * videoIn->height*1.5;
  const int nfr       = videoIn->fps   * seconds;
  const int blen = sizeof(int) + 2*sizeof(int) + nfr*frameSize;
  void *out = malloc(blen);
  if (!out) return out;
  void *ptr = out;
  *(int *)ptr=blen;            ptr+=sizeof(int);
  *(int *)ptr=videoIn->width;  ptr+=sizeof(int);
  *(int *)ptr=videoIn->height; ptr+=sizeof(int);

  for (i=0; i<nfr; i++)
   {
    if (uvcGrab(videoIn) < 0) { printf("Error grabbing\n"); break; }
    Pyuv422to420(videoIn->framebuffer, ptr, videoIn->width, videoIn->height, VIDEO_UPSIDE_DOWN);
    ptr+=frameSize;
   }

  return out;
 }

void snapshot(struct vdIn *videoIn, int nfr, int zero, double expComp, char *fname, unsigned char *medianRaw)
 {
  int i,j;
  const int frameSize = videoIn->width * videoIn->height;
  int *tmpi = calloc(3*frameSize*sizeof(int),1);
  if (!tmpi) return;
 
  for (j=0;j<nfr;j++)
   {
    if (uvcGrab(videoIn) < 0) { printf("Error grabbing\n"); break; }
    Pyuv422torgbstack(videoIn->framebuffer, tmpi, tmpi+frameSize, tmpi+2*frameSize, videoIn->width, videoIn->height, VIDEO_UPSIDE_DOWN);
   }

  image_ptr img;
  image_alloc(&img, videoIn->width, videoIn->height);
  img.data_w = nfr;

  if (!medianRaw)
   {
    for (i=0; i<frameSize; i++) img.data_red[i]=(tmpi[i            ]-zero*nfr)*expComp;
    for (i=0; i<frameSize; i++) img.data_grn[i]=(tmpi[i+  frameSize]-zero*nfr)*expComp;
    for (i=0; i<frameSize; i++) img.data_blu[i]=(tmpi[i+2*frameSize]-zero*nfr)*expComp;
   } else {
    for (i=0; i<frameSize; i++) img.data_red[i]=(tmpi[i            ]-(zero-medianRaw[i            ])*nfr)*expComp;
    for (i=0; i<frameSize; i++) img.data_grn[i]=(tmpi[i+  frameSize]-(zero-medianRaw[i+  frameSize])*nfr)*expComp;
    for (i=0; i<frameSize; i++) img.data_blu[i]=(tmpi[i+2*frameSize]-(zero-medianRaw[i+2*frameSize])*nfr)*expComp;
   }

  image_deweight(&img);
  image_put(fname, img);
  image_dealloc(&img);

  free(tmpi);
  return;
 }

void medianCalculate(int width, int height, unsigned char *medianWorkspace, unsigned char *medianMap)
 {
  const int frameSize = width*height;
  int c;

  memset(medianMap, 255, frameSize*3);

#pragma omp parallel for private(c)
  for (c=0; c<3; c++)
   {
    int i,f;
    for (f=1; f<=255; f++)
     {
      int i,d;
      for (i=0; i<frameSize; i++)
       {
        unsigned char total=medianWorkspace[c*frameSize*256+i+(f-1)*frameSize] + medianWorkspace[c*frameSize*256+i+f*frameSize];
        if (total>=129)
         {
          total=0; medianMap[c*frameSize+i] = CLIP256(f-2);
         }
        medianWorkspace[c*frameSize*256+i+(f-1)*frameSize] = 0;
        medianWorkspace[c*frameSize*256+i+ f   *frameSize] = total;
       }
     }
    for (i=0; i<frameSize; i++) medianWorkspace[i+255*frameSize]=0;
   }
 }

int dumpFrame(int width, int height, unsigned char *buffer, char *fName)
 {
  FILE *outfile;
  int frameSize = width*height;
  if ((outfile = fopen(fName,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", fName); gnom_error(ERR_GENERAL,temp_err_string);
    return 1;
   }

  fwrite(&width ,1,sizeof(int),outfile);
  fwrite(&height,1,sizeof(int),outfile);
  fwrite(buffer ,1,frameSize  ,outfile);
  fclose(outfile);
  return 0;
 }

int dumpFrameRGB(int width, int height, unsigned char *bufferRGB, char *fName)
 {
  FILE *outfile;
  int frameSize = width*height;
  if ((outfile = fopen(fName,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW RGB image frame %s.\n", fName); gnom_error(ERR_GENERAL,temp_err_string);
    return 1;
   }

  fwrite(&width   ,1,sizeof(int),outfile);
  fwrite(&height  ,1,sizeof(int),outfile);
  fwrite(bufferRGB,1,frameSize*3,outfile);
  fclose(outfile);
  return 0;
 }

int dumpFrameRGBFromInts(int width, int height, int *bufferRGB, int nfr, int gain, char *fName)
 {
  FILE *outfile;
  int frameSize = width*height;
  unsigned char *tmpc = malloc(frameSize*3);
  if (!tmpc) { sprintf(temp_err_string, "ERROR: malloc fail in dumpFrameFromInts."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  if ((outfile = fopen(fName,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", fName); gnom_error(ERR_GENERAL,temp_err_string);
    return 1;
   }

  int i,d;
#pragma omp parallel for private(i,d)
  for (i=0; i<frameSize*3; i++) tmpc[i]=CLIP256( bufferRGB[i] * gain / nfr );

  fwrite(&width ,1,sizeof(int),outfile);
  fwrite(&height,1,sizeof(int),outfile);
  fwrite(tmpc   ,1,frameSize*3,outfile);
  fclose(outfile);
  free(tmpc);
  return 0;
 }

int dumpFrameRGBFromISub(int width, int height, int *bufferRGB, int nfr, int gain, unsigned char *buffer2, char *fName)
 {
  FILE *outfile;
  int frameSize = width*height;
  unsigned char *tmpc = malloc(frameSize*3);
  if (!tmpc) { sprintf(temp_err_string, "ERROR: malloc fail in dumpFrameFromInts."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  if ((outfile = fopen(fName,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", fName); gnom_error(ERR_GENERAL,temp_err_string);
    return 1;
   }

  int i,d;
#pragma omp parallel for private(i,d)
  for (i=0; i<frameSize*3; i++) tmpc[i]=CLIP256( (bufferRGB[i] - nfr*buffer2[i]) * gain / nfr );

  fwrite(&width ,1,sizeof(int),outfile);
  fwrite(&height,1,sizeof(int),outfile);
  fwrite(tmpc   ,1,frameSize*3,outfile);
  fclose(outfile);
  free(tmpc);
  return 0;
 }


int dumpVideo(int nfr1, int nfr2, int width, int height, unsigned char *buffer1, unsigned char *buffer2, unsigned char *buffer3, char *fName)
 {
  const int frameSize = width*height*1.5;
  const int blen = sizeof(int) + 2*sizeof(int) + (nfr1+nfr1+nfr2)*frameSize;

  FILE *outfile;
  if ((outfile = fopen(fName,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW video file %s.\n", fName); gnom_error(ERR_GENERAL,temp_err_string);
    return 1; 
   }

  fwrite(&blen  ,1,sizeof(int),outfile);
  fwrite(&width ,1,sizeof(int),outfile);
  fwrite(&height,1,sizeof(int),outfile);
  fwrite(buffer1,1,frameSize*nfr1,outfile);
  fwrite(buffer2,1,frameSize*nfr1,outfile);
  fwrite(buffer3,1,frameSize*nfr2,outfile);
  fclose(outfile);
  return 0;
 }

