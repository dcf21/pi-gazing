// rawimg2jpg.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "utils/tools.h"
#include "jpeg/jpeg.h"
#include "utils/error.h"

#include "settings.h"

int main(int argc, char *argv[])
 {
  int i;

  if (argc!=3)
   {
    sprintf(temp_err_string, "ERROR: Need to specify raw image filename on commandline, followed by output frame filename, e.g. 'rawimg2jpg foo.raw frame.jpg'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  char *rawFname = argv[1];
  char *frOut = argv[2];

  FILE *infile;
  if ((infile = fopen(rawFname,"rb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output raw image file %s.\n", rawFname); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  int width, height;
  i=fread(&width ,sizeof(int),1,infile);
  i=fread(&height,sizeof(int),1,infile);

  const int frameSize=width*height;
  unsigned char *vidRaw = malloc(frameSize);
  if (vidRaw==NULL) { sprintf(temp_err_string, "ERROR: malloc fail"); gnom_fatal(__FILE__,__LINE__,temp_err_string); }
  i=fread(vidRaw,1,frameSize,infile);
  fclose(infile);

  const int nfr=1;

  image_ptr OutputImage;
  jpeg_alloc(&OutputImage, width, height);
  for (i=0; i<nfr; i++)
   {
    int x,y,l=0;
    int p=0;
    for (y=0; y<height; y++) for (x=0; x<width; x++)
     {
      OutputImage.data_red[l] =
      OutputImage.data_grn[l] =
      OutputImage.data_blu[l] = vidRaw[p];
      OutputImage.data_w  [l] = 1;
      l++; p++;
     }
    jpeg_deweight(&OutputImage);
    jpeg_put(frOut, OutputImage);
   }
  jpeg_dealloc(&OutputImage);
  free(vidRaw);
  return 0;
 }

