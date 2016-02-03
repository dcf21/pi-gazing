# admin_api.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford, Tom Oinn

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
        return jsonify({'configs': list(x.as_dict() for x in db.get_export_configurations())})

    @app.route('{0}/export/<config_id>'.format(url_path), methods=['GET'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def get_export_configuration(config_id):
        db = meteor_app.get_db()
        config = db.get_export_configuration(config_id=config_id)
        if config is None:
            return MeteorApp.not_found(entity_id=config_id)
        return jsonify({'config': config.as_dict()})

    @app.route('{0}/export/<config_id>'.format(url_path), methods=['DELETE'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def delete_export_configuration(config_id):
        db = meteor_app.get_db()
        db.delete_export_configuration(config_id=config_id)
        return MeteorApp.success()

    @app.route('{0}/export/<config_id>'.format(url_path), methods=['PUT'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def update_export_configuration(config_id):
        db = meteor_app.get_db()
        config = model.ExportConfiguration.from_dict(safe_load(request.get_data()))
        db.create_or_update_export_configuration(export_config=config)
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
        return jsonify({'users': list(u.as_dict() for u in db.get_users())})

    @app.route('{0}/users'.format(url_path), methods=['POST'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def create_user_or_change_password():
        db = meteor_app.get_db()
        new_user = safe_load(request.get_data())
        db.create_or_update_user(new_user['user_id'], new_user['password'], None)
        return jsonify({'users': list(u.as_dict() for u in db.get_users())})

    @app.route('{0}/users/roles'.format(url_path), methods=['PUT'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def update_user_roles():
        db = meteor_app.get_db()
        new_roles = safe_load(request.get_data())['new_roles']
        for user in new_roles:
            db.create_or_update_user(user_id=user['user_id'], password=None, roles=user['roles'])
        return jsonify({'users': list(u.as_dict() for u in db.get_users())})

    @app.route('{0}/users'.format(url_path), methods=['GET'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def get_users():
        db = meteor_app.get_db()
        return jsonify({'users': list(u.as_dict() for u in db.get_users())})

    @app.route('{0}/obstory/<obstory_id>/status'.format(url_path), methods=['POST'])
    @meteor_app.requires_auth(roles=['obstory_admin'])
    def update_obstory_status(obstory_id):
        db = meteor_app.get_db()
        update = safe_load(request.get_data())

        obstory_info = db.get_obstory_from_id(obstory_id)
        if not obstory_info:
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
        return jsonify({'status': status})
