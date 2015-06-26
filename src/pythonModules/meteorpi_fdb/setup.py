from setuptools import setup

setup(
    name='meteorpi_fdb',
    version='0.1.2',
    description='Data access layer, uses FireBird to persist and retrieve MeteorPi classes',
    classifiers=['Programming Language :: Python :: 2.7'],
    url='https://github.com/camsci/meteor-pi/',
    author='Tom Oinn',
    author_email='tomoinn@crypticsquid.com',
    license='GPL',
    packages=['meteorpi_fdb'],
    install_requires=[
        'meteorpi_model',
        'fdb',
        'passlib',
        'pyyaml',
        'requests',
        'requests-toolbelt'],
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=['nose'],
    zip_safe=False)
