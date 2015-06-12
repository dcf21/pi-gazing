Internal API Documentation
==========================

These Python modules are only useful to you if you're working on the MeteorPi server and database code.

Server: `meteorpi_server`
-------------------------

Logic to build the WSGI app, and optionally run it as a local Tornado based server for testing.

.. automodule:: meteorpi_server
:members:

Database: `meteorpi_fdb`
------------------------

Firebird based data access layer, uses a simple directory based file store to handle file data.

.. automodule:: meteorpi_fdb
:members:
