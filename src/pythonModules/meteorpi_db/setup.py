from setuptools import setup

setup(
    name='meteorpi_db',
    version='0.1.5',
    description='Data access layer, uses FireBird to persist and retrieve MeteorPi classes',
    classifiers=['Programming Language :: Python :: 2.7'],
    url='https://github.com/camsci/meteor-pi/',
    author='Tom Oinn',
    author_email='tomoinn@crypticsquid.com',
    license='GPL',
    packages=['meteorpi_db'],
    install_requires=[
        'meteorpi_model',
        'MySQLdb',
        'passlib',
        'json',
        'requests',
        'requests-toolbelt',
        'apscheduler',
        'backports.functools_lru_cache'],
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=['nose'],
    zip_safe=False)
