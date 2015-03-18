# MeteorPi API module

class Location:
	latitude = 0.0
	longitude = 0.0
	gps = False

class Orientation:
	altitude = 0.0
	azimuth = 0.0
	certainty = 0.0

class CameraStatus:
	regions = []
	lens = ""
	camera = ""
	validFrom = None
	validTo = None
	instURL = ""
	instaName = ""
	orientation = Orientation()
	location = Location()


