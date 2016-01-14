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


