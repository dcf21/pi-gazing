#!../../virtualenv/bin/python3
# -*- coding: utf-8 -*-
# deploy_raspberry_pi.py
#
# -------------------------------------------------
# Copyright 2015-2018 Dominic Ford
#
# This file is part of Meteor Pi.
#
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

"""
This script should be run on a Raspberry Pi, using an SD card which has been set up with the hostname <meteorpi-clean>
and the standard contents of <installation_info.py>

It asks the user to enter the settings which the defaults should be replaced with
"""

import os
import sys

from meteorpi_helpers import settings_read

# Make sure we are running on a RPi. We don't want to overwrite the contents of </etc> on a PC...
if not settings_read.settings['i_am_a_rpi']:
    print("This is not running on a Raspberry Pi. You should not run this on a PC.")
    sys.exit(1)

# Make sure we are running as root
if os.geteuid() != 0:
    print("This script must be run as root.")
    sys.exit(1)

# Change into directory containing this script, so we can use relative paths
os.chdir(settings_read.settings['pythonPath'])

# Check with the user that they know what's about to happen
confirmation = input("""
This script should only be run on an SD card which has been set up with the hostname <meteorpi-clean>
and the standard contents of <installation_info.py>, by following the instructions in the Wiki on the Meteor Pi GitHub
website.

It will replace your network settings and Meteor Pi configuration with user-entered values.

Are you sure you would like to proceed? (Y/N)
""")
if confirmation not in 'Yy':
    sys.exit(0)


# Helper function for doing string search/replace within files
def file_substitute(filename, search, replace):
    f = open(filename, 'r')
    file_data = f.read()
    f.close()
    new_data = file_data.replace(search, replace)
    f = open(filename, 'w')
    f.write(new_data)
    f.close()


# Helper function to read input from user
def user_input(prompt, default):
    value = input("Enter %s (default <%s>): " % (prompt, default))
    if not value:
        return default
    return value


# Set hostname for this Raspberry Pi
print("STEP 1: Set a hostname for your Raspberry Pi (e.g. meteorpi-dave)")

hostname = user_input("Enter hostname: ", "meteorpi-clean")
file_substitute("/etc/hostname", "meteorpi-clean", hostname)
file_substitute("/etc/hosts", "meteorpi-clean", hostname)
file_substitute("/etc/apache2/sites-available/meteorpi-clean.local.conf", "meteorpi-clean", hostname)

# Set up contents of installation_info
print("STEP 2: Update observatory details")

obstory_id = user_input("observatory ID", installation_info.local_conf['observatoryId'])
obstory_name = user_input("observatory name", installation_info.local_conf['observatoryName'])
obstory_lat = user_input("observatory latitude", installation_info.local_conf['latitude'])
obstory_lng = user_input("observatory longitude", installation_info.local_conf['longitude'])
file_substitute("../../installation_info.py", "52.19", obstory_lat)
file_substitute("../../installation_info.py", "0.15", obstory_lng)
file_substitute("../../installation_info.py", "obs0", obstory_id)
file_substitute("../../installation_info.py", "Observatory-Dummy", obstory_name)

export_url = user_input("default export URL", installation_info.local_conf['exportURL'])
export_user = user_input("default export username", installation_info.local_conf['exportUsername'])
export_pw = user_input("default export password", installation_info.local_conf['exportPassword'])
file_substitute("../../installation_info.py", "export_url", export_url)
file_substitute("../../installation_info.py", "export_user", export_user)
file_substitute("../../installation_info.py", "export_password", export_pw)

relay_pin = user_input("GPIO pin which the relay is connected to", installation_info.local_conf['gpioPinRelay'])
file_substitute("../../installation_info.py", "'gpioPinRelay': 12", "'gpioPinRelay': %s" % relay_pin)

relay_state = user_input("relay on state True/False", str(installation_info.local_conf['relayOnGPIOState']))
file_substitute("../../installation_info.py", "'relayOnGPIOState': True", "'relayOnGPIOState': %s" % relay_state)

led_a_pin = user_input("GPIO pin which LED A is connected to", installation_info.local_conf['gpioLedA'])
file_substitute("../../installation_info.py", "'gpioLedA': 18", "'gpioLedA': %s" % led_a_pin)
led_b_pin = user_input("GPIO pin which LED A is connected to", installation_info.local_conf['gpioLedB'])
file_substitute("../../installation_info.py", "'gpioLedB': 22", "'gpioLedB': %s" % led_b_pin)
led_c_pin = user_input("GPIO pin which LED A is connected to", installation_info.local_conf['gpioLedC'])
file_substitute("../../installation_info.py", "'gpioLedC': 24", "'gpioLedC': %s" % led_c_pin)

# Set up database
print("STEP 3: Set up database")
os.system("../sql/rebuild.sh")

# Set up observatory metadata
print("STEP 4: Set up observatory metadata")
os.system("./updateObservatoryStatus.py")

# Set up user account
print("STEP 4: Set up admin user account")
os.system("./updateUser.py")

# Set up default exports
print("STEP 5: Set up default exports")
os.system("./defaultExports.py")
