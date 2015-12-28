Internal API Documentation
==========================

These Python modules are only useful to you if you're working directly on or with the MeteorPi server and database code.

Server: `meteorpi_server`
-------------------------

Logic to build the Flask based WSGI app, and optionally run it as a local Tornado based server for testing. The app is
modular, initially not populated with any routes - these are provided by the xxx_api modules, allowing for modular
assembly of an app with the functions you need for your application.

.. automodule:: meteorpi_server
    :members:

.. automodule:: meteorpi_server.query_api
    :members:

.. automodule:: meteorpi_server.admin_api
    :members:

Also provides the import API - this is an extensible system which can be used to receive data from an export task on the
database side. The code includes an implementation of this system which handles event and file record replication, but
the system can also be used for other purposes such as social media gateways, notification etc.

.. automodule:: meteorpi_server.importer_api
    :members:

Database: `meteorpi_db`
------------------------

Firebird based data access layer, uses a simple directory based file store to handle file data. The database itself
provides for search, retrieval and registration operations, with extra modules providing export mark and process
functionality. Caching is implemented as an in-memory LRU cache for each main event type, mostly to optimise the kind of
burst access we tend to have during imports and exports, and during pagination of searches.

.. automodule:: meteorpi_db
    :members:

.. automodule:: meteorpi_db.exporter
    :members:

The core search operations are split into SQL generation in the sql_builder module, and lazy instantiation of the domain
entities in the generators module. While most existing APIs in the main database then instantiate lists of results in
response to search, if you are extending the server and need to iterate over all files or all events these generators
allow you to do so in an efficient manner.

.. automodule:: meteorpi_db.generators
    :members:

.. automodule:: meteorpi_db.sql_builder
    :members: