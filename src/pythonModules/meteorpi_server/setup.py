from setuptools import setup

setup(
    name='meteorpi_server',
    version='0.1.5',
    description='HTTP server based on Flask providing a remote API',
    classifiers=['Programming Language :: Python :: 2.7'],
    url='https://github.com/camsci/meteor-pi/',
    author='Tom Oinn',
    author_email='tomoinn@crypticsquid.com',
    license='GPL',
    packages=['meteorpi_server'],
    install_requires=[
        'meteorpi_db',
        'flask',
        'flask-cors',
        'tornado',
        'flask-jsonpify',
        'backports.functools_lru_cache'],
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=['nose',
                   'pyyaml',
                   'requests',
                   'flask-jsonpify'],
    zip_safe=False)
