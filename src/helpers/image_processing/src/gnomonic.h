// gnomonic.h
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2015-2020 Dominic Ford.

// This file is part of Pi Gazing.

// Pi Gazing is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Pi Gazing is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
// -------------------------------------------------

#ifndef GNOMONIC_H
#define GNOMONIC_H 1

double angular_distance(double ra0, double dec0, double ra1, double dec1);

void find_mean_position(double *ra_out, double *dec_out, const double *ra_list, const double *dec_list,
                        int point_count);

void gnomonic_project(double ra, double dec, double ra0, double dec0, int x_size, int y_size,
                      double x_scale, double y_scale,
                      double *x_out, double *y_out, double pa,
                      double barrel_a, double barrel_b, double barrel_c);

void inv_gnomonic_project(double *ra_out, double *dec_out, double ra0, double dec0, int x_size, int y_size,
                          double x_scale, double y_scale, double x, double y, double pa,
                          double barrel_a, double barrel_b, double barrel_c);

#endif

