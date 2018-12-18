# -*- coding: utf-8 -*-
# obsarchive_sky_area.py

# Function to create MySQL MULTIPOLYGON structures to represent the sky area covered by images

from math import pi

from .gnomonic import inv_gnomonic_project

null_polygon = "MULTIPOLYGON (((-999 -999, -999.1 -999, -999.1 -999.1, -999 -999.1, -999 -999)))"


def wrap_celestial_path(outline_ra_dec):
    """
    Take a polygon in (RA, Dec) space, and break it into multiple polygons which don't cross the RA=0 / RA=2*pi line.

    :param outline_ra_dec:
        A list of (RA, Dec) points in the original polygon.

    :return:
        A list of lists of (RA, Dec) points. All points in radians
    """
    outline_ra_dec_segments = [[]]

    # Cycle through list of vertices supplied, and break the list every time it crosses RA=0
    previous_ra = None
    previous_dec = None
    for (ra, dec) in outline_ra_dec:
        # Test whether we've crossed the line RA=0
        cross_discontinuity = ((previous_ra is not None) and (((ra > 1.5 * pi) and (previous_ra < 0.5 * pi)) or
                                                              (previous_ra > 1.5 * pi) and (ra < 0.5 * pi)
                                                              ))

        # If so, we start a line segment
        if cross_discontinuity:
            if ra > previous_ra:
                dec_at_discontinuity = ((abs(previous_ra) * dec + abs(ra - 2 * pi) * previous_dec) /
                                        (abs(previous_ra) + abs(ra - 2 * pi)))
                outline_ra_dec_segments[-1].append((0, dec_at_discontinuity))
                outline_ra_dec_segments.append([(2 * pi, dec_at_discontinuity)])
            else:
                dec_at_discontinuity = ((abs(previous_ra - 2 * pi) * dec + abs(ra) * previous_dec) /
                                        (abs(previous_ra - 2 * pi) + abs(ra)))
                outline_ra_dec_segments[-1].append((2 * pi, dec_at_discontinuity))
                outline_ra_dec_segments.append([(0, dec_at_discontinuity)])

        # Append point to the end of the line segment we're working on
        outline_ra_dec_segments[-1].append((ra, dec))
        previous_ra, previous_dec = ra, dec

    # If we only have a single segment, return that unchanged
    if len(outline_ra_dec_segments) < 2:
        return outline_ra_dec_segments

    # The last line segment joins onto the beginning of the first
    outline_ra_dec_segments[0] = outline_ra_dec_segments.pop()[:-1] + outline_ra_dec_segments[0]

    # Now turn line segments into closed polygons
    outline_ra_dec_with_wrapping = []
    for item in outline_ra_dec_segments:
        if item[0][0] == item[-1][0]:
            outline_ra_dec_with_wrapping.append(item + [item[0]])
        else:
            pole_declination = (pi / 2) if (item[-1][1] > 0) else -(pi / 2)
            outline_ra_dec_with_wrapping.append(item + [(item[-1][0], pole_declination),
                                                        (item[0][0], pole_declination),
                                                        item[0]])

    return outline_ra_dec_with_wrapping


def get_sky_area(ra, dec, pa, scale_x, scale_y, points_per_size=5, margin_fraction=0.05):
    """
    Return a MySQL MULTIPOLYGON specifier for the sky area covered by an image.

    :param ra:
        RA of the centre of the image, hours.

    :param dec:
        Declination of the centre of the image, degrees.

    :param pa:
        Position angle of the image, degrees.

    :param scale_x:
        The angular width of the field of view, degrees.

    :param scale_y:
        The angular height of the field of view, degrees.

    :param points_per_size:
        The number of points to sample along each edge of the image.

    :param margin_fraction:
        The total fractional width/height of the image we chop off the sides to avoid matching things on the very edge.

    :return:
        String descriptor for a MySQL MULTIPOLYGON.
    """

    # If we are supplied with null coordinates, return a null polygon
    if (ra is None) or (dec is None) or (ra < -900) or (dec < -900) or (scale_x is None) or (scale_y is None):
        return null_polygon

    # Create outline around edge of square -1 < x < 1 ; -1 < y < 1
    outline = [(-1, x / ((points_per_size - 1) / 2.) - 1) for x in range(points_per_size)]
    outline += [(x / ((points_per_size - 1) / 2.) - 1, 1) for x in range(1, points_per_size)]
    outline += [(1, 1 - x / ((points_per_size - 1) / 2.)) for x in range(1, points_per_size)]
    outline += [(1 - x / ((points_per_size - 1) / 2.), -1) for x in range(1, points_per_size)]

    # Move outline inwards by margin
    outline_with_margin = [(x * (1 - margin_fraction), y * (1 - margin_fraction)) for (x, y) in outline]

    # Perform gnomonic projection on each point along the outline
    outline_ra_dec = [inv_gnomonic_project(ra0=ra * pi / 12,
                                           dec0=dec * pi / 180,
                                           scale_x=scale_x * pi / 180,
                                           scale_y=scale_y * pi / 180,
                                           pos_ang=pa * pi / 180,
                                           size_x=2, size_y=2,
                                           x=x + 1,
                                           y=y + 1)
                      for (x, y) in outline_with_margin
                      ]

    # Deal with wrapping the polygon around the discontinuity at RA=0 / RA=2*pi
    outline_ra_dec_with_wrapping = wrap_celestial_path(outline_ra_dec)

    # Turn point lists into MySQL syntax
    point_list_polygon_strings = [
        "((" +
        ",".join(
            ["{} {}".format(point[0] * 12 / pi, point[1] * 180 / pi) for point in point_list]
        ) +
        "))"
        for point_list in outline_ra_dec_with_wrapping
    ]

    point_list_multipolygon_string = "MULTIPOLYGON ({})".format(",".join(point_list_polygon_strings))

    return point_list_multipolygon_string
