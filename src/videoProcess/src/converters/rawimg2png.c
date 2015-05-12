// rawimg2png.c 
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "utils/tools.h"
#include "png/image.h"
#include "utils/asciidouble.h"
#include "utils/error.h"
#include "utils/lensCorrect.h"
#include "utils/tools.h"

#include "settings.h"

int main(int argc, char *argv[])
 {
  int i;

  if (argc!=6)
   {
    sprintf(temp_err_string, "ERROR: Need to specify raw image filename on commandline, followed by output frame filename, e.g. 'rawimg2png foo.raw frame.png barrelA barrelB barrelC'."); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  char *rawFname = argv[1];
  char *fname = argv[2];
  double barrelA = GetFloat(argv[3],NULL);
  double barrelB = GetFloat(argv[4],NULL);
  double barrelC = GetFloat(argv[5],NULL);

  FILE *infile;
  if ((infile = fopen(rawFname,"rb")) == NULL)
   {
    sprintf(temp_err_string, "ERROR: Cannot open output raw image file %s.\n", rawFname); gnom_fatal(__FILE__,__LINE__,temp_err_string);
   }

  int width, height;
  i=fread(&width ,sizeof(int),1,infile);
  i=fread(&height,sizeof(int),1,infile);

  const int frameSize=width*height;
  unsigned char *imgRaw = malloc(3*frameSize);
  if (imgRaw==NULL) { sprintf(temp_err_string, "ERROR: malloc fail"); gnom_fatal(__FILE__,__LINE__,temp_err_string); }
  i=fread(imgRaw,1,3*frameSize,infile);
  fclose(infile);

  image_ptr OutputImage;
  image_alloc(&OutputImage, width, height);
  OutputImage.data_w = 1;
  for (i=0; i<frameSize; i++) OutputImage.data_red[i] = imgRaw[i              ];
  for (i=0; i<frameSize; i++) OutputImage.data_grn[i] = imgRaw[i + frameSize  ];
  for (i=0; i<frameSize; i++) OutputImage.data_blu[i] = imgRaw[i + frameSize*2];
  image_deweight(&OutputImage);

  int lc;
  for (lc=0; lc<2; lc++)
   {
    char frOut[FNAME_BUFFER];
    sprintf(frOut,"%s_LC%d.png",fname,lc);

    if (lc)
     {
      image_ptr CorrectedImage = lensCorrect(&OutputImage, barrelA, barrelB, barrelC);
      image_put(frOut, CorrectedImage, ALLDATAMONO);
      image_dealloc(&CorrectedImage);
     }
    else
     {
      image_put(frOut, OutputImage, ALLDATAMONO);
     }

    sprintf(frOut,"%s_LC%d.txt",fname,lc);
    FILE *f = fopen(frOut,"w");
    if (f)
     {
      fprintf(f,"skyClarity %.2f\n", calculateSkyClarity(&OutputImage));
      fclose(f);
     }
   }

  image_dealloc(&OutputImage);
  free(imgRaw);
  return 0;
 }

