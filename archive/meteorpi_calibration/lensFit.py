#!../../virtual-env/bin/python
# lensFit.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# -------------------------------------------------
# Copyright 2016 Cambridge Science Centre.

# This file is part of Meteor Pi.

# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

# Attempt to calculate the barrel distortion of the lens, to produce a better model for correcting recorded images.

# First we run orientationCalc.py. This uses astrometry.net to calculate the orientation of the camera based on recent
# images.

# It also produces a data file listing the 20-50 images used to calculate the orientation, together with the position
# of each image on the sky.

# We then call the program gnomonicStack/bin/camfit. This attempts to stack the 20-50 images, measuring the degree of
# mismatch between the images.

# It tries different barrel distortion coefficients to maximise the degree to which the images overlay one another.

import sys
import os
import orientationCalc
import mod_settings
import mod_log
import installation_info


def lens_fit(obstory_name, utc_now):
    # Run orientationCalc, to select good images around the requested time, and use astrometry.net to
    # estimate where they are on the sky
    image_list_path = orientationCalc.orientation_calc(obstory_name, utc_now, 0)

    # If orientationCalc returned None, we've not got any data we can use
    if not image_list_path:
        sys.exit(0)

    # Change into the temporary directory orientationCalc created for its output
    [tmp_dir, image_list_filename] = os.path.split(image_list_path)

    cwd = os.getcwd()
    os.chdir(tmp_dir)

    # Run the C program camfit, which attempts to stack together all of the images used by orientationCalc using
    # different barrel correction coefficients. If there are no lens distortions, the image should overlay each
    # other perfectly when they are stacked together. Otherwise, they won't overlay each other, because the
    # gnomonic transformations won't have properly de-rotated the sky. Iteratively try different barrel corrections
    # until we find a set which work well
    os.system("%s/bin/camfit %s > camFitOutput" % (mod_settings.settings['stackerPath'], image_list_filename))

    # The last line of output from camfit will contain the barrel distortion correction parameters a, b, c
    # separated by spaces
    camfit_output = open("camFitOutput").readlines()
    camfit_last_line = camfit_output[-1]

    print "Best fitting barrel distortion parameters were:\n%s\n\n" % camfit_last_line

    # Change back into the working directory
    os.chdir(cwd)


# If we're called as a script, run the method orientationCalc()
if __name__ == "__main__":
    _obstory_name = installation_info.local_conf['observatoryName']
    _utc_now = mod_log.get_utc()
    if len(sys.argv) > 1:
        _obstory_name = sys.argv[1]
    if len(sys.argv) > 2:
        _utc_now = float(sys.argv[2])
    lens_fit(_obstory_name, _utc_now)
