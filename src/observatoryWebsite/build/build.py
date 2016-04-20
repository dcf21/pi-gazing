# build.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# -------------------------------------------------
# Copyright 2016 Cambridge Science Centre.

# This file is part of Meteor Pi.

# Meteor Pi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Meteor Pi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Meteor Pi.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------

import os
import glob
import time
import shutil

import make_htaccess
import php_preprocess

# Flag to choose whether we minify CSS and Javascript
minify = False

# These subdirectories get symlinked rather than copies, because they're quite big
symlinkDirectories = ["img"]


def makehtml():

    # Paths from where we get web content
    python_path = os.path.split(os.path.abspath(__file__))[0]
    root1 = os.path.join(python_path, "..", "php")
    root_list = [root1]

    # Path to which we output processed web content
    output = os.path.join(python_path, "..", "dist")

    os.system("mkdir -p %s" % output)
    os.system("rm -Rf %s/*" % output)

    # Create an htaccess file for the root directory of web server
    make_htaccess.make_htaccess(output)

    # Walk through source directory structure
    for root in root_list:
        for in_dir in os.walk(root):

            # Separate out tuple containing subdirs and files
            assert in_dir[0][0:len(root)] == root
            dir_path = in_dir[0][len(root):]
            while dir_path.startswith('/'):
                dir_path = dir_path[1:]

            # List of files in this directory
            files = in_dir[2]

            # Ignore directories like .svn which start with a dot
            path_segments = dir_path.split('/')
            dotted_path = False
            for segment in path_segments:
                if (len(segment) > 0) and (segment[0] == '.'):
                    dotted_path = True
            if dotted_path:
                continue

            # These are big directories that it's best to symlink
            symlink = False
            for item in symlinkDirectories:
                if dir_path.startswith(item):
                    if dir_path == item:
                        a = os.path.join(root, dir_path)
                        b = os.path.join(output, dir_path)
                        if not os.path.exists(b):
                            os.system("ln -s %s %s" % (a, b))
                    symlink = True
            if symlink:
                continue

            # Report working on new directory
            print "Working on directory <%s>" % dir_path

            # Create target directory
            path = os.path.join(output, dir_path)
            os.system("mkdir -p %s" % path)

            is_javascript = dir_path.startswith("js")
            is_css = dir_path.startswith("css")

            # Loop over files
            for fname in files:
                infile = "%s" % (os.path.join(root, dir_path, fname))
                outfile = "%s" % (os.path.join(output, dir_path, fname))
                if is_javascript and fname.endswith('.js'):
                    print "Compiling JS file <%s>" % fname
                    shutil.copyfile(infile, outfile)
                elif is_css and fname.endswith('.less'):
                    print "Compiling LESS file <%s>" % fname
                    css_minify = ""
                    if minify:
                        css_minify = "--clean-css=\"--s1 --advanced --compatibility=ie8\"";
                    cmd = "lessc %s %s %s" % (infile, css_minify, outfile[:-4] + "css")
                    print cmd
                    os.system(cmd)
                elif fname.endswith('.php'):
                    php_preprocess.php_preprocess(fname, infile, outfile)
                else:
                    # print "Copying file <%s>"%fname
                    shutil.copyfile(infile, outfile)

    # Compress Javascript
    javascripts = glob.glob(os.path.join(output, "js/*.js")) + glob.glob(os.path.join(output, "js/*/*.js"))
    if minify:
        cmd = "cd %s ; uglifyjs *.js */*.js " % (os.path.join(output, "js"))
        cmd += " --compress --mangle --mangle-props "
        # cmd += " --source-map " + os.path.join(output, "js", "meteorpi.min.map")
        cmd += " --output " + os.path.join(output, "js", "meteorpi.min.js")
        print cmd
        os.system(cmd)
        for js in javascripts:
            os.unlink(js)
    else:
        cmd = "cat %s > %s"%(" ".join(javascripts),os.path.join(output, "js", "meteorpi.min.js"))
        print cmd
        os.system(cmd)

# Do it right away if we're run as a script
if __name__ == "__main__":
    makehtml()
