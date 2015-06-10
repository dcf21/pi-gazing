#!/home/pi/v_env/bin/python

from flup.server.fcgi import WSGIServer
import meteorpi_server
import meteorpi_fdb

db_path = 'localhost:/var/lib/firebird/2.5/data/meteorpi.fdb'
file_store_path = '/home/pi/meteorpi_files'

db = meteorpi_fdb.MeteorDatabase(db_path=db_path, file_store_path=file_store_path)
app = meteorpi_server.build_app(db)

print app

if __name__ == '__main__':
    WSGIServer(app).run()

