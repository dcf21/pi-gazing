#!../../virtual-env/bin/python
# calibrateLens.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is used to estimate the degree of lens-distortion present in an image.

# It should be passed the filename of a JSON file containing an image filename, and a list of stars with known
# positions in the image. This file needs to be produced manually.

# The JSON files in this directory provide an example of the format each input
# file should take. The stars should be listed as [xpos, ypos, hipparcos
# number].

# It then uses the Python Scientific Library's numerical optimiser (with seven free parameters) to work out the
# position of the centre of the image in the sky, the image's rotation, scale on the sky, and the barrel distortion
# factors.

# The best-fit parameter values are returned to the user. If they are believed to be good, you should set a status
# update on the observatory setting barrel_a, barrel_b and barrel_c. Then future observations will correct for this
# lens distortion.

# You may also changed the values for your lens in the XML file <src/sensorProperties> which means that future
# observatories set up with your model of lens will use your barrel correction coefficients.


import sys
import json
import subprocess
from math import sqrt, hypot, sin, cos, tan, asin, atan2, pi
import scipy.optimize

degrees = pi / 180

# Read Hipparcos catalogue of stars brighter than mag 5.5
hipp_positions = json.loads(open("hipparcos_catalogue.json").read())


def rotate_xy(a, theta):
    a0 = a[0] * cos(theta) + a[1] * -sin(theta)
    a1 = a[0] * sin(theta) + a[1] * cos(theta)
    a2 = a[2]
    return [a0, a1, a2]


def rotate_xz(a, theta):
    a0 = a[0] * cos(theta) + a[2] * -sin(theta)
    a1 = a[1]
    a2 = a[0] * sin(theta) + a[2] * cos(theta)
    return [a0, a1, a2]


def make_zenithal(ra, dec, ra0, dec0):
    x = cos(ra) * cos(dec)
    y = sin(ra) * cos(dec)
    z = sin(dec)
    a = [x, y, z]
    a = rotate_xy(a, -ra0)
    a = rotate_xz(a, pi / 2 - dec0)
    if a[2] > 0.99999999:
        a[2] = 1.0
    if a[2] < -0.99999999:
        a[2] = -1.0
    altitude = asin(a[2])
    if abs(cos(altitude)) < 1e-7:
        azimuth = 0.0  # Ignore azimuth at pole!
    else:
        azimuth = atan2(a[1] / cos(altitude), a[0] / cos(altitude))
    zenith_angle = pi / 2 - altitude
    return [zenith_angle, azimuth]


def ang_dist(ra0, dec0, ra1, dec1):
    x0 = cos(ra0) * cos(dec0)
    y0 = sin(ra0) * cos(dec0)
    z0 = sin(dec0)
    x1 = cos(ra1) * cos(dec1)
    y1 = sin(ra1) * cos(dec1)
    z1 = sin(dec1)
    d = sqrt(pow(x0 - x1, 2) + pow(y0 - y1, 2) + pow(z0 - z1, 2))
    return 2 * asin(d / 2)


def gnomonic_project(ra, dec, ra0, dec0, size_x, size_y, scale_x, scale_y, pos_ang, bca, bcb, bcc):
    dist = ang_dist(ra, dec, ra0, dec0)

    if dist > pi / 2:
        return [-1, -1]
    [za, az] = make_zenithal(ra, dec, ra0, dec0)
    radius = tan(za)
    az -= pos_ang

    # Correction for barrel distortion
    r = radius / tan(scale_y / 2)
    bcd = 1. - bca - bcb - bcc
    r_new = (((bca * r + bcb) * r + bcc) * r + bcd) * r
    radius = r_new * tan(scale_y / 2)

    yd = radius * cos(az) * (size_y / 2. / tan(scale_y / 2.)) + size_y / 2.
    xd = radius * -sin(az) * (size_x / 2. / tan(scale_x / 2.)) + size_x / 2.
    return [xd, yd]


def mismatch(params):
    global params_scales, star_list, img_size_x, img_size_y
    ra0 = params[0] * params_scales[0]
    dec0 = params[1] * params_scales[1]
    scale_x = params[2] * params_scales[2]
    scale_y = params[3] * params_scales[3]
    pos_ang = params[4] * params_scales[4]
    bca = params[5] * params_scales[5]
    bcb = params[6] * params_scales[6]
    bcc = params[7] * params_scales[7]

    accumulator = 0
    for star in star_list:
        pos = gnomonic_project(star['ra'], star['dec'], ra0, dec0,
                               img_size_x, img_size_y, scale_x, scale_y, pos_ang,
                               bca, bcb, bcc)
        if pos[0] < 0:
            pos[0] = -999
        if pos[1] < 0:
            pos[1] = -999
        offset = pow(hypot(star['xpos'] - pos[0], star['ypos'] - pos[1]), 2)
        accumulator += offset
    # print "%10e -- %s" % (accumulator, list(params))
    return accumulator


# Return the dimensions of an image
def image_dimensions(f):
    d = subprocess.check_output(["identify", f]).split()[2].split("x")
    d = [int(item) for item in d]
    return d


# Read input list of stars whose positions we know
input_config_filename = sys.argv[1]
input_config = json.loads(open(input_config_filename).read())

# Look up positions of each star, based on listed Hipparcos catalogue numbers
star_list = []
for star in input_config['star_list']:
    hipp = str(star[2])
    if hipp not in hipp_positions:
        print "Could not find star %d" % hipp
        continue
    [ra, dec] = hipp_positions[hipp]
    star_list.append({'xpos': int(star[0]), 'ypos': int(star[1]), 'ra': ra * degrees, 'dec': dec * degrees})

# Get dimensions of the image we are dealing with
image_file = input_config['image_file']
[img_size_x, img_size_y] = image_dimensions(image_file)

# Solve system of equations to give best fit barrel correction
# See <http://www.scipy-lectures.org/advanced/mathematical_optimization/> for more information about how this works
ra0 = star_list[0]['ra']
dec0 = star_list[0]['dec']
params_scales = [pi / 4, pi / 4, pi / 4, pi / 4, pi / 4, pi / 4, 0.05, 0.05, 0.05]
params_defaults = [ra0, dec0, pi / 4, pi / 4, 0, 0, 0, 0]
params_initial = [params_defaults[i] / params_scales[i] for i in range(len(params_defaults))]
params_optimised = scipy.optimize.minimize(mismatch, params_initial, method='nelder-mead',
                                           options={'xtol': 1e-8, 'disp': True, 'maxiter': 1e8, 'maxfev': 1e8}).x
params_final = [params_optimised[i] * params_scales[i] for i in range(len(params_defaults))]

# Display best fit numbers
headings = [["Central RA / hr", 12 / pi], ["Central Decl / deg", 180 / pi],
            ["Image width / deg", 180 / pi], ["Image height / deg", 180 / pi],
            ["Position angle / deg", 180 / pi],
            ["barrel_a", 1], ["barrel_b", 1], ["barrel_c", 1]
            ]

for i in range(len(params_defaults)):
    print "%30s : %s" % (headings[i][0], params_final[i] * headings[i][1])

# Print information about how well each star was fitted
[ra0, dec0, scale_x, scale_y, pos_ang, bca, bcb, bcc] = params_final
if True:
    print "\nStars:"
    for star in star_list:
        pos = gnomonic_project(star['ra'], star['dec'], ra0, dec0,
                               img_size_x, img_size_y, scale_x, scale_y, pos_ang,
                               bca, bcb, bcc)
        distance = hypot(star['xpos'] - pos[0], star['ypos'] - pos[1])
        print "Real position (%4d,%4d). Model position (%4d,%4d). Mismatch %5d pixels." % (star['xpos'], star['ypos'],
                                                                                           pos[0], pos[1], distance)

# Print data file listing the predicting positions of each star, against the reported position
if False:
    for star in star_list:
        pos = gnomonic_project(star['ra'], star['dec'], ra0, dec0,
                               img_size_x, img_size_y, scale_x, scale_y, pos_ang,
                               bca, bcb, bcc)
        print "%4d %4d %4d %4d" % (star['xpos'] - img_size_x / 2, star['ypos'] - img_size_y / 2,
                                   pos[0] - img_size_x / 2, pos[1] - img_size_y / 2)
