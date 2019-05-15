#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# db_import.py
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

import os
import uuid
import glob
import time
import pigazing_db
import pigazing_model as mp
import mod_log
from mod_log import log_txt, get_utc
import mod_daytimejobs
from pigazing_helpers import settings_read
import installation_info

elephant

# Look up the username we use to add entries into the database
user = settings_read.settings['pigazingUser']

# Dictionary of the observatory statuses of observatories we have seen
obstories_seen = {}


def get_obstory_name_from_id(db, obstory_id):
    global obstories_seen
    if obstory_id in obstories_seen:
        return obstories_seen[obstory_id]['name']
    obstory_info = db.get_obstory_from_id(obstory_id)
    obstories_seen[obstory_id] = obstory_info
    return obstory_info['name']


def dict_tree_append(dict_root, dict_path, value):
    d = dict_root
    for subdict_name in dict_path[:-1]:
        if subdict_name not in d:
            d[subdict_name] = {}
        d = d[subdict_name]
    leaf_name = dict_path[-1]
    if leaf_name not in d:
        d[leaf_name] = []
    d[leaf_name].append(value)


# Take a dictionary of metadata keys and values (metadict), and turn them into a list of pigazing_model.Meta objects
def metadata_to_object_list(db_handle, obs_time, obs_id, meta_dict):
    metadata_objs = []
    for meta_field in meta_dict:
        value = meta_dict[meta_field]

        # Short string fields get stored as string metadata (up to 64kB, or just under)
        if type(value) != str or len(value) < 65500:
            metadata_objs.append(mp.Meta("pigazing:" + meta_field, meta_dict[meta_field]))

        # Long strings are turned into separate files
        else:
            fname = os.path.join("/tmp", str(uuid.uuid4()))
            open(fname, "w").write(value)
            db_handle.register_file(file_path=fname, mime_type="application/json",
                                    semantic_type=meta_field, file_time=obs_time,
                                    file_meta=[], observation_id=obs_id, user_id=user)
    return metadata_objs


# Take a file path, and extract the file's semantic type, using the fact that image filenames have the form
# date_obstoryId_typeCode
def local_filename_to_semantic_type(fname):
    # Input e.g. timelapse_img_processed/20150505/20150505220000_obstoryId_BS0.png
    #  -->       timelapse/BS0

    path = [fname.split("_")[0]]  # e.g. "timelapse"
    for ext in os.path.split(fname)[1][:-4].split("_")[2:]:  # e.g. ["BS0"]
        if ext[-1] == "0":
            continue
        elif ext == "BS1":
            path.append("bgrdSub")
        elif ext == "LC1":
            path.append("lensCorr")
        else:
            path.append(ext)
    return "pigazing:" + ("/".join(path))


def database_import(db):
    # Change into the directory where data files are kept
    cwd = os.getcwd()
    os.chdir(settings_read.settings['dataPath'])

    # Lists of high water marks, showing where we've previously got up to in importing observations
    hwm_old = {}  # hwm_old[obstory_id] = old "import" high water mark
    hwm_new = {}  # hwm_new[obstory_id] = new "import" high water mark

    # A list of the trigger observation IDs we've created
    trigger_obs_list = {}  # trigger_obs_list[obstory_id][utc] = observation_id

    # A list of the still image observation IDs we've created
    still_img_obs_list = {}

    # Loop over all of the video files and images we've created locally. For each one, we create a new observation
    # object if there are no other files from the same observatory with the same time stamp.

    # We ignore trigger images if there's no video file with the same time stamp.
    for [glob_pattern, observation_list, mime_type, obs_type, create_new_observations] in [
        ["triggers_vid_processed/*/*.mp4", trigger_obs_list, "video/mp4", "movingObject", True],
        ["timelapse_img_processed/*/*.png", still_img_obs_list, "image/png", "timelapse", True],
        ["triggers_img_processed/*/*.png", trigger_obs_list, "image/png", "", False]]:

        # Create a list of all the files which match this particular wildcard
        file_list = glob.glob(glob_pattern)
        file_list.sort()
        logger.info("Registering files which match the wildcard <%s> -- %d files." % (glob_pattern, len(file_list)))

        # Loop over all the files
        for file_name in file_list:
            file_stub = file_name[:-4]
            utc = mod_log.filename_to_utc(file_name) + 0.01

            # Local images and video all have meta data in a file with a .txt file extension
            meta_file = "%s.txt" % file_stub  # File containing metadata
            meta_dict = mod_daytimejobs.file_to_dict(meta_file)  # Dictionary of image metadata
            assert "obstoryId" in meta_dict, "File <%s> does not have a obstoryId set." % file_name

            # Get the ID and name of the observatory that is responsible for this file
            obstory_id = meta_dict["obstoryId"]
            obstory_name = get_obstory_name_from_id(db=db, obstory_id=obstory_id)
            if obstory_id not in hwm_old:
                hwm_old[obstory_id] = db.get_high_water_mark(mark_type="import",
                                                             obstory_name=obstory_name)
                if hwm_old[obstory_id] is None:
                    hwm_old[obstory_id] = 0
                hwm_new[obstory_id] = hwm_old[obstory_id]

            # If this file is older than the pre-existing high water mark for files we've imported, ignore it
            # We've probably already imported it before
            if utc < hwm_old[obstory_id]:
                continue

            print("Registering file <%s>, with obstoryId <%s>." % (file_name, obstory_id))

            # See if we already have an observation with this time stamp. If not, create one
            created_new_observation = False
            if not ((obstory_id in observation_list) and (utc in observation_list[obstory_id])):
                if not create_new_observations:
                    continue
                obs_obj = db.register_observation(obstory_name=obstory_name, obs_time=utc,
                                                  obs_type=obs_type, user_id=user,
                                                  obs_meta=[])
                obs_id = obs_obj.id
                dict_tree_append(observation_list, [obstory_id, utc], obs_id)
                created_new_observation = True
                print("Created new observation with ID <%s>." % obs_id)
            else:
                obs_id = observation_list[obstory_id][utc]

            # Compile a list of metadata objects to associate with this file
            metadata_objs = metadata_to_object_list(db, utc, obs_id, meta_dict)

            # If we've newly created an observation object for this file, we transfer the file's metadata
            # to the observation as well
            if created_new_observation:
                for metadata_obj in metadata_objs:
                    db.set_observation_metadata(user, obs_id, metadata_obj)

            # Import the file itself into the database
            semantic_type = local_filename_to_semantic_type(file_name)
            db.register_file(file_path=file_name, user_id=user, mime_type=mime_type,
                             semantic_type=semantic_type,
                             file_time=utc, file_meta=metadata_objs,
                             observation_id=obs_id)

            # Update this observatory's "import" high water mark to the time of the file just imported
            hwm_new[obstory_id] = max(hwm_new[obstory_id], utc)

    os.chdir(cwd)

    # Now do some housekeeping tasks on the local database

    # Create a status log file for this observatory (so the health of this system can be checked remotely)

    # Use a file in /tmp to record the latest time we created a log file. It contains a unix time.
    last_update_filename = "/tmp/obstoryStatus_last"
    last_update_time = 0
    try:
        last_update_time = float(open(last_update_filename, "r").read())
    except IOError:
        pass
    except OSError:
        pass
    except ValueError:
        pass

    # Only create a new log file if we haven't created one within the past 12 hours
    if mod_log.get_utc() - last_update_time > 12 * 3600:
        # Give the log file a human-readable filename
        log_file_name = "/tmp/obstoryStatus_" + time.strftime("%Y%m%d", time.gmtime(get_utc())) + ".log"
        os.system("./observatoryStatusLog.sh > %s" % log_file_name)

        # Create an observation object to associate with this log file
        logfile_obs = db.register_observation(obstory_name=installation_info.local_conf['observatoryName'],
                                              user_id=user,
                                              obs_time=mod_log.get_utc(),
                                              obs_type="logging",
                                              obs_meta=[]
                                              )

        # Register the log file in the database and associate it with the observation above
        db.register_file(file_path=log_file_name, user_id=user, mime_type="text/plain",
                         semantic_type="logfile",
                         file_time=get_utc(), file_meta=[],
                         observation_id=logfile_obs.id)

        # Update the local record of when we last created a log file observation
        open(last_update_filename, "w").write("%s" % mod_log.get_utc())

    # Remove old data from the local database, if it is older than the local data lifetime
    db.clear_database(obstory_names=[installation_info.local_conf['observatoryName']],
                      tmin=0,
                      tmax=get_utc() - 24 * 2400 * installation_info.local_conf['dataLocalLifetime'])

    # Update the "import" high water marks for each obstory_name
    for obstory_id in list(hwm_new.keys()):
        obstory_name = get_obstory_name_from_id(db=db, obstory_id=obstory_id)
        db.set_high_water_mark(obstory_name=obstory_name,
                               mark_type="import",
                               time=hwm_new[obstory_id]
                               )

    # Commit our changes to the database
    db.commit()
    os.chdir(cwd)
    return


# Do import into firebird right away if we're run as a script
if __name__ == "__main__":
    _db = pigazing_db.MeteorDatabase(settings_read.settings['dbFilestore'])
    database_import(_db)
