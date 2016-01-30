# In this file you must configure the default position and name of this observatory

local_conf = {

    'latitude': 52.19,  # Degrees north
    'longitude': 0.15,  # Degrees east
    'observatoryId': "obs0",
    'observatoryName': "Observatory-Dummy",

    # Set which GPIO pins we are using
    'gpioPinRelay': 12,  # This pin is using to control the relay
    'gpioLedA': 18,  # This pin is used for indicator LED A
    'gpioLedB': 22,  # This pin is used for indicator LED B
    'gpioLedC': 24,  # This pin is used for indicator LED C

    # This flag sets the polarity of the relay used to turn the camera on
    # GPIO line is set to this state to turn the camera ON
    'relayOnGPIOState': True,

    # This flag sets how long we keep data locally on the SD card for (days)
    'dataLocalLifetime': 14,

    # Configure export of data to a remote server
    'exportURL': "export_url",
    'exportUsername': "export_user",  # The username used to log in to the remote server
    'exportPassword': "export_password",  # Corresponding password

}
