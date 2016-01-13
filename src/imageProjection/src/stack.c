// stack.c
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

#define IMAGES_MAX 1024

int main(int argc, char **argv)
 {
  char       help_string[LSTR_LENGTH], version_string[FNAME_LENGTH], version_string_underline[FNAME_LENGTH];
  char      *filename=NULL;
  int        i, HaveFilename=0;
  settings   s_model,  *feed_s = &s_model;
  settingsIn s_in[IMAGES_MAX], s_in_default;
  int        nImages=0;
  image_ptr  OutputImage;

  // Initialise sub-modules
  if (DEBUG) gnom_log("Initialising stacker.");
  DefaultSettings(feed_s, &s_in_default);

  // Turn off GSL's automatic error handler
  gsl_set_error_handler_off();

  // Make help and version strings
  sprintf(version_string, "Stacker %s", VERSION);

  sprintf(help_string   , "Stacker %s\n\
%s\n\
\n\
Usage: stack.bin <filename>\n\
  -h, --help:       Display this help.\n\
  -v, --version:    Display version number.", VERSION, StrUnderline(version_string, version_string_underline));

  // Scan commandline options for any switches
  HaveFilename=0;
  for (i=1; i<argc; i++)
   {
    if (strlen(argv[i])==0) continue;
    if (argv[i][0]!='-')
     {
      HaveFilename++; filename = argv[i];
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
  if (HaveFilename < 1)
   {
    sprintf(temp_err_string, "stack.bin should be provided with a filename on the command line to act upon. Type 'stack.bin -help' for a list of available commandline options.");
    gnom_error(ERR_GENERAL, temp_err_string);
    return 1;
   }
  else if (HaveFilename > 1)
   {
    sprintf(temp_err_string, "stack.bin should be provided with only one filename on the command line to act upon. Multiple filenames appear to have been supplied. Type 'stack.bin -help' for a list of available commandline options.");
    gnom_error(ERR_GENERAL, temp_err_string);
    return 1;
   }

  // Go through command script line by line
  if (readConfig(filename, feed_s, s_in, &s_in_default, &nImages)) return 1;

  // Malloc output image
  image_alloc(&OutputImage, feed_s->XSize, feed_s->YSize);

  // Straightforward stacking (no cloud masking)
  for (i=0; i<nImages; i++)
   {
    image_ptr InputImage;

    // Read image
    InputImage = image_get(s_in[i].InFName);
    if (InputImage.data_red==NULL) gnom_fatal(__FILE__,__LINE__,"Could not read input image file");
    if (feed_s->cloudMask==0) backgroundSubtract(InputImage, s_in+i); // Do not do background subtraction if we're doing cloud masking

    // Process image
    StackImage(InputImage, OutputImage, NULL, NULL, feed_s, s_in+i);

    // Free image
    image_dealloc(&InputImage);
   }

  image_deweight(&OutputImage);

  // If requested, do stacking again with cloud masking
  if (feed_s->cloudMask!=0)
   {
    image_ptr CloudMaskAvg = OutputImage;
    image_alloc(&OutputImage, feed_s->XSize, feed_s->YSize);

    // Stacking with mask
    for (i=0; i<nImages; i++)
     {
      image_ptr InputImage, CloudMaskThis;

      // Read image
      InputImage = image_get(s_in[i].InFName);
      if (InputImage.data_red==NULL) gnom_fatal(__FILE__,__LINE__,"Could not read input image file");
      image_cp(&InputImage,&CloudMaskThis);
      backgroundSubtract(InputImage, s_in+i);

      // Process image
      StackImage(InputImage, OutputImage, &CloudMaskAvg, &CloudMaskThis, feed_s, s_in+i);

      // Free image
      image_dealloc(&InputImage);
      image_dealloc(&CloudMaskThis);
     }

    image_deweight(&OutputImage);
    image_dealloc(&CloudMaskAvg);
   }

  // Write image
  image_put(feed_s->OutFName, OutputImage);
  image_dealloc(&OutputImage);

  if (DEBUG) gnom_log("Terminating normally.");
  return 0;
 }

