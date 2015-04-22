// rawimg2png3.c 
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "utils/tools.h"
#include "png/image.h"
#include "utils/error.h"
#include "png.h"
#include "settings.h"

int main(int argc, char *argv[])
 {
  int i;

  if (argc!=3)
   {
    sprintf(temp_err_string, "ERROR: Need to specify raw image filename on commandline, followed by output frame filename, e.g. 'rawimg2png3 foo.raw frame.png'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  char *rawFname = argv[1];
  char *fname = argv[2];

  FILE *infile;
  if ((infile = fopen(rawFname,"rb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output raw image file %s.\n", rawFname); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  int width, height;
  i=fread(&width ,sizeof(int),1,infile);
  i=fread(&height,sizeof(int),1,infile);

  const int frameSize=width*height;
  unsigned char *imgRawR = malloc(frameSize);
  unsigned char *imgRawG = malloc(frameSize);
  unsigned char *imgRawB = malloc(frameSize);
  if ( (imgRawR==NULL) || (imgRawG==NULL) || (imgRawB==NULL) ) { sprintf(temp_err_string, "ERROR: malloc fail"); gnom_fatal(__FILE__,__LINE__,temp_err_string); }
  i=fread(imgRawR,1,frameSize,infile);
  i=fread(imgRawG,1,frameSize,infile);
  i=fread(imgRawB,1,frameSize,infile);
  fclose(infile);

  image_ptr out;
  image_alloc(&out,width,height);

  int code = 0;

  for (i=0; i<3; i++)
   {
    int j;
    if (code) break;

    unsigned char *imgRaw = NULL;
    if      (i==0) imgRaw=imgRawR;
    else if (i==1) imgRaw=imgRawG;
    else           imgRaw=imgRawB;

    for (j=0; j<frameSize; j++) out.data_red[j]=imgRaw[j];
    for (j=0; j<frameSize; j++) out.data_grn[j]=imgRaw[j];
    for (j=0; j<frameSize; j++) out.data_blu[j]=imgRaw[j];

    char frOut[FNAME_BUFFER];
    sprintf(frOut,"%s.%d.png",fname,i);
    code = image_put(frOut,out);
   }

  free(imgRawR); free(imgRawG); free(imgRawB);
  return code;
 }
