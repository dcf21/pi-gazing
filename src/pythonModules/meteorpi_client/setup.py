from setuptools import setup

setup(
    name='meteorpi_client',
    version='0.1.2',
    description='Client to the MeteorPi HTTP API',
    classifiers=['Programming Language :: Python :: 2.7'],
    url='https://github.com/camsci/meteor-pi/',
    author='Tom Oinn',
    author_email='tomoinn@crypticsquid.com',
    license='GPL',
    packages=['meteorpi_client'],
    install_requires=[
        'meteorpi_model',
        'pyyaml',
        'requests'],
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=['nose',
                   'meteorpi_server'],
    zip_safe=False)
