// skyClarity.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "png/image.h"
#include "utils/tools.h"
#include "utils/asciidouble.h"
#include "utils/error.h"

int main(int argc, char *argv[]) {
    if (argc != 3) {
        sprintf(temp_err_string,
                "ERROR: Need to specify input filename and noise level on the commandline, e.g. 'skyClarity tmp.png 3.45'.");
        gnom_fatal(__FILE__, __LINE__, temp_err_string);
    }

    double noiseLevel = GetFloat(argv[2], NULL);

    // Read image
    image_ptr InputImage;
    InputImage = image_get(argv[1]);
    if (InputImage.data_red == NULL) gnom_fatal(__FILE__, __LINE__, "Could not read input image file 1");

    double skyClarity = calculateSkyClarity(&InputImage, noiseLevel);
    printf("%f", skyClarity);

    // Free image
    image_dealloc(&InputImage);
    return 0;
}
