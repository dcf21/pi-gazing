#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# daytimeTaskDefinitions.py
#
# -------------------------------------------------
# Copyright 2015-2020 Dominic Ford
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
This defines a set of tasks which need to be performed on Pi Gazing data during the daytime.
It is generic file processor. Each class looks for files in particular directories with particular extensions,
works out the time associated with each file from its filename, and performs predefined shell-commands on them.
"""

import glob
import logging
import multiprocessing
import subprocess
import os
import time
import json
import uuid
import numpy

from math import floor, ceil

from pigazing_helpers.dcf_ast import unix_from_jd, jd_from_unix, julian_day, inv_julian_day
from pigazing_helpers.sunset_times import sun_pos, alt_az
from pigazing_helpers.obsarchive import obsarchive_model, obsarchive_db
from pigazing_helpers import hardware_properties
from pigazing_helpers.settings_read import settings, installation_info, known_observatories

observatories_seen = {}


def check_observatory_exists(db_handle, obs_id=installation_info['observatoryId'], utc=0):
    """
    If an observatory doesn't exist in the database, with all metadata fields set at the unix time <time>, create an
    entry for it with default settings based on the data in <configuration_global/known_observatories.xml>.

    :param db_handle:
        Database connection handle
    :param obs_id:
        The ID of the observatory to create
    :param utc:
        The unix time stamp at which the observatory must be set up, with all required metadata fields present.
    :return:
        None
    """

    # If this observatory doesn't exist in the database, create it now with information from installation_info
    if not db_handle.has_obstory_id(obs_id):
        logging.info("Observatory '{}' is not set up. Using default settings.".format(obs_id))

        # Make sure that observatory exists in known_observatories list
        assert obs_id in known_observatories

        db_handle.register_obstory(obstory_id=obs_id,
                                   obstory_name=known_observatories[obs_id]['observatoryName'],
                                   latitude=known_observatories[obs_id]['latitude'],
                                   longitude=known_observatories[obs_id]['longitude'],
                                   owner=known_observatories[obs_id]['owner'])

    # Look up what metadata fields are set for this observatory
    metadata = db_handle.get_obstory_status(obstory_id=obs_id, time=utc)

    # Instantiate database of all the hardware we have specifications for
    hw = hardware_properties.HardwareProps(
        path=os.path.join(settings['pythonPath'], "..", "configuration_global", "camera_properties")
    )

    # If we don't have a specified software version, ensure we have it now
    if ('software_version' not in metadata) or (metadata['software_version'] != settings['softwareVersion']):
        db_handle.register_obstory_metadata(obstory_id=obs_id,
                                            key="software_version",
                                            value=settings['softwareVersion'],
                                            metadata_time=utc,
                                            time_created=time.time(),
                                            user_created=settings['pigazingUser'])

    # If we don't have complete metadata regarding the camera, ensure we have it now
    if 'camera' not in metadata:
        hw.update_camera(db=db_handle,
                         obstory_id=obs_id,
                         utc=utc,
                         name=known_observatories[obs_id]['defaultCamera'])

    # If we don't have complete metadata regarding the lens, ensure we have it now
    if 'lens' not in metadata:
        hw.update_lens(db=db_handle,
                       obstory_id=obs_id,
                       utc=utc,
                       name=known_observatories[obs_id]['defaultLens'])

    # If we don't have a clipping region, define one now
    if 'clipping_region' not in metadata:
        db_handle.register_obstory_metadata(obstory_id=obs_id,
                                            key="clipping_region",
                                            value="[[]]",
                                            metadata_time=utc,
                                            time_created=time.time(),
                                            user_created=settings['pigazingUser'])

    # Register raspberry pi hardware version
    if os.path.exists("/sys/firmware/devicetree/base/model"):
        hardware_version = open("/sys/firmware/devicetree/base/model").read()
        db_handle.register_obstory_metadata(obstory_id=obs_id,
                                            key="hardware_version",
                                            value=hardware_version,
                                            metadata_time=utc,
                                            time_created=time.time(),
                                            user_created=settings['pigazingUser'])


def execute_shell_command(arguments):
    """
    Run a shell command to compete some task. Import the resulting file products into the database, and then delete
    them.

    :param arguments:
        Dictionary of the arguments associated with each command we are to run
    :return:
        None
    """

    # If we have run out of time, exit immediately
    if (arguments['must_quit_by'] is not None) and (time.time() > arguments['must_quit_by']):
        return

    # Compile a list of all of the output files we have generated
    file_inputs = []
    file_products = []

    # Loop over all the input files associated with this time stamp
    for job in arguments['job_list']:

        # If this job requires a clipping mask, we create that now
        if 'mask_file' in job['shell_command']:
            # Open connection to the database
            db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                                   db_host=installation_info['mysqlHost'],
                                                   db_user=installation_info['mysqlUser'],
                                                   db_password=installation_info['mysqlPassword'],
                                                   db_name=installation_info['mysqlDatabase'],
                                                   obstory_id=installation_info['observatoryId'])

            # Fetch observatory status
            obstory_status = db.get_obstory_status(obstory_id=arguments['obs_id'],
                                                   time=arguments['utc'])

            # Close database connection
            db.close_db()
            del db

            # Export the clipping mask to a JSON file
            mask_file = "/tmp/mask_{}_{}.txt".format(os.getpid(), str(uuid.uuid4()))
            with open(mask_file, "w") as f:
                f.write("\n\n".join(
                    ["\n".join([("%d %d" % p) for p in pointList])
                     for pointList in json.loads(obstory_status['clipping_region'])]
                )
                )
            job['mask_file'] = mask_file

        # Make settings available as string substitutions
        job['settings'] = settings

        # Make sure that output directories exist
        for output_file_wildcard in job['output_file_wildcards']:
            output_path = os.path.join(job['data_dir'],
                                       os.path.split(output_file_wildcard['wildcard'])[0]
                                       )
            os.system("mkdir -p {}".format(output_path))

        # Run the shell command
        command = job['shell_command'].format(**job)
        print(command)
        result = subprocess.run(command, shell=True, stderr=subprocess.PIPE)
        errors = result.stderr.decode('utf-8').strip()

        # Check for errors
        if errors:
            logging.error("Error processing file <{}>: <{}>".format(job['input_file'], errors))

        # Compile list of all the input files we have processed
        for item in (job['input_file'], job['input_metadata_filename']):
            if item is not None:
                file_inputs.append(item)

        # Fetch list of output files we have created
        for output_file_wildcard in job['output_file_wildcards']:
            output_path = os.path.join(job['data_dir'],
                                       output_file_wildcard['wildcard']
                                       )
            for output_file in glob.glob(output_path):
                file_products.append({
                    'filename': output_file,
                    'mime_type': output_file_wildcard['mime_type'],
                    'input_file_metadata': job['input_metadata'],
                    'propagate_metadata': job['metadata_fields_to_propagate'],
                    'metadata_files': []
                })

    # Only add anything to the database if we created some output files
    if len(file_products) > 0:
        # Open connection to the database
        db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                               db_host=installation_info['mysqlHost'],
                                               db_user=installation_info['mysqlUser'],
                                               db_password=installation_info['mysqlPassword'],
                                               db_name=installation_info['mysqlDatabase'],
                                               obstory_id=installation_info['observatoryId'])

        # Collect metadata associated with this observation
        observation_metadata = {}
        for output_file in file_products:

            # Collect metadata associated with this output file
            try:
                product_metadata_file, obstory_info, product_metadata = metadata_file_to_dict(
                    db_handle=db,
                    product_filename=output_file['filename'],
                    input_metadata=output_file['input_file_metadata'],
                    required=False
                )
            except AssertionError:
                logging.error("Invalid metadata for file <{}>".format(output_file['filename']))
                continue

            # Store metadata associated with this file
            metadata_objs = metadata_to_object_list(db_handle=db,
                                                    obs_time=arguments['utc'],
                                                    obs_id=arguments['obs_id'],
                                                    user_id=arguments['user_id'],
                                                    meta_dict=product_metadata)

            if product_metadata_file is not None:
                output_file['metadata_files'].append(product_metadata_file)

            output_file['product_metadata'] = product_metadata
            output_file['metadata_objs'] = metadata_objs
            output_file['obstory_info'] = obstory_info

            # Check which fields this file propagates to its parent observation
            for field_to_propagate in output_file['propagate_metadata']:
                if field_to_propagate in product_metadata:
                    observation_metadata[field_to_propagate] = product_metadata[field_to_propagate]

        # Turn metadata associated with this observation into database metadata objects
        metadata_objs = metadata_to_object_list(db_handle=db,
                                                obs_time=arguments['utc'],
                                                obs_id=arguments['obs_id'],
                                                user_id=arguments['user_id'],
                                                meta_dict=observation_metadata)

        # Import file products into the database
        obs_obj = db.register_observation(obstory_id=arguments['obs_id'],
                                          random_id=False,
                                          obs_time=arguments['utc'],
                                          creation_time=time.time(),
                                          obs_type=arguments['obs_type'],
                                          user_id=arguments['user_id'],
                                          obs_meta=metadata_objs,
                                          published=1, moderated=1, featured=0,
                                          ra=-999, dec=-999,
                                          field_width=None, field_height=None,
                                          position_angle=None, central_constellation=None,
                                          altitude=-999, azimuth=-999, alt_az_pa=None,
                                          astrometry_processed=None, astrometry_processing_time=None,
                                          astrometry_source=None)
        obs_id = obs_obj.id

        for output_file in file_products:
            # The semantic types which we should make the primary images of their parent observations
            primary_image_type_list = (
                'pigazing:movingObject/maximumBrightness',
                'pigazing:timelapse/backgroundSubtracted'
            )

            db.register_file(file_path=output_file['filename'],
                             user_id=output_file['obstory_info']['userId'],
                             mime_type=output_file['mime_type'],
                             semantic_type=output_file['product_metadata']['semanticType'],
                             primary_image=output_file['product_metadata']['semanticType'] in primary_image_type_list,
                             file_time=arguments['utc'],
                             file_meta=output_file['metadata_objs'],
                             observation_id=obs_id,
                             random_id=False)

        # Close connection to the database
        db.commit()
        db.close_db()
        del db

    # Delete input files
    for item in file_inputs:
        if os.path.exists(item):
            os.unlink(item)

    # Delete output files
    for item in file_products:
        if os.path.exists(item['filename']):
            os.unlink(item['filename'])
        for metadata_filename in item['metadata_files']:
            if os.path.exists(metadata_filename):
                os.unlink(metadata_filename)


observatory_information = {}


def metadata_file_to_dict(db_handle, product_filename, required, input_metadata=None):
    """
    Make a dictionary from a text file containing the metadata associated with some file product

    :param db_handle:
        Database connection handle
    :param product_filename:
        The filename of the file product whose metadata we are to read
    :param required:
        Do we require that this metadata file must exist?
    :type required:
        bool
    :param input_metadata:
        Metadata that we are to merge the contents of this file into
    :type input_metadata:
        dict
    :return:
        The filename of the metadata file, observatory info, and a dictionary of the metadata we collected
    """
    global observatory_information

    # Metadata is stored in text files which sit alongside each file product
    filename_without_extension = os.path.splitext(product_filename)[0]
    metadata_filename = "{}.txt".format(filename_without_extension)

    # Start constructing a dictionary of the metadata in the file
    output = {}

    if input_metadata is not None:
        output = {**input_metadata}

    # Make sure that the metadata file exists!
    if required:
        assert os.path.exists(metadata_filename)

    # Read the file, line by line
    if os.path.exists(metadata_filename):
        for line in open(metadata_filename):
            # Ignore blank lines and comment lines
            if line.strip() == "":
                continue
            if line[0] == "#":
                continue
            # Each line has the format <key value>
            words = line.split()
            keyword = words[0]
            val = words[1]
            # Try to convert the value to a float, but if this isn't possible, return it as a string
            try:
                val = float(val)
            except ValueError:
                pass
            output[keyword] = val

    # Make sure that essential metadata keys are defined
    assert 'obstoryId' in output
    assert 'utc' in output
    assert 'semanticType' in output

    # Look up information about the observatory which made this observation
    obs_id = output['obstoryId']

    # Make sure that we have information about this observatory
    if obs_id in observatory_information:
        obstory_info = observatory_information[obs_id]
    else:
        check_observatory_exists(db_handle=db_handle, obs_id=obs_id, utc=output['utc'])
        obstory_info = db_handle.get_obstory_from_id(obstory_id=obs_id)
        observatory_information[obs_id] = obstory_info

    # If the magic metadata key "refresh" is set, them we mark in the database that the observatory has been serviced.
    if 'refresh' in output and output['refresh']:
        db_handle.register_obstory_metadata(obstory_id=obs_id,
                                            key="refresh",
                                            value=1,
                                            metadata_time=output['utc'] - 1,
                                            time_created=time.time(),
                                            user_created=settings['pigazingUser'])

        # Recheck that all required metadata us set at the time of this observation
        check_observatory_exists(db_handle=db_handle, obs_id=obs_id, utc=output['utc'])

    # Add further metadata about the position of the Sun
    utc = output['utc']

    sun_pos_at_utc = sun_pos(utc=utc)
    sun_alt_az_at_utc = alt_az(ra=sun_pos_at_utc[0], dec=sun_pos_at_utc[1],
                               utc=utc,
                               latitude=obstory_info['latitude'],
                               longitude=obstory_info['longitude']
                               )
    output['sunRA'] = sun_pos_at_utc[0]
    output['sunDecl'] = sun_pos_at_utc[1]
    output['sunAlt'] = sun_alt_az_at_utc[0]
    output['sunAz'] = sun_alt_az_at_utc[1]

    # Return the dictionary of metadata
    return metadata_filename, obstory_info, output


# Function for turning filenames into Unix times
def filename_to_utc(filename):
    """
    Function for turning filenames of observations into Unix times. We have a standard filename convention, where
    all observations start with the UTC date and time that the observation was made.

    :param filename:
        Filename of observation
    :type filename:
        str
    :return:
        The unix time when the observation was made
    """

    filename = os.path.split(filename)[1]
    if not filename.startswith("20"):
        return -1
    year = int(filename[0:4])
    mon = int(filename[4:6])
    day = int(filename[6:8])
    hour = int(filename[8:10])
    minute = int(filename[10:12])
    sec = int(filename[12:14])
    return unix_from_jd(julian_day(year, mon, day, hour, minute, sec))


def fetch_time_string_from_filename(filename):
    """
    Fetch a string describing the day when an observation was made, based on its filename. We have a standard filename
    convention, where all observations start with the UTC date and time that the observation was made.

    :param filename:
        Filename of observation
    :type filename:
        str
    :return:
        The day when the observation was made
    """

    filename = os.path.split(filename)[1]
    if not filename.startswith("20"):
        return None
    utc = filename_to_utc(filename)
    utc -= 12 * 3600
    [year, month, day, hour, minutes, sec] = inv_julian_day(jd_from_unix(utc))
    return "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(int(year), int(month), int(day),
                                                         int(hour), int(minutes), int(sec))


def metadata_to_object_list(db_handle, obs_time, obs_id, user_id, meta_dict):
    """
    Take a dictionary of metadata keys and their values, and turn them into a list of obsarchive_model.Meta objects.

    :param db_handle:
        Database connection handle
    :param obs_time:
        The time stamp of the observation with this metadata
    :param obs_id:
        The publicId of the observation with this metadata
    :param user_id:
        The username of the user who owns this observation
    :param meta_dict:
        Dictionary of metadata associated with this observation
    :return:
        A list of obsarchive_model.Meta objects
    """

    metadata_objs = []
    for meta_field in meta_dict:
        value = meta_dict[meta_field]

        # Short string fields get stored as string metadata (up to 64kB, or just under)
        if type(value) != str or len(value) < 65500:
            metadata_objs.append(obsarchive_model.Meta("pigazing:" + meta_field, meta_dict[meta_field]))

        # Long strings are turned into separate files
        else:
            filename = os.path.join("/tmp", str(uuid.uuid4()))
            open(filename, "w").write(value)
            db_handle.register_file(file_path=filename, mime_type="application/json",
                                    semantic_type=meta_field, file_time=obs_time,
                                    file_meta=[], observation_id=obs_id, user_id=user_id)
    return metadata_objs


class TaskRunner:
    """
    Generic class describing a task that we need to perform on a set of files.

    Descendants of this class specify the wildcard that we can use to find the files we need to operate on, and the
    format of the shell command we need to run on each file.
    """

    def __init__(self, must_quit_by=None):
        """
        Initialise task runner.

        :param must_quit_by:
            The unix time by which we need to stop running tasks.
        """
        self.must_quit_by = must_quit_by
        self.task_list = []

    def fetch_job_list_by_time_stamp(self):
        """
        Fetch list of input files we need to operate on, and sort them by time stamp. Files with the same time stamp
        correspond to the same "observation" and so will be grouped together in the database.

        :return:
            None
        """

        global observatories_seen

        # Open connection to the database
        db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                               db_host=installation_info['mysqlHost'],
                                               db_user=installation_info['mysqlUser'],
                                               db_password=installation_info['mysqlPassword'],
                                               db_name=installation_info['mysqlDatabase'],
                                               obstory_id=installation_info['observatoryId'])

        # Path to data directory
        data_dir = os.path.join(settings['pythonPath'], '../datadir/')

        # Fetch list of input files, and sort them by time stamp
        jobs_by_time = {}
        for glob_pattern in self.glob_patterns():
            for input_file in sorted(glob.glob(os.path.join(data_dir, glob_pattern['wildcard']))):

                # Collect metadata associated with this input file
                try:
                    input_metadata_file, obstory_info, input_metadata = metadata_file_to_dict(
                        db_handle=db,
                        product_filename=input_file,
                        required=True
                    )
                except AssertionError:
                    logging.error("Invalid metadata for file <{}>".format(input_file))
                    continue

                # Properties that specify what command to run to complete this task, and what output it produces
                job_descriptor = {
                    'input_file': input_file,
                    'input_file_without_extension': os.path.splitext(os.path.split(input_file)[1])[0],
                    'input_metadata_filename': input_metadata_file,
                    'input_metadata': input_metadata,
                    'metadata_fields_to_propagate': self.propagate_metadata_to_observation(metadata=input_metadata),
                    'shell_command': self.shell_command(),
                    'data_dir': data_dir,
                    'h264_encoder': 'libav' if settings['i_am_a_rpi'] else 'libav',
                    'output_file_wildcards': self.output_file_wildcards(input_file)
                }

                # Work out the time stamp of this job from the input file's filename
                obstory_id = input_metadata['obstoryId']
                utc = input_metadata['utc']
                time_stamp_string = "{:014.1f}_{}".format(filename_to_utc(filename=input_file),
                                                          obstory_id)

                # If we haven't had any jobs at the time stamp before, create an empty list for this time stamp
                if time_stamp_string not in jobs_by_time:
                    jobs_by_time[time_stamp_string] = {
                        'obs_id': obstory_id,
                        'utc': utc,
                        'obs_type': glob_pattern['obs_type'],
                        'user_id': obstory_info['userId'],
                        'must_quit_by': self.must_quit_by,
                        'job_list': []
                    }

                # Append this job to list of others with the same time stamp
                jobs_by_time[time_stamp_string]['job_list'].append(job_descriptor)

                # Record that we've seen this observatory at this time
                if obstory_id not in observatories_seen:
                    observatories_seen[obstory_id] = {
                        'utc_min': utc,
                        'utc_max': utc
                    }

                if utc < observatories_seen[obstory_id]['utc_min']:
                    observatories_seen[obstory_id]['utc_min'] = utc
                if utc > observatories_seen[obstory_id]['utc_max']:
                    observatories_seen[obstory_id]['utc_max'] = utc

        # Close database connection
        db.commit()
        db.close_db()

        return jobs_by_time

    def fetch_job_list(self):
        """
        Populate the class variable <self.task_list> with a list of all the jobs we need to do.

        Each job is defined as a dictionary, containing all the arguments that we need to pass to
        <execute_shell_command>.

        :return:
            None
        """
        # Sort list of input files by time stamp
        jobs_by_time = self.fetch_job_list_by_time_stamp()

        # Make list of all time stamps
        time_stamps = sorted(jobs_by_time.keys())

        # Sort all jobs into a list
        self.task_list = [jobs_by_time[time_stamp] for time_stamp in time_stamps]

        # Write update on our progress
        logging.info("Starting job group <{}>. Running {} tasks.".format(self.__class__.__name__, len(self.task_list)))

    @staticmethod
    def glob_patterns():
        """
        Return the string that we need to glob (inside the <datadir> directory) to find all the files this task needs
        to operate on.

        :return:
            string filename wildcard
        """
        return []

    def execute_tasks(self):
        """
        Execute this task on all of the input files which we have identified.

        :return:
            None
        """
        self.fetch_job_list()

        pool = multiprocessing.Pool(processes=self.maximum_concurrency())
        pool.map(func=execute_shell_command, iterable=self.task_list)
        pool.close()

    @staticmethod
    def maximum_concurrency():
        """
        The maximum number of jobs we are allowed to do in parallel for this task.

        :return:
            integer maximum number of threads allowed
        """
        return 1

    @staticmethod
    def shell_command():
        """
        The shell command that we run to perform this task. This string is passed through the <str.format> method
        with the dictionary in <self.task_list> as its arguments, allowing access to the job's properties.

        :return:
            string shell command, with substitution places marked using <str.format> syntax
        """
        return None

    @staticmethod
    def output_file_wildcards(input_file):
        """
        The filename wildcard that we use to get from an input file to all of the products that were produced by
        running this task on that input file. This allows us to identify which output files we created, and therefore
        need to import into the database.

        :param input_file:
            The filename of the input file this task is operating on
        :return:
            A list of wildcards that we need to glob to find the output products that we created
        """
        return []

    @staticmethod
    def propagate_metadata_to_observation(metadata):
        """
        Return a list of metadata properties that we should propagate from output files into their parent observation.
        :param metadata:
            The metadata on this output file
        :return:
            A list of metadata keys to propagate to the parent observation
        """
        return []


class MergeOutputIntoSingleObservations(TaskRunner):
    """
    Merge the jobs in several task runners into a single task runner. This means that output from the various tasks
    which share common time stamps will be incorporated into common observations in the database.
    """

    def __init__(self, sub_task_classes, must_have_semantic_types=None):
        self.sub_task_classes = sub_task_classes
        self.must_have_semantic_types = must_have_semantic_types

        if self.must_have_semantic_types is None:
            self.must_have_semantic_types = ()

        self.sub_tasks = None

        super().__init__()

    def __call__(self, must_quit_by=None):
        self.must_quit_by = must_quit_by
        return self

    def fetch_job_list_by_time_stamp(self):
        """
        Build a list of jobs which need to be done, sorted by time stamp. We merge all of the jobs which need doing
        by each of the sub tasks into a single list.

        :return:
            Dictionary of job descriptors, with time stamp strings as the dictionary key
        """
        # Instantiate sub tasks
        self.sub_tasks = []
        for sub_task_class in self.sub_task_classes:
            self.sub_tasks.append(
                sub_task_class(must_quit_by=self.must_quit_by)
            )

        # Fetch list of input files, and sort them by time stamp
        jobs_by_time = {}

        for sub_task in self.sub_tasks:
            # Fetch a list of the new jobs to be done
            new_jobs_by_time = sub_task.fetch_job_list_by_time_stamp()

            # Loop over all the time stamps of the new jobs
            for time_stamp, new_jobs in new_jobs_by_time.items():

                # If we haven't had any jobs at the time stamp before, create an empty list for this time stamp
                if time_stamp not in jobs_by_time:
                    jobs_by_time[time_stamp] = new_jobs

                # Merge this job to list of others with the same time stamp
                else:
                    jobs_by_time[time_stamp]['job_list'].extend(new_jobs['job_list'])

        # Purge any jobs that don't have files with all the required semantic types
        for time_stamp in list(jobs_by_time):
            required_file_types = list(self.must_have_semantic_types)
            for file in jobs_by_time[time_stamp]['job_list']:
                semantic_type = file['input_metadata']['semanticType']
                while semantic_type in required_file_types:
                    required_file_types.remove(semantic_type)

            # If a required semantic type is missing, purge this observation
            if len(required_file_types) > 0:
                del jobs_by_time[time_stamp]

        # Return combined list of jobs
        return jobs_by_time

    def output_file_wildcards(self, input_file):
        output = []
        for sub_task in self.sub_tasks:
            output.extend(sub_task.output_file_wildcards(input_file))
        return output


class AnalyseRawVideos(TaskRunner):
    @staticmethod
    def glob_patterns():
        return [
            {
                'wildcard': 'raw_video/*.h264',
                'obs_type': 'pigazing:'
            }
        ]

    @staticmethod
    def shell_command():
        return """
{settings[binaryPath]}/debug/analyseH264_{h264_encoder} \
         --input \"{input_file}\" \
         --obsid \"{input_metadata[obstoryId]}\" \
         --time-start {input_metadata[utc_start]} \
         --fps {input_metadata[fps]} \
         --mask \"{mask_file}\"
        """

    @staticmethod
    def output_file_wildcards(input_file):
        return []


class TimelapseRawImages(TaskRunner):
    """
    A Task Runner which converts raw RGB image files generated during each night's observation into PNG images.
    """

    @staticmethod
    def glob_patterns():
        return [
            {
                'wildcard': 'analysis_products/timelapse_nonlive/*.rgb',
                'obs_type': 'pigazing:timelapse/'
            }, {
                'wildcard': 'analysis_products/timelapse_live/*.rgb',
                'obs_type': 'pigazing:timelapse/'
            }
        ]

    @staticmethod
    def shell_command():
        return """
{settings[imageProcessorPath]}/debug/rawimg2png \
         --input \"{input_file}\" \
         --output \"{data_dir}/analysis_products_reduced/timelapse_img/{input_file_without_extension}\" \
         --noise {input_metadata[stackNoiseLevel]}
         """

    @staticmethod
    def output_file_wildcards(input_file):
        input_file_without_extension = os.path.splitext(os.path.split(input_file)[1])[0]
        return [
            {
                'wildcard': 'analysis_products_reduced/timelapse_img/{}.png'.format(input_file_without_extension),
                'mime_type': 'image/png'
            }
        ]

    @staticmethod
    def propagate_metadata_to_observation(metadata):
        if metadata['semanticType'] == 'pigazing:timelapse/backgroundSubtracted':
            return ['skyClarity']
        else:
            return []


class TriggerRawImages(TaskRunner):
    """
    A Task Runner which converts raw RGB image files generated during each night's observation into PNG images.
    """

    @staticmethod
    def glob_patterns():
        return [
            {
                'wildcard': 'analysis_products/triggers_nonlive/*.rgb',
                'obs_type': 'pigazing:movingObject/'
            }, {
                'wildcard': 'analysis_products/triggers_live/*.rgb',
                'obs_type': 'pigazing:movingObject/'
            }
        ]

    @staticmethod
    def shell_command():
        return """
{settings[imageProcessorPath]}/debug/rawimg2png \
         --input \"{input_file}\" \
         --output \"{data_dir}/analysis_products_reduced/triggers_img1/{input_file_without_extension}\" \
         --noise {input_metadata[stackNoiseLevel]}
         """

    @staticmethod
    def output_file_wildcards(input_file):
        input_file_without_extension = os.path.splitext(os.path.split(input_file)[1])[0]
        return [
            {
                'wildcard': 'analysis_products_reduced/triggers_img1/{}.png'.format(input_file_without_extension),
                'mime_type': 'image/png'
            }
        ]


class TriggerRawVideos(TaskRunner):
    """
    A TaskRunner which converts raw .vid files generated during each night's observation, and compresses them into mp4
    files.
    """

    @staticmethod
    def glob_patterns():
        return [
            {
                'wildcard': 'analysis_products/triggers_nonlive/*.vid',
                'obs_type': 'pigazing:movingObject/'
            }, {
                'wildcard': 'analysis_products/triggers_live/*.vid',
                'obs_type': 'pigazing:movingObject/'
            }
        ]

    @staticmethod
    def shell_command():
        return """
{settings[imageProcessorPath]}/debug/rawvid2mp4_{h264_encoder} \
         --input \"{input_file}\" \
         --output \"{data_dir}/analysis_products_reduced/triggers_vid/{input_file_without_extension}.mp4\"
         """

    @staticmethod
    def output_file_wildcards(input_file):
        input_file_without_extension = os.path.splitext(os.path.split(input_file)[1])[0]
        return [
            {
                'wildcard': 'analysis_products_reduced/triggers_vid/{}.mp4'.format(input_file_without_extension),
                'mime_type': 'video/mp4'
            }
        ]

    @staticmethod
    def propagate_metadata_to_observation(metadata):
        if metadata['semanticType'] == 'pigazing:movingObject/video':
            return [
                'amplitudePeak', 'amplitudeTimeIntegrated', 'detectionCount', 'detectionSignificance', 'duration',
                'height', 'pathBezier', 'videoDuration', 'videoFPS', 'videoStart', 'width'
            ]
        else:
            return []


class SelectBestImages(TaskRunner):
    """
    A TaskRunner which picks the best image from every 30 minute period, and flags it as a featured observation.
    """

    def fetch_job_list_by_time_stamp(self):
        return {0: True}

    def execute_tasks(self):
        global observatories_seen

        # We should select the best image from every N seconds of observing
        period = 1800

        # This makes sure that we have a valid task list
        self.fetch_job_list()

        # Open connection to the database
        db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                               db_host=installation_info['mysqlHost'],
                                               db_user=installation_info['mysqlUser'],
                                               db_password=installation_info['mysqlPassword'],
                                               db_name=installation_info['mysqlDatabase'],
                                               obstory_id=installation_info['observatoryId'])

        # Select best images for each observatory in turn
        for obstory_id in observatories_seen:
            utc_start = floor(observatories_seen[obstory_id]['utc_min'] / period) * period
            utc_end = ceil(observatories_seen[obstory_id]['utc_max'] / period) * period

            # Remove featured flag from any time-lapse images that are already highlighted
            db.con.execute("""
UPDATE archive_observations SET featured=0
WHERE observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
      AND obsType=(SELECT uid FROM archive_semanticTypes WHERE name='pigazing:timelapse/')
      AND obsTime BETWEEN %s AND %s;
""", (obstory_id, utc_start - 1, utc_end + 1))

            # Loop over each hour within the time period for which we have new observations
            for hour in numpy.arange(utc_start, utc_end - 1, period):

                # Select the time-lapse image with the best sky clarity within each hour
                db.con.execute("""
SELECT o.uid
FROM archive_files f
INNER JOIN archive_observations o ON f.observationId = o.uid
INNER JOIN archive_metadata m ON f.uid = m.fileId AND
           m.fieldId=(SELECT uid FROM archive_metadataFields WHERE metaKey='pigazing:skyClarity')
WHERE o.observatory=(SELECT uid FROM archive_observatories WHERE publicId=%s)
      AND obsType=(SELECT uid FROM archive_semanticTypes WHERE name='pigazing:timelapse/')
      AND obsTime BETWEEN %s AND %s
ORDER BY m.floatValue DESC LIMIT 1;
""", (obstory_id, hour, hour + period))

                # Feature that image
                for item in db.con.fetchall():
                    db.con.execute("UPDATE archive_observations SET featured=1 WHERE uid=%s;", (item['uid'],))

        # Close connection to the database
        db.commit()
        db.close_db()
        del db


class ExportData(TaskRunner):
    """
    A TaskRunner which calls the script <exportData.py> to export all observations and metadata to an external server.
    """

    def fetch_job_list_by_time_stamp(self):
        return {0: True}

    def execute_tasks(self):

        # If we have run out of time, exit immediately
        if (self.must_quit_by is not None) and (time.time() > self.must_quit_by):
            return

        # This makes sure that we have a valid task list
        self.fetch_job_list()

        must_quit_string = ""
        if self.must_quit_by is not None:
            must_quit_string = "--stop-by {must_quit_by}".format(must_quit_by=self.must_quit_by)

        command = "{python_path}/command_line/exportData.py {must_quit_string}".format(
            python_path=settings['pythonPath'],
            must_quit_string=must_quit_string)
        print(command)
        os.system(command)


class DetermineLensCorrection(TaskRunner):
    """
    A TaskRunner which calls the script <calibrate_lens.py> to work out the radial distortion of the lens.
    """

    def fetch_job_list_by_time_stamp(self):
        return {0: True}

    def execute_tasks(self):

        # If we have run out of time, exit immediately
        if (self.must_quit_by is not None) and (time.time() > self.must_quit_by):
            return

        # This makes sure that we have a valid task list
        self.fetch_job_list()

        must_quit_string = ""
        if self.must_quit_by is not None:
            must_quit_string = "--stop-by {must_quit_by}".format(must_quit_by=self.must_quit_by)

        command = "{python_path}/calibration/calibrate_lens.py {must_quit_string}".format(
            python_path=settings['pythonPath'],
            must_quit_string=must_quit_string)
        print(command)
        os.system(command)


class DeterminePointing(TaskRunner):
    """
    A TaskRunner which calls the script <orientation_calculate.py> to work out which direction the camera is pointing.
    """

    def fetch_job_list_by_time_stamp(self):
        return {0: True}

    def execute_tasks(self):

        # If we have run out of time, exit immediately
        if (self.must_quit_by is not None) and (time.time() > self.must_quit_by):
            return

        # This makes sure that we have a valid task list
        self.fetch_job_list()

        must_quit_string = ""
        if self.must_quit_by is not None:
            must_quit_string = "--stop-by {must_quit_by}".format(must_quit_by=self.must_quit_by)

        command = "{python_path}/calibration/orientation_calculate.py {must_quit_string}".format(
            python_path=settings['pythonPath'],
            must_quit_string=must_quit_string)
        print(command)
        os.system(command)


class Snooze(TaskRunner):
    """
    A TaskRunning which sleeps until we next want to start observing.
    """

    def fetch_job_list_by_time_stamp(self):
        return {0: True}

    def execute_tasks(self):

        # Snooze until we next want to start observing
        if (self.must_quit_by is not None):
            sleep_period = self.must_quit_by - time.time()
            if sleep_period > 0:
                logging.info("Sleeping for {} seconds".format(sleep_period))
                time.sleep(sleep_period)


# A list of all the tasks we need to perform, in order
task_running_order = [
    AnalyseRawVideos,
    MergeOutputIntoSingleObservations(
        sub_task_classes=(TriggerRawImages, TriggerRawVideos),
        must_have_semantic_types=('pigazing:movingObject/video',)
    ),
    TimelapseRawImages,
    SelectBestImages,
    DetermineLensCorrection,
    DeterminePointing,
    ExportData,
    Snooze
]
