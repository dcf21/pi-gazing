API Documentation
=================

Client: `meteorpi_client`
-------------------------

Use this to connect to and query a remote MeteorPi server.

.. autoclass:: meteorpi_client.MeteorClient
    :members:

Model: `meteorpi_model`
-----------------------

This module provides classes which represent entities within the MeteorPi project.

Typically you will use this package by creating instances of :class:`meteorpi_model.FileRecordSearch` and
:class:`meteorpi_model.EventSearch`, with the :class:`meteorpi_model.MetaConstraint` used by both kinds of search
when you want to search over event or file metadata.

Searches will return data as collections of :class:`meteorpi_model.FileRecord` or :class:`meteorpi_model.Event` along
with their associated :class:`meteorpi_model.Meta` metadata collections.

FileRecord
^^^^^^^^^^
.. autoclass:: meteorpi_model.FileRecord
    :members:

Event
^^^^^
.. autoclass:: meteorpi_model.Event
    :members:

Meta
^^^^
.. autoclass:: meteorpi_model.Meta
    :members:

FileRecordSearch
^^^^^^^^^^^^^^^^
.. autoclass:: meteorpi_model.FileRecordSearch
    :members:

EventSearch
^^^^^^^^^^^
.. autoclass:: meteorpi_model.EventSearch
    :members:

MetaConstraint
^^^^^^^^^^^^^^
.. autoclass:: meteorpi_model.MetaConstraint
    :members:

NSString
^^^^^^^^
.. autoclass:: meteorpi_model.NSString
    :members:

User
^^^^
.. autoclass:: meteorpi_model.User
    :members:

CameraStatus
^^^^^^^^^^^^
.. autoclass:: meteorpi_model.CameraStatus
    :members:

.. autoclass:: meteorpi_model.Location
    :members:

.. autoclass:: meteorpi_model.Orientation
    :members: