# In this file you must configure the default position and name of this camera

LATITUDE = 52.194317  # Degrees north
LONGITUDE = 0.147193  # Degrees east
CAMERA_NAME = "Cambridge-South-East"

# This flag sets the polarity of the relay used to turn the camera on
# GPIO line 12 is set to this state to turn the camera ON
relayOnGPIOState = True

# This flag sets how long we keep data locally on the SD card for (days)
dataLocalLifetime = 5

# Configure export of data to a remote server
EXPORT_URL = "https://meteorpi.cambridgesciencecentre.org/api/import"
EXPORT_USERNAME = ""  # The username used to log in to the remote server
EXPORT_PASSWORD = ""  # Corresponding password
