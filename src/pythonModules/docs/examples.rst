API Examples
============

These examples are shown connecting to the development server running on my machine - URLs and the actual results from
a real server will be different (obviously). Before you start you'll need to install the MeteorPi client library (this
also brings in the model as a dependency), using:

.. code-block:: bash

    > pip install meteorpi_client

For your own sanity we recommend using a virtual environment at this point, but it's not required. If you're using the
system Python installation you may need to run the command above with root permissions.

Connecting to a MeteorPi Server
-------------------------------

Firstly check that we can connect to a server, here running on the `localhost` machine, and list the cameras. This code
should all execute from a Python shell.

.. code-block:: python

    >>> import meteorpi_client
    >>> client = meteorpi_client.MeteorClient(base_url="http://localhost:12345/")
    >>> client
    <meteorpi_client.MeteorClient instance at 0x7f26b54ca6c8>
    >>> client.list_cameras()
    ['aabbccddeeff', '001122334455']

Searching for Files
-------------------

Next test is to search for files. To do this you need to create a :class:`meteorpi_model.FileRecordSearch` object and
pass it into the client's **search_files** method. The search object contains a large number of potential search
restrictions that can be applied in its constructor - in this simple case the search will restrict results to only
those from the specified camera, exclude files which are part of the record of an event (files can be part of events or
can exist stand-alone). A default result limit of 100 is applied - this makes no difference in this case as we're only
going to return a handful of files from the test data set but it's worth bearing in mind when operating on real data.

.. code-block:: python

    >>> import meteorpi_model as m
    >>> file_search = m.FileRecordSearch(camera_ids='aabbccddeeff', exclude_events='true')
    >>> result = client.search_files(search=file_search)
    >>> result
    {'count': 6,
     'files': [<meteorpi_model.FileRecord instance at 0x7f5717c8dc20>,
               <meteorpi_model.FileRecord instance at 0x7f571677c878>,
               <meteorpi_model.FileRecord instance at 0x7f571675c6c8>,
               <meteorpi_model.FileRecord instance at 0x7f5716771050>,
               <meteorpi_model.FileRecord instance at 0x7f5716760e60>,
               <meteorpi_model.FileRecord instance at 0x7f57165cf7e8>]}

The result is a dict containing two keys. **count** is an integer and tells you how many results would have been
returned by the query if there was no limit. In this case, because the query has returned all the results, **count**
is the same as the length of the **files** list.

**files** contains the results in the form of :class:`meteorpi_model.FileRecord` objects. To help examine these it's
worth noting that many of the model objects have a *as_dict()* method. This is used internally to send the object to
the client, but can also show you what's inside:

.. code-block:: python

    >>> result["files"][0].as_dict()
    {'status_id': 'ababc09c8199431ba54e2e0f35f5fb25',
     'file_time': 1427847660000,
     'meta': [{'type': 'string', 'value': 'meta_value_0', 'key': 'meteorpi:meta_key_0'}],
     'semantic_type': 'meteorpi:test_file',
     'camera_id': 'aabbccddeeff',
     'file_size': 0,
     'mime_type': 'text/plain',
     'file_id': 'a3949199e2df41a0bff500985dc2c93e'}

From this you can see that this is clearly test data! On a real server you'd see other values here, in particular you
would expect a non-zero file size and to see something more meaningful in **semantic_type**.

There are some difference here between what *as_dict()* shows and what's contained within the object you're holding. In
particular in this case the **file_time** is shown as a long number. This is what we use internally, it's actually the
number of milliseconds since a particular point in time and we use it because it means we don't have to deal with leap
years, leap seconds, daylight saving time, time zones and all that extra 'fun' you get with real world dates. You'll be
pleased to know though that the object actually contains a Python :class:`datetime.datetime`:

.. code-block:: python

    >>> result["files"][0].file_time
    datetime.datetime(2015, 4, 1, 0, 21)

Downloading Files
-----------------

Once you have a :class:`meteorpi_model.FileRecord` from a search you probably want to get the actual file it represents.
The files are held on the server, you can either get the URL for a file or trigger a download directly to your local
disk.

.. code-block:: python

    >>> result["files"][0].get_url()
    'http://localhost:12345//files/content/a3949199e2df41a0bff500985dc2c93e/None'
    >>> result["files"][0].download_to("my_file_on_disk.txt")
    'my_file_on_disk.txt'
