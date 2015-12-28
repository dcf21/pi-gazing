Python Server Configuration
===========================

The MeteorPi server is designed to be modular - aspects such as the admin API, data export, and others can be configured
independently to suit your particular deployment. If you don't need export functionality you simply don't include that
component in your server, saving resources - particularly helpful for some of the resource constrained environments we
envisage this software inhabiting.

There is a full HTTP server included in the meteorpi_server package, but we only recommend using this for testing and
development. Instead MeteorPi is intended to be run in a WSGI container, there are implementations of such a thing for
all common web servers. The WSGI application can be constructed and configured from a regular Python script, and it is
in this script that the configuration and component selection described above occurs.

Server Object
^^^^^^^^^^^^^

The WSGI application object is created using an instance of :class:`meteorpi_server.MeteorApp`. Note that the
:class:`meteorpi_server.MeteorServer` is the development server, you almost certainly don't want to use this. The app
is created with a reference to a :class:`meteorpi_db.MeteorDatabase` as follows:

.. code-block:: python

    from meteorpi_db import MeteorDatabase
    from meteorpi_server import MeteorApp, admin_api, importer_api, query_api

    # Configure and create database and server objects
    db_path = 'localhost:/var/lib/firebird/2.5/data/meteorpi.db'
    file_store_path = '/home/meteorpi/meteorpi_files'
    db = MeteorDatabase(db_path=db_path, file_store_path=file_store_path)
    meteor_app = MeteorApp(db=db)
    # Get the WSGI application from the meteor_app object
    wsgi_app = meteor_app.app

HTTP APIs
---------

Once you have the WSGI application the mechanism to expose this to the web server will vary from server to server, but
before doing this you need to configure the application. The code shown above will create the app, and connect it to
its database, but will not actually add any HTTP APIs. To do this you must call methods within **meteorpi_server** - at
the present time there are three packages of APIs which can be installed independently, each of which provides a subset
of the complete HTTP API. For most applications, and to enable the website, you will want to install all three:

.. code-block:: python

    # Add routes
    admin_api.add_routes(meteor_app=meteor_app)
    importer_api.add_routes(meteor_app=meteor_app)
    query_api.add_routes(meteor_app=meteor_app)

The three sets of routes (a route is the Flask term for a mapping between a URL pattern and a function in the code)
define different capabilities. The admin routes are needed for administration through the web interface or programmatic
API. The query routes are used when querying data, and the importer routes are used when allowing this node to receive
data from another node in the system (so it's likely that a camera node will not want to add this last set).

Data Export
-----------

The export mechanism is also provided by an extra set of functions. It does not require the HTTP server to operate as it
is entirely push based, but it's likely that you'll want to include it in the WSGI app to allow your server to push data
to other nodes (i.e. a camera sending data to a central server). Note that without this package you can still configure
export tasks in the web UI and through the admin api routes (see above) but you won't actually get any export
functionality.

To create a new exporter you need to create a :class:`meteorpi_db.exporter.MeteorExporter` instance, this exposes a
scheduler which can be used to automatically apply any export configurations on the node and to manage the export
process for any matching :class:`meteorpi_model.FileRecord` and :class:`meteorpi_model.Event` instances.

.. code-block:: python

    from meteorpi_db.exporter import MeteorExporter
    exporter = MeteorExporter(db=db,
                              mark_interval_seconds=1,
                              max_failures_before_disable=4,
                              defer_on_failure_seconds=3)

The parameter values shown above are extremely short - they're what's used in the unit tests. Be sure to check the class
documentation for :class:`meteorpi_db.exporter.MeteorExporter` and configure this object appropriately for your
application!

At this point you have an exporter linked to your database, but its not going to run any scheduled tasks until you
actually turn the scheduler on:

.. code-block:: python

    # Start the scheduler, will use the parameters specified when constructing the exporter
    exporter.scheduler.start()

The scheduler is, by default, an instance of :class:`apscheduler.schedulers.background.BackgroundScheduler`, and can be
stopped and started using the methods on that class.

At the moment there is no method to restrict data exports to a particular time range. We may add this in a future
version. In the meantime the workaround would be to use the database API to mark all export configurations as inactive
to effectively pause their exports, then mark them as active again to re-enable. Testing suggests that the load imposed
by the data replication process is relatively light, so it should be possible to simply leave the system active at all
times.

WSGI Application Scripts
^^^^^^^^^^^^^^^^^^^^^^^^

Your HTTP server will provide a mechanism to map a subset of its URL space to a WSGI application. We have used Apache
HTTPD and LigHTTPD, both of which require some extra lines of code. For convenience, skeleton WSGI application scripts
for these two servers are shown below (although note that you will definitely want to customise these, in particular,
again, the export parameters - in fact you may well want to remove some capabilities entirely).

Apache HTTPD
------------

Apache, configured with mod_wsgi, uses a regular Python script to set up its application. The WSGI app object must be
exposed as a value named 'application'. Note that this script also includes the necessary initial lines to run from a
virtual environment, this is strongly recommended:

.. code-block:: python

    activate_this = '/home/meteorpi/meteor-env/bin/activate_this.py'
    execfile(activate_this, dict(__file__=activate_this))

    from meteorpi_db import MeteorDatabase
    from meteorpi_db.exporter import MeteorExporter
    from meteorpi_server import MeteorApp, admin_api, importer_api, query_api

    # Configure and create database and server objects
    db_path = 'localhost:/var/lib/firebird/2.5/data/meteorpi.db'
    file_store_path = '/home/meteorpi/meteorpi_files'
    db = MeteorDatabase(db_path=db_path, file_store_path=file_store_path)
    meteor_app = MeteorApp(db=db)

    # Add all routes
    admin_api.add_routes(meteor_app=meteor_app)
    importer_api.add_routes(meteor_app=meteor_app)
    query_api.add_routes(meteor_app=meteor_app)

    # Configure overly eager exporter - change these times!
    exporter = MeteorExporter(db=db,
                              mark_interval_seconds=1,
                              max_failures_before_disable=4,
                              defer_on_failure_seconds=3)
    exporter.scheduler.start()

    # Expose WSGI application as 'application'
    application = meteor_app.app

LigHTTPD
--------

This server uses a FastCGI to WSGI bridge, and requires slightly more setup in the Python script. In particular, it's
necessary to construct an actual server process rather than simply passing through the WSGI application object. The
LigHTTPD server then connects to this server process using an internal mechanism (OS dependent). As before, we run in a
virtual environment for sanity, but this time we do so by explicitly specifying the Python executable in the hash-bang
at the head of the file.

This method requires an additional package installation of the **flup** server (i.e. 'pip install flup' from within the
virtual environment).

.. code-block:: python

    #!/home/meteorpi/meteor-env/bin/python
    from flup.server.fcgi import WSGIServer

    from meteorpi_db import MeteorDatabase
    from meteorpi_db.exporter import MeteorExporter
    from meteorpi_server import MeteorApp, admin_api, importer_api, query_api

    # Configure and create database and server objects
    db_path = 'localhost:/var/lib/firebird/2.5/data/meteorpi.db'
    file_store_path = '/home/meteorpi/meteorpi_files'
    db = MeteorDatabase(db_path=db_path, file_store_path=file_store_path)
    meteor_app = MeteorApp(db=db)

    # Add all routes
    admin_api.add_routes(meteor_app=meteor_app)
    importer_api.add_routes(meteor_app=meteor_app)
    query_api.add_routes(meteor_app=meteor_app)

    # Configure overly eager exporter - change these times!
    exporter = MeteorExporter(db=db,
                              mark_interval_seconds=1,
                              max_failures_before_disable=4,
                              defer_on_failure_seconds=3)
    exporter.scheduler.start()

    # Start the WSGI server
    if __name__ == '__main__':
        WSGIServer(meteor_app.app).run()

