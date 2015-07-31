Welcome to MeteorPi's Python documentation!
===========================================

This site contains documentation for the Python modules in the MeteorPi project. The code for these modules, as well as
image processing code, server scripts and similar, is all hosted on GitHub_ - this also hosts a wiki which contains
general information about the project, although we're in the process of migrating definitive information into this
document instead.

The code described here will be of use to you if you are either:

#. Remotely accessing an existing MeteorPi installation, whether that installation is a single camera or a central
   server aggregating data from multiple cameras (the same API is used in both cases)
#. Modifying or customising the MeteorPi code to run on your own system (please let us know if you're doing this, it's
   great and we'd love to hear from you!)

In the first case you should only need the **meteorpi_client** module, and the data types from **meteorpi_model**. The
API examples here should help you get going, but you'll certainly want to consult the documentation for the various
search and model classes fairly soon after.

Contents:

.. toctree::
    :maxdepth: 2

    install
    api
    examples
    api-internal

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _GitHub: https://github.com/camsci/meteor-pi