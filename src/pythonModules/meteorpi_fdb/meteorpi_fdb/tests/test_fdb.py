from unittest import TestCase

import meteorpi_fdb as m

class TestFdb(TestCase):
	def testGetInstallationId(self):
		m.getInstallationId()
