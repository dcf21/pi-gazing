// gnomonic.c
// Pi Gazing
// Dominic Ford

// -------------------------------------------------
// Copyright 2019 Dominic Ford.

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

#include <stdlib.h>
#include <math.h>
#include <gsl/gsl_math.h>
#include "gnomonic.h"

//! rotate_xy - Rotate a three-component vector about the z axis
//! \param a Vector to rotate in place
//! \param theta The angle to rotate around the z axis (radians)

void rotate_xy(double *a, double theta) {
    double a0 = a[0] * cos(theta) + a[1] * -sin(theta);
    double a1 = a[0] * sin(theta) + a[1] * cos(theta);
    double a2 = a[2];
    a[0] = a0;
    a[1] = a1;
    a[2] = a2;
}

//! rotate_xz - Rotate a three-component vector about the y axis
//! \param a Vector to rotate in place
//! \param theta The angle to rotate around the y axis (radians)

void rotate_xz(double *a, double theta) {
    double a0 = a[0] * cos(theta) + a[2] * -sin(theta);
    double a1 = a[1];
    double a2 = a[0] * sin(theta) + a[2] * cos(theta);
    a[0] = a0;
    a[1] = a1;
    a[2] = a2;
}

//! make_zenithal - Convert a position on the sky into alt/az coordinates
//! \param [in] ra The right ascension of the point to convert (radians)
//! \param [in] dec The declination of the point to convert (radians)
//! \param [in] ra0 The right ascension of the zenith (radians)
//! \param [in] dec0 The declination of the zenith (radians)
//! \param [out] za The zenith angle of the point (radians); equals pi/2 - altitude
//! \param [out] az The azimuth of the point (radians)

void make_zenithal(double ra, double dec, double ra0, double dec0, double *za, double *az) {
    double altitude, azimuth, zenith_angle;
    double x = cos(ra) * cos(dec);
    double y = sin(ra) * cos(dec);
    double z = sin(dec);
    double a[3] = {x, y, z};
    rotate_xy(a, -ra0);
    rotate_xz(a, (M_PI / 2) - dec0);
    if (a[2] > 0.999999999) a[2] = 1.0;
    if (a[2] < -0.999999999) a[2] = -1.0;
    altitude = asin(a[2]);
    if (fabs(cos(altitude)) < 1e-7) azimuth = 0.0; // Ignore azimuth at pole!
    else azimuth = atan2(a[1] / cos(altitude), a[0] / cos(altitude));
    zenith_angle = (M_PI / 2) - altitude;

    *za = zenith_angle;
    *az = azimuth;
}

//! angular_distance - Calculate the angular distance between two points on the sky
//! \param [in] ra0 The right ascension of the first point (radians)
//! \param [in] dec0 The declination of the first point (radians)
//! \param [in] ra1 The right ascension of the second point (radians)
//! \param [in] dec1 The declination of the second point (radians)
//! \return The angular separation (radians)

double angular_distance(double ra0, double dec0, double ra1, double dec1) {
    // Convert the first point from spherical polar coordinates to Cartesian coordinates
    double x0 = cos(ra0) * cos(dec0);
    double y0 = sin(ra0) * cos(dec0);
    double z0 = sin(dec0);
    // Convert the second point from spherical polar coordinates to Cartesian coordinates
    double x1 = cos(ra1) * cos(dec1);
    double y1 = sin(ra1) * cos(dec1);
    double z1 = sin(dec1);
    // Calculate the linear distance between the two points
    double d = sqrt(pow(x0 - x1, 2) + pow(y0 - y1, 2) + pow(z0 - z1, 2));
    // Convert linear distance into angular distance
    return 2 * asin(d / 2);
}

//! find_mean_position - Return the average of three points on the sky
//! \param [out] ra_out The right ascension of the average of the three points
//! \param [out] dec_out The declination of the average of the three points
//! \param [in] ra0 The right ascension of the first point (radians)
//! \param [in] dec0 The declination of the first point (radians)
//! \param [in] ra1 The right ascension of the second point (radians)
//! \param [in] dec1 The declination of the second point (radians)
//! \param [in] ra2 The right ascension of the third point (radians)
//! \param [in] dec2 The declination of the third point (radians)

void find_mean_position(double *ra_out, double *dec_out,
                        double ra0, double dec0,
                        double ra1, double dec1,
                        double ra2, double dec2) {
    // Convert the first point from spherical polar coordinates to Cartesian coordinates
    double x0 = cos(ra0) * cos(dec0);
    double y0 = sin(ra0) * cos(dec0);
    double z0 = sin(dec0);
    // Convert the second point from spherical polar coordinates to Cartesian coordinates
    double x1 = cos(ra1) * cos(dec1);
    double y1 = sin(ra1) * cos(dec1);
    double z1 = sin(dec1);
    // Convert the third point from spherical polar coordinates to Cartesian coordinates
    double x2 = cos(ra2) * cos(dec2);
    double y2 = sin(ra2) * cos(dec2);
    double z2 = sin(dec2);
    // Work out the centroid of the three points in Cartesian space
    double x3 = (x0 + x1 + x2) / 3;
    double y3 = (y0 + y1 + y2) / 3;
    double z3 = (z0 + z1 + z2) / 3;
    // Work out the magnitude of the centroid vector
    double mag = sqrt(gsl_pow_2(x3) + gsl_pow_2(y3) + gsl_pow_2(z3));
    // Convert the Cartesian coordinates into RA and Dec
    *dec_out = asin(z3 / mag);
    *ra_out = atan2(y3, x3);
}

//! gnomonic_project - Project a pair of celestial coordinates (RA, Dec) into pixel coordinates (x,y)
//! \param [in] ra The right ascension of the point to project (radians)
//! \param [in] dec The declination of the point to project (radians)
//! \param [in] ra0 The right ascension of the centre of the frame (radians)
//! \param [in] dec0 The declination of the centre of the frame (radians)
//! \param [in] x_size The horizontal size of the frame (pixels)
//! \param [in] y_size The vertical size of the frame (pixels)
//! \param [in] x_scale The angular width of the frame (radians)
//! \param [in] y_scale The angular height of the frame (radians)
//! \param [out] x_out The x position of (RA, Dec)
//! \param [out] y_out The y position of (RA, Dec)
//! \param [in] pa The position angle of the frame on the sky
//! \param [in] barrel_a The barrel distortion parameter A
//! \param [in] barrel_b The barrel distortion parameter B
//! \param [in] barrel_c The barrel distortion parameter C

void gnomonic_project(double ra, double dec, double ra0, double dec0, int x_size, int y_size,
                      double x_scale, double y_scale,
                      double *x_out, double *y_out, double pa,
                      double barrel_a, double barrel_b, double barrel_c) {
    double dist = angular_distance(ra, dec, ra0, dec0);
    double za, az, radius, xd, yd;

    if (dist > M_PI / 2) {
        *x_out = -1;
        *y_out = -1;
        return;
    }
    make_zenithal(ra, dec, ra0, dec0, &za, &az);
    radius = tan(za);
    az += pa;

    // Correction for barrel distortion
    double r = radius / tan(y_scale / 2);
    double bcd = 1. - barrel_a - barrel_b - barrel_c;
    double R = (((barrel_a * r + barrel_b) * r + barrel_c) * r + bcd) * r;
    radius = R * tan(y_scale / 2);

    yd = radius * cos(az) * (y_size / 2. / tan(y_scale / 2.)) + y_size / 2.;
    xd = radius * -sin(az) * (x_size / 2. / tan(x_scale / 2.)) + x_size / 2.;

    //if ((xd>=0)&&(xd<=x_size)) *x_out=(int)xd; else *x_out=-1;
    //if ((yd>=0)&&(yd<=y_size)) *y_out=(int)yd; else *y_out=-1;
    *x_out = xd;
    *y_out = yd;
}

//! inv_gnomonic_project - Project a pair of pixel coordinates (x,y) into a celestial position (RA, Dec). This includes
//! a correction for Barrel distortion.
//! \param [out] ra_out The right ascension of the point to project (radians)
//! \param [out] dec_out The declination of the point to project (radians)
//! \param [in] ra0 The right ascension of the centre of the frame (radians)
//! \param [in] dec0 The declination of the centre of the frame (radians)
//! \param [in] x_size The horizontal size of the frame (pixels)
//! \param [in] y_size The vertical size of the frame (pixels)
//! \param [in] x_scale The angular width of the frame (radians)
//! \param [in] y_scale The angular height of the frame (radians)
//! \param [in] x The x position of (RA, Dec)
//! \param [in] y The y position of (RA, Dec)
//! \param [in] pa The position angle of the frame on the sky
//! \param [in] barrel_a The barrel distortion parameter A
//! \param [in] barrel_b The barrel distortion parameter B
//! \param [in] barrel_c The barrel distortion parameter C

void inv_gnomonic_project(double *ra_out, double *dec_out, double ra0, double dec0, int x_size, int y_size,
                          double x_scale, double y_scale, double x, double y, double pa,
                          double barrel_a, double barrel_b, double barrel_c) {
    double x2 = (x - x_size / 2.) / (x_size / 2. / tan(x_scale / 2.));
    double y2 = (y - y_size / 2.) / (y_size / 2. / tan(y_scale / 2.));

    double za = atan(hypot(x2, y2));
    double az = atan2(-x2, y2) - pa;

    // Correction for barrel distortion
    double r = za / tan(y_scale / 2.);
    double bcd = 1. - barrel_a - barrel_b - barrel_c;
    double R = (((barrel_a * r + barrel_b) * r + barrel_c) * r + bcd) * r;
    za = R * tan(y_scale / 2.);

    double altitude = M_PI / 2 - za;
    double a[3] = {cos(altitude) * cos(az),
                   cos(altitude) * sin(az),
                   sin(altitude)};

    rotate_xz(a, -(M_PI / 2) + dec0);
    rotate_xy(a, ra0);

    *ra_out = atan2(a[1], a[0]);
    *dec_out = asin(a[2]);
}
