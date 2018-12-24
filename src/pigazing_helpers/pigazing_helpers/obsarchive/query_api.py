# -*- coding: utf-8 -*-
# query_api.py

import os
import re
import sys
import time
from urllib.parse import unquote

from flask import request, send_file, Response
from flask_jsonpify import jsonify
from yaml import safe_load

from . import obsarchive_model as mp


def add_routes(obsarchive_app, url_path=''):
    """
    Adds search and retrieval routes to a :class:`obsarchive_server.ObservationServer` instance

    :param ObservationApp obsarchive_app:
        The :class:`obsarchive_server.ObservationApp` to which routes should be added
    :param string url_path:
        The base path used for the query routes, defaults to ''
    """
    from .obsarchive_server import ObservationApp

    app = obsarchive_app.app

    @app.after_request
    def after_request(response):
        response.headers.add('Accept-Ranges', 'bytes')
        return response

    # Return a list of all of the observatories which are registered in this repository
    # A dictionary of basic information is returned for each
    @app.route('{0}/obstories'.format(url_path), methods=['GET'])
    def get_obstories():
        db = obsarchive_app.get_db()
        obstories = db.get_obstory_ids()
        output = {}
        for o in obstories:
            output[o] = db.get_obstory_from_id(o)
            db.con.execute("SELECT m.time FROM archive_metadata m "
                           "INNER JOIN archive_observatories l ON m.observatory = l.uid "
                           "AND l.publicId = %s AND m.time>0 "
                           "ORDER BY m.time ASC LIMIT 1",
                           (o,))
            first_seen = 0
            results = db.con.fetchall()
            if results:
                first_seen = results[0]['time']
            db.con.execute("SELECT m.time FROM archive_metadata m "
                           "INNER JOIN archive_observatories l ON m.observatory = l.uid "
                           "AND l.publicId = %s AND m.time>0 "
                           "ORDER BY m.time DESC LIMIT 1",
                           (o,))
            last_seen = 0
            results = db.con.fetchall()
            if results:
                last_seen = results[0]['time']
            output[o]['firstSeen'] = first_seen
            output[o]['lastSeen'] = last_seen
        db.close_db()
        return jsonify(output)

    # Return a list of all of the metadata tags which ever been set on a particular observatory, with time stamp
    @app.route('{0}/obstory/<obstory_id>/metadata'.format(url_path), methods=['GET'])
    def get_obstory_status_all(obstory_id):
        db = obsarchive_app.get_db()
        search = mp.ObservatoryMetadataSearch(obstory_ids=[obstory_id], time_min=0, time_max=time.time())
        data = db.search_obstory_metadata(search)['items']
        data.sort(key=lambda x: x.time)
        output = [[i.time, i.key, i.value] for i in data]
        db.close_db()
        return jsonify({'status': output})

    # Return a list of all of the metadata which was valid for a particular observatory at a particular time
    @app.route('{0}/obstory/<obstory_id>/statusdict'.format(url_path), methods=['GET'])
    @app.route('{0}/obstory/<obstory_id>/statusdict/<unix_time>'.format(url_path), methods=['GET'])
    def get_obstory_status_by_time(obstory_id, unix_time=None):
        db = obsarchive_app.get_db()
        if unix_time is None:
            unix_time = time.time()
        status = {}
        try:
            obstory_info = db.get_obstory_from_id(obstory_id)
            if obstory_info:
                obstory_name = obstory_info['name']
                status = db.get_obstory_status(obstory_name=obstory_name, time=float(unix_time))
        except ValueError:
            return jsonify({'error': 'No such observatory "%s".' % obstory_id})
        db.close_db()
        return jsonify({'status': status})

    # Search for observations using a YAML search string
    @app.route('{0}/obs/<search_string>'.format(url_path), methods=['GET'], strict_slashes=True)
    def search_events(search_string):
        db = obsarchive_app.get_db()
        try:
            search = mp.ObservationSearch.from_dict(safe_load(unquote(search_string)))
        except ValueError:
            return jsonify({'error': str(sys.exc_info()[1])})
        observations = db.search_observations(search)
        db.close_db()
        return jsonify({'obs': list(x.as_dict() for x in observations['obs']), 'count': observations['count']})

    # Search for files using a YAML search string
    @app.route('{0}/files/<search_string>'.format(url_path), methods=['GET'])
    def search_files(search_string):
        db = obsarchive_app.get_db()
        try:
            search = mp.FileRecordSearch.from_dict(safe_load(unquote(search_string)))
        except ValueError:
            return jsonify({'error': str(sys.exc_info()[1])})
        files = db.search_files(search)
        db.close_db()
        return jsonify({'files': list(x.as_dict() for x in files['files']), 'count': files['count']})

    # Return a list of the number of observations of a particular type in a sequence
    # of time intervals between utc_min and utc_max, with step size period
    @app.route('{0}/activity/<obstory_id>/<semantic_type>/<utc_min>/<utc_max>/<period>'.format(url_path),
               methods=['GET'])
    def get_activity(obstory_id, semantic_type, utc_min, utc_max, period):
        db = obsarchive_app.get_db()
        utc_min = float(utc_min)
        utc_max = float(utc_max)
        period = float(period)
        count = 0
        output = []
        while count < 250:
            a = utc_min + period * count
            b = a + period
            count += 1
            db.con.execute("SELECT COUNT(*) FROM archive_observations o "
                           "INNER JOIN archive_observatories l ON o.observatory = l.uid "
                           "INNER JOIN archive_semanticTypes s ON o.obsType = s.uid "
                           "WHERE l.publicId=%s AND s.name=%s AND o.obsTime>=%s AND o.obsTime<%s LIMIT 1",
                           (obstory_id, semantic_type, a, b))
            output.append(db.con.fetchone()['COUNT(*)'])
            if b >= utc_max:
                break
        db.close_db()
        return jsonify({"activity": output})

    # Return a thumbnail version of an image
    @app.route('{0}/thumbnail/<file_id>/<file_name>'.format(url_path), methods=['GET'])
    def get_thumbnail(file_id, file_name):
        db = obsarchive_app.get_db()
        record = db.get_file(repository_fname=file_id)
        if record is None:
            db.close_db()
            return ObservationApp.not_found(entity_id=file_id)
        if record.mime_type != "image/png":
            db.close_db()
            return ObservationApp.not_found(entity_id=file_id)
        file_path = db.file_path_for_id(record.id)
        thumb_path = os.path.join(db.file_store_path, "../thumbnails", record.id)
        if not os.path.exists(thumb_path):
            resize_tool = os.path.join(obsarchive_app.binary_path, "resize")
            os.system("%s %s 220 %s" % (resize_tool, file_path, thumb_path))
        db.close_db()
        return send_file(filename_or_fp=thumb_path, mimetype=record.mime_type)

    # Return a file from the repository
    @app.route('{0}/files/content/<file_id>/<file_name>'.format(url_path), methods=['GET'])
    @app.route('{0}/files/content/<file_id>'.format(url_path), methods=['GET'])
    def get_file_content(file_id, file_name=None):

        # http://blog.asgaard.co.uk/2012/08/03/http-206-partial-content-for-flask-python
        def send_file_partial(filename_or_fp, mimetype):
            range_header = request.headers.get('Range', None)
            if not range_header:
                return send_file(filename_or_fp)

            size = os.path.getsize(filename_or_fp)
            byte1, byte2 = 0, None

            m = re.search('(\d+)-(\d*)', range_header)
            g = m.groups()

            if g[0]:
                byte1 = int(g[0])
            if g[1]:
                byte2 = int(g[1])

            length = size - byte1
            if byte2 is not None:
                length = byte2 - byte1 + 1

            with open(filename_or_fp, 'rb') as f:
                f.seek(byte1)
                data = f.read(length)

            rv = Response(data,
                          206,
                          mimetype=mimetype,
                          direct_passthrough=True)
            rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))

            return rv

        db = obsarchive_app.get_db()
        record = db.get_file(repository_fname=file_id)
        if record is None:
            db.close_db()
            return ObservationApp.not_found(entity_id=file_id)
        file_path = db.file_path_for_id(record.id)
        db.close_db()
        return send_file_partial(filename_or_fp=file_path, mimetype=record.mime_type)
