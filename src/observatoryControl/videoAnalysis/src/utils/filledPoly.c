// filledPoly.c
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

// Adapted from public-domain code by Darel Rex Finley, 2007

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "utils/asciidouble.h"
#include "utils/filledPoly.h"
#include "str_constants.h"

void fillPolygonsFromFile(FILE *infile, unsigned char *mask, int width, int height) {
    char line[FNAME_LENGTH];
    int polyCorners = 0, polyX[MAX_POLY_CORNERS], polyY[MAX_POLY_CORNERS];
    int stopping = 0, filledPixels = 0;

    memset(mask, 0, width * height);

    while (!stopping) {
        if (feof(infile)) {
            stopping = 1;
            goto blankLine;
        }
        file_readline(infile, line, LSTR_LENGTH);
        StrStrip(line, line);
        if (strlen(line) == 0) goto blankLine;
        if (line[0] == '#') continue;

        char *cp = line;
        polyX[polyCorners] = GetFloat(cp, NULL);
        cp = NextWord(cp);
        polyY[polyCorners] = GetFloat(cp, NULL);
        polyCorners++;
        continue;

        blankLine:
        if (polyCorners > 2) {
            filledPixels += fillPolygon(polyCorners, polyX, polyY, mask, width, height);
            polyCorners = 0;
        }
    }

    if (filledPixels < 1)
        memset(mask, 1, width * height); // If not clipping region is specified, allow triggers across the whole frame
    return;
}

int fillPolygon(int polyCorners, int *polyX, int *polyY, unsigned char *mask, int width, int height) {
    int Nfilled = 0;

    int nodes, nodeX[MAX_POLY_CORNERS], pixelX, pixelY, i, j, swap;

    // Loop through the rows of the image.
    for (pixelY = 0; pixelY < height; pixelY++) {
        // Build a list of nodes.
        nodes = 0;
        j = polyCorners - 1;
        for (i = 0; i < polyCorners; i++) {
            if (((polyY[i] < (double) pixelY) && (polyY[j] >= (double) pixelY)) ||
                ((polyY[j] < (double) pixelY) && (polyY[i] >= (double) pixelY))) {
                nodeX[nodes++] = (int) (polyX[i] +
                                        (pixelY - polyY[i]) / ((double) (polyY[j] - polyY[i])) * (polyX[j] - polyX[i]));
            }
            j = i;
        }

        // Sort the nodes, via a simple "Bubble" sort.
        i = 0;
        while (i < nodes - 1) {
            if (nodeX[i] > nodeX[i + 1]) {
                swap = nodeX[i];
                nodeX[i] = nodeX[i + 1];
                nodeX[i + 1] = swap;
                if (i) i--;
            }
            else { i++; }
        }

        // Fill the pixels between node pairs.
        for (i = 0; i < nodes; i += 2) {
            if (nodeX[i] >= width) break;
            if (nodeX[i + 1] > 0) {
                if (nodeX[i] < 0) nodeX[i] = 0;
                if (nodeX[i + 1] > width) nodeX[i + 1] = width;
                for (pixelX = nodeX[i]; pixelX < nodeX[i + 1]; pixelX++) {
                    mask[pixelX + width * pixelY] = 1;
                    Nfilled++;
                }
            }
        }
    }
    return Nfilled;
}

