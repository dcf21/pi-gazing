// barrel.c
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

#include <gsl/gsl_errno.h>
#include <gsl/gsl_math.h>

#include "asciidouble.h"
#include "error.h"
#include "gnomonic.h"
#include "imageProcess.h"
#include "image.h"
#include "readConfig.h"
#include "settings.h"
#include "str_constants.h"
#include "backgroundSub.h"

int main(int argc, char **argv)
 {
  char       help_string[LSTR_LENGTH], version_string[FNAME_LENGTH], version_string_underline[FNAME_LENGTH];
  char      *filename[3];
  int        i, HaveFilename=0;
  settings   s_model,  *feed_s = &s_model;
  settingsIn s_in_default;
  image_ptr  OutputImage;

  // Initialise sub-modules
  if (DEBUG) gnom_log("Initialising stacker.");
  DefaultSettings(feed_s, &s_in_default);

  // Turn off GSL's automatic error handler
  gsl_set_error_handler_off();

  // Make help and version strings
  sprintf(version_string, "Barrel Distortion Corrector %s", VERSION);

  sprintf(help_string   , "Barrel Distortion Corrector %s\n\
%s\n\
\n\
Usage: barrel.bin <filename> <camera model> <output filename>\n\
  -h, --help:       Display this help.\n\
  -v, --version:    Display version number.", VERSION, StrUnderline(version_string, version_string_underline));

  // Scan commandline options for any switches
  HaveFilename=0;
  for (i=1; i<argc; i++)
   {
    if (strlen(argv[i])==0) continue;
    if (argv[i][0]!='-')
     {
      if (HaveFilename > 2)
       {
        sprintf(temp_err_string, "barrel.bin should be provided with three filenames on the command line to act upon. Too many filenames appear to have been supplied. Type 'barrel.bin -help' for a list of available commandline options.");
        gnom_error(ERR_GENERAL, temp_err_string);
        return 1;
       }
      filename[HaveFilename] = argv[i];
      HaveFilename++;
      continue;
     }
    if      ((strcmp(argv[i], "-v")==0) || (strcmp(argv[i], "-version")==0) || (strcmp(argv[i], "--version")==0))
     {
      gnom_report(version_string);
      return 0;
     }
    else if ((strcmp(argv[i], "-h")==0) || (strcmp(argv[i], "-help")==0) || (strcmp(argv[i], "--help")==0))
     {
      gnom_report(help_string);
      return 0;
     }
    else
    {
     sprintf(temp_err_string, "Received switch '%s' which was not recognised.\nType 'stack.bin -help' for a list of available commandline options.", argv[i]);
     gnom_error(ERR_GENERAL, temp_err_string);
     return 1;
    }
   }

  // Check that we have been provided with exactly one filename on the command line
  if (HaveFilename < 3)
   {
    sprintf(temp_err_string, "barrel.bin should be provided with three filenames on the command line to act upon. Type 'barrel.bin -help' for a list of available commandline options.");
    gnom_error(ERR_GENERAL, temp_err_string);
    return 1;
   }

  // Read camera description
  {
   char line[LSTR_LENGTH]; FILE *inc; char *cp;

   if ((inc = fopen(filename[1],"r"))==NULL) { sprintf(temp_err_string, "Stacker could not open input camera file '%s'.", filename[1]); gnom_error(ERR_GENERAL, temp_err_string); return 1; }
   file_readline(inc, line, LSTR_LENGTH);
   StrStrip(line,line);
   cp=line;
   if (!ValidFloat(cp,NULL)) gnom_fatal(__FILE__,__LINE__,"Could not read barrel_a");
   s_in_default.barrel_a = GetFloat(cp,NULL);
   //sprintf(temp_err_string, "barrel_a = %f", s_in_default.barrel_a); gnom_report(temp_err_string);
   cp=NextWord(cp);
   if (!ValidFloat(cp,NULL)) gnom_fatal(__FILE__,__LINE__,"Could not read barrel_b");
   s_in_default.barrel_b = GetFloat(cp,NULL);
   //sprintf(temp_err_string, "barrel_b = %f", s_in_default.barrel_b); gnom_report(temp_err_string);
   cp=NextWord(cp);
   if (!ValidFloat(cp,NULL)) gnom_fatal(__FILE__,__LINE__,"Could not read barrel_c");
   s_in_default.barrel_c = GetFloat(cp,NULL);
   //sprintf(temp_err_string, "barrel_c = %f", s_in_default.barrel_c); gnom_report(temp_err_string);
   cp=NextWord(cp);
  }


   {
    image_ptr InputImage;

    // Read image
    strcpy(s_in_default.InFName, filename[0]);
    InputImage = image_get(filename[0]);
    if (InputImage.data_red==NULL) gnom_fatal(__FILE__,__LINE__,"Could not read input image file");

    feed_s->mode   = MODE_GNOMONIC;
    feed_s->XSize  = InputImage.xsize;
    feed_s->YSize  = InputImage.ysize;
    feed_s->YScale*= ((double)InputImage.ysize)/InputImage.xsize; // Make sure that we treat image with correct aspect ratio
    strcpy(feed_s->OutFName, filename[2]);
    s_in_default.InXSize   = InputImage.xsize;
    s_in_default.InYSize   = InputImage.ysize;
    s_in_default.InYScale *= ((double)InputImage.ysize)/InputImage.xsize;

    // Malloc output image
    image_alloc(&OutputImage, feed_s->XSize, feed_s->YSize);

    // Process image
    StackImage(InputImage, OutputImage, NULL, NULL, feed_s, &s_in_default);
    
    // Free image
    image_dealloc(&InputImage);
   }

  // Write image
  image_deweight(&OutputImage);
  image_put(feed_s->OutFName, OutputImage);
  image_dealloc(&OutputImage);

  if (DEBUG) gnom_log("Terminating normally.");
  return 0;
 }

