#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# listExportStatus.py
#
# -------------------------------------------------
# Copyright 2015-2019 Dominic Ford
#
# This file is part of Pi Gazing.
#
# Pi Gazing is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pi Gazing is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pi Gazing.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

"""
List the status of exporting data to external servers
"""


from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def list_export_status():
    # Open connection to image archive
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    sql = db.con

    sql.execute("SELECT * FROM archive_exportConfig;")
    export_configs = sql.fetchall()

    for config in export_configs:
        heading = "{} (UID {})".format(config['exportName'], config['exportConfigId'])
        print("\n{}\n{}\n\n".format(heading, "-" * len(heading)))

        if config['active']:
            print("  * Active")
        else:
            print("  * Disabled")
        n_total = n_pending = -1

        if config['exportType'] == "metadata":
            sql.execute("SELECT COUNT(*) FROM archive_metadataExport;")
            n_total = sql.fetchall()[0]['COUNT(*)']
            sql.execute("SELECT COUNT(*) FROM archive_metadataExport WHERE exportState>0;")
            n_pending = sql.fetchall()[0]['COUNT(*)']

        elif config['exportType'] == "observation":
            sql.execute("SELECT COUNT(*) FROM archive_observationExport;")
            n_total = sql.fetchall()[0]['COUNT(*)']
            sql.execute("SELECT COUNT(*) FROM archive_observationExport WHERE exportState>0;")
            n_pending = sql.fetchall()[0]['COUNT(*)']

        elif config['exportType'] == "file":
            sql.execute("SELECT COUNT(*) FROM archive_fileExport;")
            n_total = sql.fetchall()[0]['COUNT(*)']
            sql.execute("SELECT COUNT(*) FROM archive_fileExport WHERE exportState>0;")
            n_pending = sql.fetchall()[0]['COUNT(*)']

        print("  * {:9d} jobs in export table".format(n_total))
        print("  * {:9d} jobs still to be done".format(n_pending))


if __name__ == "__main__":
    list_export_status()
