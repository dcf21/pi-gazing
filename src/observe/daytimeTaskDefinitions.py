#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# daytimeTaskDefinitions.py
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
This defines a set of tasks which need to be performed on Pi Gazing data during the daytime.
It is generic file processor. Each class looks for files in particular directories with particular extensions,
works out the time associated with each file from its filename, and performs predefined shell-commands on them.
"""

import glob
import logging
import multiprocessing
import os
import time
import json
import uuid

from pigazing_helpers.dcf_ast import unix_from_jd, jd_from_unix, julian_day, inv_julian_day
from pigazing_helpers.sunset_times import sun_pos, alt_az
from pigazing_helpers.obsarchive import obsarchive_model, obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


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
        if 'mask_file' in job['command_line']:
            mask_file = "/tmp/mask_{}_{}.txt".format(os.getpid(), str(uuid.uuid4()))
            with open(mask_file, "w") as f:
                f.write("\n\n".join(
                    ["\n".join([("%d %d" % p) for p in pointList])
                     for pointList in json.loads(arguments['obstory_status']['clippingRegion'])]
                    )
                )
            job['mask_file'] = mask_file

        # Run the shell command
        command = job['command_line'].format(**job)
        # os.system(command)
        print(command)

        # Compile list of all the input files we have processed
        for item in (job['input_file'], job['input_metadata_filename']):
            if item is not None:
                file_inputs.append(item)

        # Fetch list of output files we have created
        for output_file_wildcard in job['output_file_wildcards']:
            for output_file in glob.glob(output_file_wildcard['wildcard']):
                file_products.append({
                    'filename': output_file,
                    'mime_type': output_file_wildcard['mime_type'],
                    'metadata_files': []
                })

    # Open connection to the database
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Import file products into the database
    obs_obj = db.register_observation(obstory_id=arguments['obs_id'], obs_time=arguments['utc'],
                                      obs_type=arguments['obs_type'], user_id=arguments['user_id'],
                                      obs_meta=[])
    obs_id = obs_obj.id

    for output_file in file_products:

        # Collect metadata associated with this output file
        product_metadata_file, product_metadata = metadata_file_to_dict(product_filename=output_file['filename'],
                                                                        obstory_status=arguments['obstory_status'])

        metadata_objs = metadata_to_object_list(db_handle=db,
                                                obs_time=arguments['utc'],
                                                obs_id=arguments['obs_id'],
                                                user_id=arguments['user_id'],
                                                meta_dict=product_metadata)

        if product_metadata_file is not None:
            output_file['metadata_files'].append(product_metadata_file)

        db.register_file(file_path=output_file['filename'],
                         user_id=arguments['user_id'], mime_type=output_file['mime_type'],
                         semantic_type=product_metadata['semanticType'],
                         file_time=arguments['utc'], file_meta=metadata_objs,
                         observation_id=obs_id)

    # Close connection to the database
    db.commit()
    db.close_db()
    del db

    # Delete input and output files
    for item in file_inputs:
        os.unlink(item)

    # Delete output files
    for item in file_products:
        os.unlink(item['filename'])
        for metadata_filename in item['metadata_files']:
            os.unlink(metadata_filename)


def metadata_file_to_dict(product_filename, obstory_status):
    """
    Make a dictionary from a text file containing the metadata associated with some file product

    :param product_filename:
        The filename of the file product whose metadata we are to read
    :param obstory_status:
        The status of the observatory which made this observation
    :return:
        The filename of the metadata file, and a dictionary of the metadata we collected
    """

    # Metadata is stored in text files which sit alongside each file product
    filename_without_extension = os.path.splitext(product_filename)[0]
    metadata_filename = "{}.txt".format(filename_without_extension)

    # Start constructing a dictionary of the metadata in the file
    output = {}

    # If the file doesn't exist, quietly return an empty dictionary
    if not os.path.exists(metadata_filename):
        return None, output

    # Read the file, line by line
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

    # Add further metadata about the position of the Sun
    utc = output['utc']
    obs_id = output['obsId']

    sun_pos_at_utc = sun_pos(utc)
    sun_alt_az_at_utc = alt_az(sun_pos_at_utc[0], sun_pos_at_utc[1], output['utc'],
                      obstory_status['latitude'], obstory_status['longitude'])
    output['sunRA'] = sun_pos_at_utc[0]
    output['sunDecl'] = sun_pos_at_utc[1]
    output['sunAlt'] = sun_alt_az_at_utc[0]
    output['sunAz'] = sun_alt_az_at_utc[1]

    # Return the dictionary of metadata
    return metadata_filename, output


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
    return "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(year, month, day, hour, minutes, sec)


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

        # Fetch list of input files, and sort them by time stamp
        jobs_by_time = {}
        for glob_pattern in self.glob_patterns():
            for input_file in glob.glob(os.path.join(settings['pythonPath'], "../datadir/", glob_pattern)):

                # Collect metadata associated with this input file
                input_metadata_file, input_metadata = metadata_file_to_dict(product_filename=input_file,
                                                                            obstory_status=obstory_status)

                # Properties that specify what command to run to complete this task, and what output it produces
                job_descriptor = {
                    'input_file': input_file,
                    'input_file_without_extension': os.path.splitext(input_file)[0],
                    'input_metadata_filename': input_metadata_file,
                    'input_metadata': input_metadata,
                    'shell_command': self.shell_command(),
                    'output_file_wildcards': self.output_file_wildcards(input_file)
                }

                # Work out the time stamp of this job from the input file's filename
                time_stamp_string = "{}_{}".format(fetch_time_string_from_filename(filename=input_file),
                                                   input_metadata['obsId'])

                # If we haven't had any jobs at the time stamp before, create an empty list for this time stamp
                if time_stamp_string not in jobs_by_time:
                    jobs_by_time[time_stamp_string] = {
                        'obs_id': input_metadata['obsId'],
                        'utc': input_metadata['utc'],
                        'obs_type': insert_here,
                        'user_id': obstory_status['owner'],
                        'obstory_status': obstory_status,
                        'must_quit_by': self.must_quit_by,
                        'job_list': []
                    }

                # Append this job to list of others with the same time stamp
                jobs_by_time[time_stamp_string]['job_list'].append(job_descriptor)

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
        return None

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
        return None


class MergeOutputIntoSingleObservations(TaskRunner):
    """
    Merge the jobs in several task runners into a single task runner. This means that output from the various tasks
    which share common time stamps will be incorporated into common observations in the database.
    """

    def __init__(self, sub_task_classes):
        self.sub_task_classes = sub_task_classes
        self.sub_tasks = None
        super().__init__()

    def __call__(self, must_quit_by=None):
        self.must_quit_by = must_quit_by

    def fetch_job_list_by_time_stamp(self):
        # Instantiate sub tasks
        self.sub_tasks = []
        for sub_task_class in self.sub_task_classes:
            self.sub_tasks = sub_task_class(must_quit_by=self.must_quit_by)

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

        # Return combined list of jobs
        return jobs_by_time


class AnalyseRawVideos(TaskRunner):
    @staticmethod
    def glob_patterns():
        return ["rawvideo/*.h264"]

    @staticmethod
    def shell_command():
        return """
{settings[binaryPath]}/debug/analyseH264_libav \
         --input \"{input_file}\" \
         --obsid \"{input_metadata[obsid]}\" \
         --time-start {input_metadata[t_start]} \
         --fps {input_metadata[fps]} \
         --mask \"{mask_file}\"
        """

    @staticmethod
    def output_file_wildcards(input_file):
        return []


class TimelapseRawImages(TaskRunner):
    @staticmethod
    def glob_patterns():
        return ["timelapse_raw_nonlive/*.rgb", "timelapse_raw_live/*.rgb"]

    @staticmethod
    def shell_command():
        return """
{settings[imageProcessorPath]}/debug/rawimg2png \
         --input \"{input_file}\" \
         --output \"timelapse_img_processed/{input_file_without_extension}\" \
         --noise {input_metadata[noiseLevel]}
         """

    @staticmethod
    def output_file_wildcards(input_file):
        time_string = fetch_time_string_from_filename(filename=input_file)
        return [
            {
                'wildcard': 'timelapse_img_processed/{}*.png'.format(time_string),
                'mime_type': 'image/png'
            }
        ]


class TriggerRawImages(TaskRunner):
    @staticmethod
    def glob_patterns():
        return ["triggers_raw_nonlive/*.rgb", "triggers_raw_live/*.rgb"]

    @staticmethod
    def shell_command():
        return """
{settings[imageProcessorPath]}/debug/rawimg2png \
         --input \"{input_file}\" \
         --output \"triggers_img_processed/{input_file_without_extension}\" \
         --noise {input_metadata[noiseLevel]}
         """

    @staticmethod
    def output_file_wildcards(input_file):
        time_string = fetch_time_string_from_filename(filename=input_file)
        return [
            {
                'wildcard': 'triggers_img_processed/{}*.png'.format(time_string),
                'mime_type': 'image/png'
            }
        ]


# A list of all the tasks we need to perform, in order
task_running_order = [
    AnalyseRawVideos,
    MergeOutputIntoSingleObservations(sub_task_classes=(TriggerRawImages, TriggerRawVideos)),
    TimelapseRawImages,  # SelectBestImages, DetermineLensCorrection, DeterminePointing
]
