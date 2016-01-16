#!../../virtual-env/bin/python
# dbImport.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
import uuid
import glob
import time
import meteorpi_db
import meteorpi_model as mp
import mod_log
from mod_log import log_txt, get_utc
import mod_settings
import installation_info

db = meteorpi_db.MeteorDatabase(mod_settings.settings['dbFilestore'])


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


def metadata_to_db(db_handle, file_time, obstory_name, file_stub, metadict):
    metadata_objs = []
    metadata_files = []
    for metafield in metadict:
        value = metadict[metafield]
        if type(value) != str or len(value) < 250:
            metadata_objs.append(mp.Meta(metafield, metadict[metafield]))
        else:
            fname = os.path.join("/tmp", str(uuid.uuid4()))
            open(fname, "w").write(value)
            file_obj = db_handle.register_file(file_path=fname, mime_type="application/json",
                                               semantic_type=metafield, file_time=file_time,
                                               file_metas=[], obstory_id=obstory_name, file_name=os.path.split(fname)[1])
            metadata_files.append(file_obj)
    return [metadata_objs, metadata_files]


def local_filename_to_semantic_type(fname):
    # Input e.g. timelapse_img_processed/20150505/20150505220000_cameraId_BS0.png
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
    return "/".join(path)


def database_import():
    global db

    cwd = os.getcwd()
    os.chdir(mod_settings.settings['dataPath'])

    hwm_old = {}
    hwm_new = {}

    # Create list of files and events we are importing
    dirs = ["timelapse_img_processed", "triggers_img_processed"]
    files = {}
    imgs = {}
    for dirname in dirs:
        files[dirname] = glob.glob(os.path.join(dirname, "*/*.png"))
        files[dirname].sort()

    trigger_list = glob.glob("triggers_vid_processed/*/*.mp4")
    trigger_list.sort()

    # Make list of trigger times
    trigger_times = []
    for fname in trigger_list:
        utc = mod_log.filename_to_utc(fname) + 0.01
        trigger_times.append(utc)

    # Import still images
    for dirname in dirs:
        for fname in files[dirname]:
            fstub = fname[:-4]
            utc = mod_log.filename_to_utc(fname) + 0.01
            # Video analysis may veto an object after producing trigger maps.
            # Do not import these orphan files into the database.
            if (dirname == "triggers_img_processed") and (utc not in trigger_times):
                continue
            metafile = "%s.txt" % fstub  # File containing metadata
            metadict = mod_hwm.fileToDB(metafile)  # Dictionary of image metadata
            assert "cameraId" in metadict, "Timelapse photograph <%s> does not have a cameraId set." % fname
            camera_id = metadict["cameraId"]
            if camera_id not in hwm_old:
                hwm_new[camera_id] = hwm_old[camera_id] = db.get_high_water_mark(camera_id)
            if utc < hwm_old[camera_id]:
                continue
            file_name = os.path.split(fname)[1]
            [metadata_objs, metadata_files] = metadata_to_db(db, utc, camera_id, file_name,
                                                             metadict)  # List of metadata objects
            semantic_type = local_filename_to_semantic_type(fname)
            log_txt("Registering file <%s>, with cameraId <%s>" % (fname, camera_id))
            file_obj = db.register_file(file_path=fname, mime_type="image/png",
                                        semantic_type=semantic_type,
                                        file_time=utc, file_metas=metadata_objs,
                                        camera_id=camera_id,
                                        file_name=file_name)
            if os.path.exists(metafile):
                os.remove(metafile)  # Clean up metadata files that we've finished with
            dict_tree_append(imgs, [dirname, utc], file_obj)
            hwm_new[camera_id] = max(hwm_new[camera_id], utc)

    # Import trigger events
    for fname in trigger_list:
        fstub = fname[:-4]
        utc = mod_log.filename_to_utc(fname) + 0.01
        metafile = "%s.txt" % fstub  # File containing metadata
        metadict = mod_hwm.fileToDB(metafile)  # Dictionary of image metadata
        assert "cameraId" in metadict, "Trigger video <%s> does not have a cameraId set." % fname
        camera_id = metadict["cameraId"]
        if camera_id not in hwm_old:
            hwm_new[camera_id] = hwm_old[camera_id] = db.get_high_water_mark(camera_id)
        if utc < hwm_old[camera_id]:
            continue
        file_name = os.path.split(fname)[1]
        [metadata_objs, metadata_files] = metadata_to_db(db, utc, camera_id, file_name,
                                                         metadict)  # List of metadata objects
        semantic_type = local_filename_to_semantic_type(fname)
        file_objs = [db.register_file(file_path=fname, mime_type="video/mp4",
                                      semantic_type=semantic_type,
                                      file_time=utc, file_metas=metadata_objs,
                                      camera_id=camera_id,
                                      file_name=file_name)]

        if "triggers_img_processed" in imgs:
            if utc in imgs["triggers_img_processed"]:
                file_objs.extend(imgs["triggers_img_processed"][utc])
        file_objs.extend(metadata_files)
        log_txt("Registering event <%s>, with cameraId <%s> and %d files" % (fname, camera_id, len(file_objs)))
        event_obj = db.register_event(camera_id=camera_id, event_time=utc,
                                      event_type="meteorpi", file_records=file_objs,
                                      event_meta=metadata_objs)
        if os.path.exists(metafile):
            os.remove(metafile)  # Clean up metadata files that we've finished with
        hwm_new[camera_id] = max(hwm_new[camera_id], utc)

    os.chdir(cwd)

    # Create a camera status log file
    os.system("./cameraStatusLog.sh > /tmp/cameraStatus.log")
    file_obj = db.register_file(file_path="/tmp/cameraStatus.log", mime_type="text/plain",
                                semantic_type="logfile",
                                file_time=get_utc(), file_metas=[],
                                camera_id=my_installation_id(),
                                file_name="cameraStatus_" + time.strftime("%Y%m%d",get_utc()) + ".log")

    # Remove old data from the local database
    db.clear_database(obstory_names=[installation_info.local_conf['observatoryName']],
                      tmin=0,
                      tmax=get_utc() - 24 * 2400 * installation_info.local_conf['dataLocalLifetime'])
    return hwm_new


# Do import into firebird right away if we're run as a script
if __name__ == "__main__":
    database_import()
