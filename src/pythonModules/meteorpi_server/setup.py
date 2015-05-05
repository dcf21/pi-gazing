from setuptools import setup

setup(
    name='meteorpi_server',
    version='0.1',
    description='HTTP server based on Flask providing a remote API',
    classifiers=['Programming Language :: Python :: 2.7'],
    url='https://github.com/camsci/meteor-pi/',
    author='Tom Oinn',
    author_email='tomoinn@crypticsquid.com',
    license='GPL',
    packages=['meteorpi_server'],
    install_requires=[
        'meteorpi_fdb',
        'flask',
        'tornado',
        'pyyaml'],
    include_package_data=True,
    test_suite='nose.collector',
    tests_require=['nose'],
    zip_safe=False)
