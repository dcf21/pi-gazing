#!../../virtual-env/bin/python
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# Run this python script to manually turn the camera in an observatory on.

# You shouldn't normally need to do this, as the camera is automatically turned on when the observatory starts
# observing each day. However you may want to run this when you are testing the camera.

import mod_relay

mod_relay.camera_on()
