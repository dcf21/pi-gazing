# admin_api.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford, Tom Oinn

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

import time
from urllib import unquote

from yaml import safe_load

import meteorpi_model as model
from flask.ext.jsonpify import jsonify
from flask import request, g


def add_routes(meteor_app, url_path=''):
    from meteorpi_server import MeteorApp
    app = meteor_app.app

    @app.route('{0}/export'.format(url_path), methods=['GET'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def get_export_configurations():
        db = meteor_app.get_db()
        output = {'configs': list(x.as_dict() for x in db.get_export_configurations())}
        db.close_db()
        return jsonify(output)

    @app.route('{0}/export/<config_id>'.format(url_path), methods=['GET'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def get_export_configuration(config_id):
        db = meteor_app.get_db()
        config = db.get_export_configuration(config_id=config_id)
        db.close_db()
        if config is None:
            return MeteorApp.not_found(entity_id=config_id)
        return jsonify({'config': config.as_dict()})

    @app.route('{0}/export/<config_id>'.format(url_path), methods=['DELETE'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def delete_export_configuration(config_id):
        db = meteor_app.get_db()
        db.delete_export_configuration(config_id=config_id)
        db.close_db()
        return MeteorApp.success()

    @app.route('{0}/export/<config_id>'.format(url_path), methods=['PUT'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def update_export_configuration(config_id):
        db = meteor_app.get_db()
        config = model.ExportConfiguration.from_dict(safe_load(request.get_data()))
        db.create_or_update_export_configuration(export_config=config)
        db.close_db()
        return MeteorApp.success()

    @app.route('{0}/export'.format(url_path), methods=['POST'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def create_export_configuration():
        db = meteor_app.get_db()
        spec = safe_load(request.get_data())
        export_type = spec['type']
        if export_type == 'file':
            search = model.FileRecordSearch(limit=0)
        elif export_type == 'observation':
            search = model.ObservationSearch(limit=0)
        elif export_type == 'metadata':
            search = model.ObservatoryMetadataSearch(limit=0)
        else:
            raise ValueError("Search 'type' must be either 'file' or 'observation' or 'metadata'")
        config = model.ExportConfiguration(target_url=spec['target_url'],
                                           user_id=spec['user_id'],
                                           password=spec['password'],
                                           search=search,
                                           name=spec['name'],
                                           description=spec['description'])
        db.create_or_update_export_configuration(config)
        db.close_db()
        return jsonify({'config': config.as_dict()})

    @app.route('{0}/login'.format(url_path), methods=['GET'])
    @meteor_app.requires_auth(roles=['user'])
    def login():
        return jsonify({'user': meteor_app.get_user().as_dict()})

    @app.route('{0}/users/<user_id>'.format(url_path), methods=['DELETE'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def delete_user(user_id):
        db = meteor_app.get_db()
        user_id = unquote(user_id)
        db.delete_user(user_id)
        output = {'users': list(u.as_dict() for u in db.get_users())}
        db.close_db()
        return jsonify(output)

    @app.route('{0}/users'.format(url_path), methods=['POST'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def create_user_or_change_password():
        db = meteor_app.get_db()
        new_user = safe_load(request.get_data())
        db.create_or_update_user(new_user['user_id'], new_user['password'], None)
        output = {'users': list(u.as_dict() for u in db.get_users())}
        db.close_db()
        return jsonify(output)

    @app.route('{0}/users/roles'.format(url_path), methods=['PUT'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def update_user_roles():
        db = meteor_app.get_db()
        new_roles = safe_load(request.get_data())['new_roles']
        for user in new_roles:
            db.create_or_update_user(user_id=user['user_id'], password=None, roles=user['roles'])
        output = {'users': list(u.as_dict() for u in db.get_users())}
        db.close_db()
        return jsonify(output)

    @app.route('{0}/users'.format(url_path), methods=['GET'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def get_users():
        db = meteor_app.get_db()
        output = {'users': list(u.as_dict() for u in db.get_users())}
        db.close_db()
        return jsonify(output)

    @app.route('{0}/obstory/<obstory_id>/status'.format(url_path), methods=['POST'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def update_obstory_status(obstory_id):
        db = meteor_app.get_db()
        update = safe_load(request.get_data())

        obstory_info = db.get_obstory_from_id(obstory_id)
        if not obstory_info:
            db.close_db()
            return MeteorApp.not_found(entity_id=obstory_id)
        obstory_name = obstory_info['name']

        db.register_obstory_metadata(obstory_name=obstory_name,
                                     key=update['key'],
                                     value=update['value'],
                                     metadata_time=update['time'],
                                     time_created=time.time(),
                                     user_created=g.user.user_id
                                     )

        status = db.get_obstory_status(obstory_name=obstory_name, time=float(update['time']))
        db.close_db()
        return jsonify({'status': status})
