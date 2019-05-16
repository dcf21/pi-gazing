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

from pigazing_helpers.dcf_ast import unix_from_jd, jd_from_unix, julian_day, inv_julian_day
from pigazing_helpers.obsarchive import obsarchive_db
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

    # Loop over all the input files associated with this time stamp
    for job in arguments['jobs']:

        # Collect metadata associated with this file
        input_metadata_file, input_metadata = metadata_file_to_dict(product_filename=job['input_file'])
    
        # Make metadata available to shell command
        job['input_file_without_extension'] = os.path.splitext(job['input_file'])[0]
        job['input_metadata'] = input_metadata
    
        # Run the shell command
        command = job['command_line'].format(**job)
        # os.system(command)
        print(command)
    
        # Fetch list of output files we have created
        file_products = []
        file_metadata_products = []
        for item in job['output_file_wildcards']:
            file_products.append(glob.glob(item))
        if input_metadata_file is not None:
            file_metadata_products.append(input_metadata_file)

    # Open connection to the database
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Import file products into the database
    for item in file_products:
        pass

    # Close connection to the database
    db.commit()
    db.close_db()
    del db

    # Delete file products
    for item in file_products + file_metadata_products:
        os.unlink(item)


def metadata_file_to_dict(product_filename):
    """
    Make a dictionary from a text file containing the metadata associated with some file product

    :param product_filename:
        The filename of the file product whose metadata we are to read
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
                # Properties that specify what command to run to complete this task, and what output it produces
                job_descriptor = {
                    'input_file': input_file,
                    'shell_command': self.shell_command(),
                    'output_file_wildcards': self.output_file_wildcards(input_file)
                }

                # Work out the time stamp of this job from the input file's filename
                time_stamp = filename_to_utc(input_file)

                # If we haven't had any jobs at the time stamp before, create an empty list for this time stamp
                if time_stamp not in jobs_by_time:
                    jobs_by_time[time_stamp] = []

                # Append this job to list of others with the same time stamp
                jobs_by_time[time_stamp].append(job_descriptor)

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
        self.task_list = []

        for time_stamp in time_stamps:
            self.task_list.append({
                'jobs': jobs_by_time[time_stamp],
                'must_quit_by': self.must_quit_by
            })

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
        jobs_by_time = None

        for sub_task in self.sub_tasks:
            # If this is the first sub task, we use it to create a new dictionary of jobs_by_time
            if jobs_by_time is None:
                jobs_by_time = sub_task.fetch_job_list_by_time_stamp()

            # subsequently, we need to merge the contents of the dictionaries together
            else:
                # Fetch a list of the new jobs to be done
                new_jobs_by_time = sub_task.fetch_job_list_by_time_stamp()

                # Loop over all the time stamps of the new jobs
                for time_stamp, new_jobs in new_jobs_by_time.items():

                    # If we haven't had any jobs at the time stamp before, create an empty list for this time stamp
                    if time_stamp not in jobs_by_time:
                        jobs_by_time[time_stamp] = []

                    # Merge this job to list of others with the same time stamp
                    jobs_by_time[time_stamp].extend(new_jobs)

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
        return ["timelapse_img_processed/{}*.png".format(time_string)]


# A list of all the tasks we need to perform, in order
task_running_order = [
    AnalyseRawVideos,
    MergeOutputIntoSingleObservations(sub_task_classes=(TriggerRawImages, TriggerRawVideos)),
    TimelapseRawImages,  # SelectBestImages, DetermineLensCorrection, DeterminePointing
]
