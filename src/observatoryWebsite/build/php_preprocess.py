# php_preprocess.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import os
import shutil


def php_preprocess(db, fname, infile, outfile):
    print "Working on file <%s>" % fname
    shutil.copyfile(infile, outfile)

    # Make PHP files executable
    os.system("chmod 755 %s" % outfile)
