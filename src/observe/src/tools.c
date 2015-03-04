// tools.c
// $Id: tools.c 1199 2015-02-24 00:16:12Z pyxplot $

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "v4l2uvc.h"
#include "jpeg.h"
#include "color.h"
#include "error.h"
#include "tools.h"

#include "settings.h"

void *videoRecord(struct vdIn *videoIn, double seconds)
 {
  int i;
  const int frameSize = videoIn->width * videoIn->height;
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
    Pyuv422toMono(videoIn->framebuffer, ptr, videoIn->width, videoIn->height);
    ptr+=frameSize;
   }

  return out;
 }

void snapshot(struct vdIn *videoIn, int nfr, int zero, double expComp, char *fname, unsigned char *medianRaw)
 {
  int i,j,p;
  const int frameSize = videoIn->width * videoIn->height;
  unsigned char *tmpc = malloc(frameSize);
  if (!tmpc) return;
  int *tmpi = malloc(frameSize*sizeof(int));
  if (!tmpi) return;
  for (i=0; i<frameSize; i++) tmpi[i]=0;
 
  for (j=0;j<nfr;j++)
   {
    if (uvcGrab(videoIn) < 0) { printf("Error grabbing\n"); break; }
    Pyuv422toMono(videoIn->framebuffer, tmpc, videoIn->width, videoIn->height);
    for (i=0; i<frameSize; i++) tmpi[i]+=tmpc[i];
   }

  image_ptr img;
  jpeg_alloc(&img, videoIn->width, videoIn->height);
  for (i=0; i<frameSize; i++) img.data_w  [i]=nfr;

  // Invert order of pixels in tmpi and medianRaw because camera is upside down
  const int pinit = VIDEO_UPSIDE_DOWN ? (frameSize-1) : 0;
  const int pstep = VIDEO_UPSIDE_DOWN ? -1            : 1;
  if (!medianRaw)
   {
    for (i=0, p=pinit; i<frameSize; i++,p+=pstep) img.data_red[i]=(tmpi[p]-zero*nfr)*expComp;
    for (i=0, p=pinit; i<frameSize; i++,p+=pstep) img.data_grn[i]=(tmpi[p]-zero*nfr)*expComp;
    for (i=0, p=pinit; i<frameSize; i++,p+=pstep) img.data_blu[i]=(tmpi[p]-zero*nfr)*expComp;
   } else {
    for (i=0, p=pinit; i<frameSize; i++,p+=pstep) img.data_red[i]=(tmpi[p]-(zero-medianRaw[p])*nfr)*expComp;
    for (i=0, p=pinit; i<frameSize; i++,p+=pstep) img.data_grn[i]=(tmpi[p]-(zero-medianRaw[p])*nfr)*expComp;
    for (i=0, p=pinit; i<frameSize; i++,p+=pstep) img.data_blu[i]=(tmpi[p]-(zero-medianRaw[p])*nfr)*expComp;
   }

  jpeg_deweight(&img);
  jpeg_put(fname, img);
  jpeg_dealloc(&img);

  free(tmpc); free(tmpi);
  return;
 }

void medianCalculate(int width, int height, unsigned char *medianWorkspace, unsigned char *medianMap)
 {
  int frameSize = width*height;
  int f,i;

  for (i=0; i<frameSize; i++) medianMap[i]=255;

  for (f=1; f<=255; f++)
   {
    int i,d;
    for (i=0; i<frameSize; i++)
     {
      unsigned char total=medianWorkspace[i+(f-1)*frameSize] + medianWorkspace[i+f*frameSize];
      if (total>=129)
       {
        total=0; medianMap[i] = CLIP256(f-2);
       }
      medianWorkspace[i+(f-1)*frameSize] = 0;
      medianWorkspace[i+ f   *frameSize] = total;
     }
   }
  for (i=0; i<frameSize; i++) medianWorkspace[i+255*frameSize]=0;
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

int dumpFrameRGB(int width, int height, unsigned char *bufferR, unsigned char *bufferG, unsigned char *bufferB, char *fName)
 {
  FILE *outfile;
  int frameSize = width*height;
  if ((outfile = fopen(fName,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW RGB image frame %s.\n", fName); gnom_error(ERR_GENERAL,temp_err_string);
    return 1;
   }

  fwrite(&width ,1,sizeof(int),outfile);
  fwrite(&height,1,sizeof(int),outfile);
  fwrite(bufferR,1,frameSize  ,outfile);
  fwrite(bufferG,1,frameSize  ,outfile);
  fwrite(bufferB,1,frameSize  ,outfile);
  fclose(outfile);
  return 0;
 }

int dumpFrameFromInts(int width, int height, int *buffer, int nfr, int gain, char *fName)
 {
  FILE *outfile;
  int frameSize = width*height;
  unsigned char *tmpc = malloc(frameSize);
  if (!tmpc) { sprintf(temp_err_string, "ERROR: malloc fail in dumpFrameFromInts."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  if ((outfile = fopen(fName,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", fName); gnom_error(ERR_GENERAL,temp_err_string);
    return 1;
   }

  int i,d; for (i=0; i<frameSize; i++) tmpc[i]=CLIP256( buffer[i] * gain / nfr );

  fwrite(&width ,1,sizeof(int),outfile);
  fwrite(&height,1,sizeof(int),outfile);
  fwrite(tmpc   ,1,frameSize  ,outfile);
  fclose(outfile);
  free(tmpc);
  return 0;
 }

int   dumpFrameFromISub(int width, int height, int *buffer, int nfr, int gain, unsigned char *buffer2, char *fName)
 {
  FILE *outfile;
  int frameSize = width*height;
  unsigned char *tmpc = malloc(frameSize);
  if (!tmpc) { sprintf(temp_err_string, "ERROR: malloc fail in dumpFrameFromInts."); gnom_fatal(__FILE__,__LINE__,temp_err_string); }

  if ((outfile = fopen(fName,"wb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output RAW image frame %s.\n", fName); gnom_error(ERR_GENERAL,temp_err_string);
    return 1;
   }

  int i,d; for (i=0; i<frameSize; i++) tmpc[i]=CLIP256( (buffer[i] - nfr*buffer2[i]) * gain / nfr );

  fwrite(&width ,1,sizeof(int),outfile);
  fwrite(&height,1,sizeof(int),outfile);
  fwrite(tmpc   ,1,frameSize  ,outfile);
  fclose(outfile);
  free(tmpc);
  return 0;
 }


int dumpVideo(int nfr1, int nfr2, int width, int height, unsigned char *buffer1, unsigned char *buffer2, unsigned char *buffer3, char *fName)
 {
  const int frameSize = width*height;
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

