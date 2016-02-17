// filledPoly.h
// Meteor Pi, Cambridge Science Centre
// Dominic Ford

#ifndef FILLEDPOLY_H
#define FILLEDPOLY_H 1

#include <stdio.h>

#define MAX_POLY_CORNERS 1024

void fillPolygonsFromFile(FILE *infile, unsigned char *mask, int width, int height);

int fillPolygon(int polyCorners, int *polyX, int *polyY, unsigned char *mask, int width, int height);

#endif

