__author__ = 'tom'

import meteorpi_server
import os.path as path

"""Start a blocking server accessing meteorpi_test2 DB if run as a script"""
if __name__ == "__main__":
    server = meteorpi_server.MeteorServer(db_path='localhost:/var/lib/firebird/2.5/data/meteorpi_test2.fdb',
                          file_store_path=path.expanduser("~/meteorpi_test2_files"), port=12345)
    print 'Running blocking server (meteorpi_test2) on port {0}'.format(server.port)
    server.start()