#!../../datadir/virtualenv/bin/python3
# -*- coding: utf-8 -*-
# populateConstellations.py

"""
Functions used to populate the table of constellations in the database
"""

import logging
import os
import random
import sys

from PIL import Image, ImageDraw
from lxml import etree
from pigazing_helpers.obsarchive import obsarchive_db
from pigazing_helpers.settings_read import settings, installation_info


def add_constellation(c_, info_):
    """
    Add a constellation to the table of constellations in the database.

    :param c_:
        A MySQLdb database connection object
    :param info_:
        A dictionary of information about the constellation
    :return:
        None
    """

    # Update constellation's record in the database
    c_.execute("""
UPDATE pigazing_constellations SET date=%s,genitiveForm=%s,area=%s
WHERE name=%s;
""", (info_["date"], info_["genitive"], info_["area"], info_["name"]))


def draw_outline(path_drawer, poly, width, col_red, col_grn, col_blu, wrap_around=True):
    """
    Use the PIL drawing functions to plot a polygon onto an image tile.

    This fill function can deal with regions wrapping around RA=0

    :param path_drawer:
        A PIL ImageDraw instance, used for drawing on an image
    :param poly:
        A list of the points of the polygon we are to draw
    :param width:
        The width of the canvas we are drawing onto
    :param col_red:
        The colour with which to fill the polygon
    :param col_grn:
        The colour with which to fill the polygon
    :param col_blu:
        The colour with which to fill the polygon
    :param wrap_around:
        Boolean flag indicating whether we should wrap polygons which cross the RA=0/24 discontinuity
    :return:
        None
    """

    # Do not draw polygons with fewer than three vertices
    if len(poly) < 3:
        return

    # Test whether polygon crosses the line of discontinuity
    crossed_ra_zero = False
    if wrap_around:
        for item in range(1, len(poly)):
            if (poly[item - 1][0] < width * 0.25) and (poly[item][0] > width * 0.75):
                crossed_ra_zero = True
            if (poly[item][0] < width * 0.25) and (poly[item - 1][0] > width * 0.75):
                crossed_ra_zero = True
    if not crossed_ra_zero:
        # If it doesn't cross the discontinuity, we can straightforwardly draw it right away
        path_drawer.polygon(poly, fill=(col_red, col_grn, col_blu, 255))
        return

    # Path does cross the discontinuity
    poly1 = []
    # Draw the right half of the path
    for pt in poly:
        if pt[0] < (width * 0.5):
            poly1.append((pt[0] + width, pt[1]))
        else:
            poly1.append((pt[0], pt[1]))
    path_drawer.polygon(poly1, fill=(col_red, col_grn, col_blu, 255))
    poly1 = []
    # Draw the left half of the path
    for pt in poly:
        if pt[0] > (width * 0.5):
            poly1.append((pt[0] - width, pt[1]))
        else:
            poly1.append((pt[0], pt[1]))
    path_drawer.polygon(poly1, fill=(col_red, col_grn, col_blu, 255))

    # This goes wrong for Ursa Minor and Octans, but we fudge those below


# Add metadata about constellations
def constellation_data(c_, logger):
    """
    Populate the constellations table in the database with basic metadata about constellations.

    :param c_:
        A MySQLdb database connection object
    :param logger:
        A logging object
    :return:
        None
    """

    # Add simple list of names of constellations
    for line in open("data/constellation_names.dat"):
        if (len(line.strip()) > 10) and (line[0].strip() != '#'):
            words = line.split()
            shortname = words[0]
            longname1 = ""
            longname2 = ""
            for j in range(len(words[1])):
                if (j > 0) and (words[1][j] <= 'Z'):
                    longname1 += " "
                    longname2 += "@"
                longname1 += words[1][j]
                longname2 += words[1][j]
            c.execute("""
REPLACE INTO pigazing_constellations (name, abbrev, namenospaces) VALUES (%s, %s, %s);
""", (longname1, shortname, longname2))

    # The file which contains all the raw data about the constellations
    filename = "data/constellations.xml"

    # Placeholder data which we insert for the time being
    info = {"name": "XXX", "date": "XXX", "genitive": "XXX", "area": 0}

    try:
        xml = etree.fromstring(open(filename).read())
        for element in xml.iter():
            if (element.tag == 'constellation') and (info["name"] != 'XXX'):
                add_constellation(c_=c_, info_=info)
            if type(element.text) != str:
                continue
            info[element.tag] = element.text.strip()

        # Add final constellation
        add_constellation(c_=c_, info_=info)
        del xml
    except:
        # Give user-friendly error messages if the XML file is broken
        logger.info("\nError found in XML file <{}>\n\n".format(filename))
        raise

    # Add central RA and Dec of each constellation
    filename = "data/constellation_name_places.dat"
    c_.execute("SELECT constellationId FROM pigazing_constellations WHERE name != 'Unknown' ORDER BY name ASC;")
    ids = c_.fetchall()
    i = 0
    for line in open(filename):
        line = line.strip()

        # Ignore blank lines and comment lines
        if (len(line) == 0) or (line[0] == "#"):
            continue

        # Extract the central coordinates for each constellation
        words = line.split()
        c_.execute("UPDATE pigazing_constellations SET RA=%s,Decl=%s WHERE constellationId=%s;",
                   (words[1], words[2], ids[i]["constellationId"]))
        i += 1

    # Make a map of the constellations. We use the functions below to create a high-resolution rectangular map of
    # the constellations which we can use to quickly turn any (RA, Dec) into the ID number of the constellation which
    # contains that point

    # This number of pixels per degree
    res = 8

    # These are the pixel dimensions of the map we're about to make
    width = 360 * res
    height = 180 * res

    # Create map
    map_image = Image.new('RGBA', (width, height), (0, 0, 0, 255))
    path_drawer = ImageDraw.Draw(map_image)

    # Colour in celestial poles, which aren't correctly filled otherwise by 2D fill algorithm
    c_.execute("SELECT constellationId FROM pigazing_constellations WHERE abbrev='UMI';")
    red = c_.fetchone()["constellationId"] * 2
    grn = int(random.random() * 255)
    blu = int(random.random() * 255)
    draw_outline(path_drawer=path_drawer,
                 poly=[(0, 0), (width, 0), (width, height / 2), (0, height / 2)],
                 width=width, col_red=red, col_grn=grn, col_blu=blu, wrap_around=False)

    c_.execute("SELECT constellationId FROM pigazing_constellations WHERE abbrev='OCT';")
    red = c_.fetchone()["constellationId"] * 2
    grn = int(random.random() * 255)
    blu = int(random.random() * 255)
    draw_outline(path_drawer=path_drawer,
                 poly=[(0, height), (width, height), (width, height / 2), (0, height / 2)],
                 width=width, col_red=red, col_grn=grn, col_blu=blu, wrap_around=False)

    # Fill the outline of each constellation in turn. Set the red channel equal to the constellationId
    filename = "data/constellations_eq2000.dat"
    constellation_name_old = ""
    pt_list = []
    red = grn = blu = 0
    for line in open(filename):
        if (len(line.strip()) == 0) or (line[0] == '#'):
            continue
        ra = float(line.split()[0]) * 360 / 24
        dec = float(line[12:].split()[0])
        constellation_name = line[23:].split()[0]
        if line[11] == '-':
            dec *= -1
        if constellation_name != constellation_name_old:
            if constellation_name_old:
                draw_outline(path_drawer=path_drawer,
                             poly=pt_list, width=width, col_red=red, col_grn=grn, col_blu=blu, wrap_around=True)
            pt_list = []
            constellation_name_old = constellation_name
            c_.execute("SELECT constellationId FROM pigazing_constellations WHERE abbrev=%s;", (constellation_name,))
            red = c_.fetchone()["constellationId"] * 2
            grn = int(random.random() * 255)
            blu = int(random.random() * 255)
        pt_list.append(((360 - ra) * res, (90 - dec) * res))
    draw_outline(path_drawer=path_drawer,
                 poly=pt_list, width=width, col_red=red, col_grn=grn, col_blu=blu, wrap_around=True)

    # Save the final image
    os.system("mkdir -p {}".format(settings['dataPath']))
    map_image.save(os.path.join(settings['dataPath'], "constellationMask.png"), "PNG")


# If we're called as a script, run the method constellation_data()
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        stream=sys.stdout,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    # Open a connection to the database
    db = obsarchive_db.ObservationDatabase(file_store_path=settings['dbFilestore'],
                                           db_host=installation_info['mysqlHost'],
                                           db_user=installation_info['mysqlUser'],
                                           db_password=installation_info['mysqlPassword'],
                                           db_name=installation_info['mysqlDatabase'],
                                           obstory_id=installation_info['observatoryId'])

    # Fetch database connection handle
    c = db.con

    c.execute("BEGIN;")

    # Add constellation descriptions, and central positions
    constellation_data(c_=c, logger=logger)

    # Commit changes
    c.execute("COMMIT;")
    db.commit()
    db.close_db()
