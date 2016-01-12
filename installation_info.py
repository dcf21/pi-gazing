# In this file you must configure the default position and name of this camera

local_conf = {

    'latitude': 52.194317,  # Degrees north
    'longitude': 0.147193,  # Degrees east
    'observatoryId': "obs1",
    'observatoryName': "Cambridge-South-East",

    # This flag sets the polarity of the relay used to turn the camera on
    # GPIO line 12 is set to this state to turn the camera ON
    'relayOnGPIOState': True,

    # This flag sets how long we keep data locally on the SD card for (days)
    'dataLocalLifetime': 10,

    # Configure export of data to a remote server
    'exportURL': "https://meteorpi.cambridgesciencecentre.org/api/import",
    'exportUsername': "",  # The username used to log in to the remote server
    'exportPassword': "",  # Corresponding password

}
