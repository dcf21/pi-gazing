API Documentation
=================

Controlled Vocabularies
-----------------------

At various points in the model we use extensible sets of names. This gives us versatility in describing Events and
FileRecords, but can be confusing when searching and when interpreting the results of those searches. To mitigate this
confusion we maintain pages on our wiki containing the possible values and descriptions for such cases:

Metadata keys
^^^^^^^^^^^^^

Various points in the model and search classes use metadata. These are extensible fields, used to enrich the information
provided by an Event or FileRecord, and consist of a key and value. The value may be numeric, time or text, and the keys
can, in theory, be anything. Obviously to sensibly search for and interpret these metadata values you'll need to have
an idea of the possible keys and their meanings. These are maintained on our wiki at
https://github.com/camsci/meteor-pi/wiki/List-of-metadata-fields

Semantic types
^^^^^^^^^^^^^^

In a similar fashion, we use a namespaced string to specify the semantic type of both Event and FileRecord objects. The
semantic type is used to indicate the meaning of the object - an Event may have a semantic type indicating that it's an
observation of a meteor as opposed to a satellite, a FileRecord may have one to denote that it's a timelapse image
rather than some other image. Note in particular that FileRecords also have a MIME type, the MIME type denotes the
format of the file whereas the semantic type indicates its contents.

As there's a potentially infinite number of these types we maintain a list of the semantic types used by the MeteorPi
project at https://github.com/camsci/meteor-pi/wiki/List-of-semantic-types. Other projects may extend this set of types,
but this should always contain an up-to-date list of the values we use within the project. Use this to find out what to
put in your queries, and to interpret the values in the objects those queries retrieve.


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

Export
^^^^^^

These classes are used to configure the data export mechanism within a node, it's unlikely you'll need to use them
directly yourself but they're part of the model API so included here for completeness.

.. autoclass:: meteorpi_model.ExportConfiguration
    :members:
