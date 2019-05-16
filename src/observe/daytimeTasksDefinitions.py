#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# daytime_jobs.py
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

    # Collect metadata associated with this file
    input_metadata_file, input_metadata = metadata_file_to_dict(product_filename=arguments['input_file'])

    # Make metadata available to shell command
    arguments['input_file_without_extension'] = os.path.splitext(arguments['input_file'])[0]
    arguments['input_metadata'] = input_metadata

    # Run the shell command
    command = arguments['command_line'].format(**arguments)
    # os.system(command)
    print(command)

    # Fetch list of output files we have created
    file_products = []
    file_metadata_products = []
    for item in arguments['output_file_wildcards']:
        file_products.append(glob.glob(item))
    if input_metadata_file is not None:
        file_metadata_products.append(input_metadata_file)

    # Open connection to the database
    db = obsarchive_db.ObservationDatabase(file_store_path=arguments['settings']['dbFilestore'],
                                           db_host=arguments['installation_info']['mysqlHost'],
                                           db_user=arguments['installation_info']['mysqlUser'],
                                           db_password=arguments['installation_info']['mysqlPassword'],
                                           db_name=arguments['installation_info']['mysqlDatabase'],
                                           obstory_id=arguments['installation_info']['observatoryId'])

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
        self.fetch_job_list()

        logging.info("Starting job group <{}>. Running {} tasks.".format(self.__class__.__name__, len(self.task_list)))

    def fetch_job_list(self):
        """
        Populate the class variable <self.task_list> with a list of all the jobs we need to do.

        Each job is defined as a dictionary, containing all the arguments that we need to pass to
        <execute_shell_command>.

        :return:
            None
        """
        self.task_list = []

        input_file_list = []
        for glob_pattern in self.glob_patterns():
            input_file_list.append(
                glob.glob(os.path.join(settings['pythonPath'], "../datadir/", glob_pattern))
            )

        for input_file in input_file_list:
            self.task_list.append({
                'input_file': input_file,
                'shell_command': self.shell_command(),
                'output_file_wildcards': self.output_file_wildcards(input_file),
                'settings': settings,
                'installation_info': installation_info,
                'must_quit_by': self.must_quit_by
            })

    @staticmethod
    def glob_patterns():
        """
        Return the string that we need to glob (inside the <datadir> directory) to find all the files this task needs
        to operate on.

        :return:
            string filename wildcard
        """
        raise NotImplementedError

    def execute_tasks(self):
        """
        Execute this task on all of the input files which we have identified.

        :return:
            None
        """
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
        raise NotImplementedError

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
        raise NotImplementedError


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


task_list = [
    AnalyseRawVideos,  # TriggerRawImages, TriggerRawVideos,
    TimelapseRawImages,  # SelectBestImages, DetermineLensCorrection, DeterminePointing
]
