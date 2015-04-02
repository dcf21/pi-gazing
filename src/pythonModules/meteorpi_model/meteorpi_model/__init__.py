# MeteorPi API module

class Location:
	def __init__(self, latitude = 0.0, longitude = 0.0, gps = False):
		self.latitude = latitude
		self.longitude = longitude
		self.gps = gps
	def __str__(self):
		return '(lat={0}, long={1}, gps={2})'.format(self.latitude, self.longitude, self.gps)
	latitude = 0.0
	longitude = 0.0
	gps = False

class Orientation:
	def __init__(self, altitude = 0.0, azimuth = 0.0, certainty = 0.0):
		self.altitude = altitude
		self.azimuth = azimuth
		self.certainty = certainty
	def __str__(self):
		return '(alt={0}, az={1}, p={2})'.format(self.altitude, self.azimuth, self.certainty)
	altitude = 0.0
	azimuth = 0.0
	certainty = 0.0

class CameraStatus:
	def __init__(self, lens, camera, instURL, instName, orientation, location):
		self.lens = lens
		self.camera = camera
		self.instURL = instURL
		self.instName = instName
		self.orientation = orientation
		self.location = location
	def __str__(self):
		return 'CameraStatus(location={0}, orientation={1}, validFrom={2}, validTo={3}, version={4}, lens={5}, cam={6})'.format(self.location, self.orientation, self.validFrom, self.validTo, self.softwareVersion, self.lens, self.camera)
	regions = []
	lens = ""
	camera = ""
	validFrom = None
	validTo = None
	instURL = ""
	instName = ""
	orientation = Orientation()
	location = Location()
	softwareVersion = 1


