from setuptools import setup

setup(name='meteorpi_model',
      version='0.1.5',
      description='Model classes used across the MeteorPi project',
      url='https://github.com/camsci/meteor-pi/',
      author='Tom Oinn',
      author_email='tomoinn@crypticsquid.com',
      license='GPL',
      packages=['meteorpi_model'],
      test_suite='nose.collector',
      tests_require=['nose'],
      zip_safe=False)
