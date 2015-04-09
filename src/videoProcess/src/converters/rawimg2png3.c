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
  unsigned char *vidRawR = malloc(frameSize);
  unsigned char *vidRawG = malloc(frameSize);
  unsigned char *vidRawB = malloc(frameSize);
  if ( (vidRawR==NULL) || (vidRawG==NULL) || (vidRawB==NULL) ) { sprintf(temp_err_string, "ERROR: malloc fail"); gnom_fatal(__FILE__,__LINE__,temp_err_string); }
  i=fread(vidRawR,1,frameSize,infile);
  i=fread(vidRawG,1,frameSize,infile);
  i=fread(vidRawB,1,frameSize,infile);
  fclose(infile);

  image_ptr out;
  image_alloc(&out,width,height);

  int code = 0;

  for (i=0; i<3; i++)
   {
    int j;
    if (code) break;

    unsigned char *vidRaw = NULL;
    if      (i==0) vidRaw=vidRawR;
    else if (i==1) vidRaw=vidRawG;
    else           vidRaw=vidRawB;

    for (j=0; j<frameSize; j++) out.data_red[j]=vidRaw[j];
    for (j=0; j<frameSize; j++) out.data_grn[j]=vidRaw[j];
    for (j=0; j<frameSize; j++) out.data_blu[j]=vidRaw[j];

    char frOut[FNAME_BUFFER];
    sprintf(frOut,"%s.%d.png",fname,i);
    code = image_put(frOut,out);
   }

  free(vidRawR); free(vidRawG); free(vidRawB);
  return code;
 }

