// rawimg2png.c 
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "utils/tools.h"
#include "png/image.h"
#include "utils/error.h"
#include "utils/tools.h"

#include "settings.h"

int main(int argc, char *argv[])
 {
  int i;

  if (argc!=3)
   {
    sprintf(temp_err_string, "ERROR: Need to specify raw image filename on commandline, followed by output frame filename, e.g. 'rawimg2png foo.raw frame.png'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  char *rawFname = argv[1];
  char *fname = argv[2];

  char frOut[FNAME_BUFFER];
  sprintf(frOut,"%s.png",fname);

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

  image_ptr OutputImage;
  image_alloc(&OutputImage, width, height);
  OutputImage.data_w = 1;

  int x,y,l=0;
  i=0;
  for (y=0; y<height; y++) for (x=0; x<width; x++)
   {
    OutputImage.data_red[l] =
    OutputImage.data_grn[l] =
    OutputImage.data_blu[l] = vidRaw[i];
    l++; i++;
   }
  image_deweight(&OutputImage);
  image_put(frOut, OutputImage);

  sprintf(frOut,"%s.txt",fname);
  FILE *f = fopen(frOut,"w");
  if (f)
   {
    fprintf(f,"skyClarity %.2f\n", calculateSkyClarity(&OutputImage));
    fclose(f);
   }

  image_dealloc(&OutputImage);
  free(vidRaw);
  return 0;
 }

