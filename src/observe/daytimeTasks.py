#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# daytimeTasks.py
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
This performs a set of tasks which need to be performed on Pi Gazing data during the daytime.
"""

import argparse
import logging
import os
import time

import daytimeTaskDefinitions

from pigazing_helpers.settings_read import settings


def daytime_tasks(must_quit_by=None):
    """
    This performs a set of tasks which need to be performed on Pi Gazing data during the daytime.

    :param must_quit_by:
        The unix time when we need to exit, even if jobs are unfinished
    :type must_quit_by:
        float
    :return:
        None
    """

    # Run each task in sequence
    for task in daytimeTaskDefinitions.task_running_order:

        # If we have run out of time, exit immediately
        if (must_quit_by is not None) and (time.time() > must_quit_by):
            return

        # Initialise task runner
        task_runner = task(must_quit_by=must_quit_by)

        # Run task
        task_runner.execute_tasks()


if __name__ == "__main__":
    # Read commandline arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop-by', default=None, type=float,
                        dest='stop_by', help='The unix time when we need to exit, even if jobs are unfinished')
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        handlers=[
                            logging.FileHandler(os.path.join(settings['pythonPath'], "../datadir/pigazing.log")),
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    daytime_tasks(must_quit_by=args.stop_by)
