#!../../virtual-env/bin/python
# firebirdImport.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import glob

import meteorpi_fdb
import meteorpi_model as mp

import mod_hwm
from mod_log import logTxt
from mod_settings import *
from mod_time import *

fdb_handle = meteorpi_fdb.MeteorDatabase(DBPATH, FDBFILESTORE)


def dictTreeAppend(dict_root, dict_path, value):
    d = dict_root
    for subDictName in dict_path[:-1]:
        if subDictName not in d:
            d[subDictName] = {}
        d = d[subDictName]
    leaf_name = dict_path[-1]
    if leaf_name not in d:
        d[leaf_name] = []
    d[leaf_name].append(value)


def metadataToFDB(fdb_handle, file_time, camera_id, file_stub, metadict):
    metadata_objs = []
    metadata_files = []
    for metafield in metadict:
        value = metadict[metafield]
        if type(value) != str or len(value) < 250:
            metadata_objs.append(mp.Meta(mp.NSString(metafield, "meteorpi"), metadict[metafield]))
        else:
            fname = os.path.join("/tmp", str(uuid.uuid4()))
            open(fname, "w").write(value)
            file_obj = fdb_handle.register_file(file_path=fname, mime_type="application/json",
                                                semantic_type=mp.NSString(metafield, "meteorpi"), file_time=file_time,
                                                file_metas=[], camera_id=camera_id, file_name=os.path.split(fname)[1])
            metadata_files.append(file_obj)
    return [metadata_objs, metadata_files]


def localFilenameToSemanticType(fname):
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


def firebirdImport():
    global fdb_handle

    pid = os.getpid()
    cwd = os.getcwd()

    os.chdir(DATA_PATH)

    hwm_old = {}
    hwm_new = {}

    # Create list of files and events we are importing
    dirs = ["timelapse_img_processed", "triggers_img_processed"]
    files = {}
    imgs = {}
    for dirname in dirs:
        files[dirname] = glob.glob(os.path.join(dirname, "*/*.png"))

    trigger_list = glob.glob("triggers_vid_processed/*/*.mp4")

    # Make list of trigger times
    trigger_times = []
    for fname in trigger_list:
        utc = mod_hwm.filenameToUTC(fname)
        trigger_times.append(utc)

    # Import still images
    for dirname in dirs:
        for fname in files[dirname]:
            fstub = fname[:-4]
            utc = mod_hwm.filenameToUTC(fname)
            if (dirname == "triggers_img_processed") and (utc not in trigger_times):
                # Video analysis may veto an object after producing trigger maps.
                # Do not import these orphan files into the database.
                continue
            metafile = "%s.txt" % fstub  # File containing metadata
            metadict = mod_hwm.fileToDB(metafile)  # Dictionary of image metadata
            assert "cameraId" in metadict, "Timelapse photograph <%s> does not have a cameraId set." % fname
            camera_id = metadict["cameraId"]
            if camera_id not in hwm_old:
                hwm_new[camera_id] = hwm_old[camera_id] = datetime2UTC(fdb_handle.get_high_water_mark(camera_id))
            if utc < hwm_old[camera_id]:
                continue
            file_name = os.path.split(fname)[1]
            [metadata_objs, metadata_files] = metadataToFDB(fdb_handle, UTC2datetime(utc), camera_id, file_name,
                                                          metadict)  # List of metadata objects
            semanticType = localFilenameToSemanticType(fname)
            logTxt("Registering file <%s>, with cameraId <%s>" % (fname, camera_id))
            fileObj = fdb_handle.register_file(file_path=fname, mime_type="image/png",
                                               semantic_type=mp.NSString(semanticType, "meteorpi"),
                                               file_time=UTC2datetime(utc), file_metas=metadata_objs, camera_id=camera_id,
                                               file_name=file_name)
            if os.path.exists(metafile):
                os.remove(metafile)  # Clean up metadata files that we've finished with
            dictTreeAppend(imgs, [dirname, utc], fileObj)
            hwm_new[camera_id] = max(hwm_new[camera_id], utc)

    # Import trigger events
    for fname in trigger_list:
        fstub = fname[:-4]
        utc = mod_hwm.filenameToUTC(fname)
        metafile = "%s.txt" % fstub  # File containing metadata
        metadict = mod_hwm.fileToDB(metafile)  # Dictionary of image metadata
        assert "cameraId" in metadict, "Trigger video <%s> does not have a cameraId set." % fname
        camera_id = metadict["cameraId"]
        if camera_id not in hwm_old:
            hwm_new[camera_id] = hwm_old[camera_id] = datetime2UTC(fdb_handle.get_high_water_mark(camera_id))
        if utc < hwm_old[camera_id]:
            continue
        file_name = os.path.split(fname)[1]
        [metadata_objs, metadata_files] = metadataToFDB(fdb_handle, UTC2datetime(utc), camera_id, file_name,
                                                      metadict)  # List of metadata objects
        semanticType = localFilenameToSemanticType(fname)
        fileObjs = [fdb_handle.register_file(file_path=fname, mime_type="video/mp4",
                                             semantic_type=mp.NSString(semanticType, "meteorpi"),
                                             file_time=UTC2datetime(utc), file_metas=metadata_objs, camera_id=camera_id,
                                             file_name=file_name)]

        fileObjs.extend(imgs["triggers_img_processed"][utc])
        fileObjs.extend(metadata_files)
        logTxt("Registering event <%s>, with cameraId <%s> and %d files" % (fname, camera_id, len(fileObjs)))
        eventObj = fdb_handle.register_event(camera_id=camera_id, event_time=UTC2datetime(utc),
                                             event_type=mp.NSString("meteorpi", "meteorpi"), file_records=fileObjs,
                                             event_meta=metadata_objs)
        if os.path.exists(metafile):
            os.remove(metafile)  # Clean up metadata files that we've finished with
        hwm_new[camera_id] = max(hwm_new[camera_id], utc)

    # Update firebird hwm
    for camera_id, utc in hwm_new.iteritems():
        logTxt("Updating high water mark of camera <%s> to UTC %d (%s)" % (camera_id, utc, UTC2datetime(utc)))
        fdb_handle.set_high_water_mark(UTC2datetime(utc), camera_id)

    os.chdir(cwd)


# Do import into firebird right away if we're run as a script
if __name__ == "__main__":
    firebirdImport()
