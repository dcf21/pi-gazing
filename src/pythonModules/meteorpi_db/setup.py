from setuptools import setup

setup(
    name='meteorpi_db',
    version='0.2.0',
    description='Data access layer, uses MySQL',
    classifiers=['Programming Language :: Python :: 2.7'],
    url='https://github.com/camsci/meteor-pi/',
    author='Dominic Ford, Tom Oinn',
    author_email='tomoinn@crypticsquid.com',
    license='GPL',
    packages=['meteorpi_db'],
    install_requires=[
        'meteorpi_model',
        'MySQL-python',
        'passlib',
        'requests',
        'requests-toolbelt'],
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=['nose'],
    zip_safe=False)
