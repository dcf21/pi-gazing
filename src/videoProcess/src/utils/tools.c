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
  fprintf(f,"fpsTarget %.6f\n",v.fps);
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
  const int frameSize = videoIn->width * videoIn->height * 3/2;
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
  image_put(fname, img, ALLDATAMONO);
  image_dealloc(&img);

  free(tmpi);
  return;
 }

double calculateSkyClarity(image_ptr *img)
 {
  int       i,j,score=0;
  const int gridsize = 8;
  const int stride   = img->xsize;
  for (i=1;i<gridsize-1;i++) for (j=1;j<gridsize-1;j++)
   {
    const int xmin = img->xsize* j   /gridsize;
    const int ymin = img->ysize* i   /gridsize;
    const int xmax = img->xsize*(j+1)/gridsize;
    const int ymax = img->ysize*(i+1)/gridsize;
    int x,y,count=0;
    for (y=ymin;y<ymax;y++) for (x=xmin;x<xmax;x++)
     {
      if ( (img->data_grn[y*stride+x] > img->data_grn[(y  )*stride+(x+6)]+16) &&
           (img->data_grn[y*stride+x] > img->data_grn[(y+6)*stride+(x+6)]+16) &&
           (img->data_grn[y*stride+x] > img->data_grn[(y+6)*stride+(x  )]+16) &&
           (img->data_grn[y*stride+x] > img->data_grn[(y+6)*stride+(x-6)]+16) &&
           (img->data_grn[y*stride+x] > img->data_grn[(y  )*stride+(x-6)]+16) &&
           (img->data_grn[y*stride+x] > img->data_grn[(y-6)*stride+(x-6)]+16) &&
           (img->data_grn[y*stride+x] > img->data_grn[(y-6)*stride+(x  )]+16) &&
           (img->data_grn[y*stride+x] > img->data_grn[(y-6)*stride+(x+6)]+16) ) count++;
     }
    if (count>2) score++;
   }
  return (100. * score) / pow(gridsize-1,2);
 }

void medianCalculate(const int width, const int height, const int medianMapResolution, int *medianWorkspace, unsigned char *medianMap)
 {
  const int frameSize = width*height;
  int c;

  const int mapSize = medianMapResolution*medianMapResolution;
  unsigned char *tmpMap = calloc(1,3*mapSize);

  // Find the median value of each cell in the median grid
  for (c=0; c<3; c++)
   {
    int i;
#pragma omp parallel for private(i)
    for (i=0; i<mapSize; i++)
     {
      int f,d;
      const int offset = (c*mapSize+i)*256;
      int NcoaddedPixels = 0;
      for (f=0; f<256; f++) NcoaddedPixels += medianWorkspace[offset+f];
      int total = 0;
      for (f=0; f<256; f++)
       {
        total += medianWorkspace[offset+f];
        if (total>=NcoaddedPixels/2) break;
       }
      tmpMap[c*mapSize+i] = CLIP256(f-2);
     }
   }
  memset(medianWorkspace, 0, mapSize*3*256*sizeof(int));

  // Linearly interpolate coarse median map across the whole image
  for (c=0; c<3; c++)
   {
    int y;
#pragma omp parallel for private(y)
    for (y=0; y<height; y++)
     {
      int d,x;
      double ym = medianMapResolution * ((double)y) / height - 0.5;
      if (ym<0) ym=0; if (ym>medianMapResolution-1) ym=medianMapResolution-1;
      int    y0 = floor(ym);
      int    y1w= CLIP256( 255*(ym-y0) );
      int    y0w= 255-y1w;
      int    y1 = (y0==medianMapResolution-1) ? y0 : y0+1;
      for (x=0; x<width; x++)
       {
        double xm = medianMapResolution * ((double)x) / width - 0.5;
        if (xm<0) xm=0; if (xm>medianMapResolution-1) xm=medianMapResolution-1;
        int    x0 = floor(xm);
        int    x1w= CLIP256( 255*(xm-x0) );
        int    x0w= 255-x1w;
        int    x1 = (x0==medianMapResolution-1) ? x0 : x0+1;
        int    pixVal = ( x0w*y0w*tmpMap[c*mapSize + y0*medianMapResolution + x0] +
                          x1w*y0w*tmpMap[c*mapSize + y0*medianMapResolution + x1] +
                          x0w*y1w*tmpMap[c*mapSize + y1*medianMapResolution + x0] +
                          x1w*y1w*tmpMap[c*mapSize + y1*medianMapResolution + x1]   ) >> 16;
        medianMap[c*frameSize + y*width+x] = CLIP256(pixVal);
       }
     }
   }
  free(tmpMap);
  return;
 }

int dumpFrame(int width, int height, unsigned char *buffer, char *fName)
 {
  FILE *outfile;
  const int frameSize = width*height;
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

