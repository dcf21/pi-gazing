// gnomonic.h
// Meteor Pi, Cambridge Science Centre 
// Dominic Ford

// -------------------------------------------------
// Copyright 2016 Cambridge Science Centre.

// This file is part of Meteor Pi.

// Meteor Pi is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Meteor Pi is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

#ifndef GNOMONIC_H
#define GNOMONIC_H 1

double AngDist(double RA0, double Dec0, double RA1, double Dec1);

void FindMeanPosition(double *RAm, double *DECm, double RA0, double DEC0, double RA1, double DEC1, double RA2,
                      double DEC2);

void GnomonicProject(double RA, double Dec, double RA0, double Dec0, int SizeX, int SizeY, double ScaleX, double ScaleY,
                     double *x, double *y, double posang, double bca, double bcb, double bcc);

void InvGnomProject(double *RA, double *Dec, double RA0, double Dec0, int SizeX, int SizeY, double ScaleX,
                    double ScaleY, double x, double y, double posang, double bca, double bcb, double bcc);

#endif

