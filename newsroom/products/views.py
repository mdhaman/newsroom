import re

import flask
from bson import ObjectId
from flask import jsonify, current_app
from flask_babel import gettext
from superdesk import get_resource_service

from newsroom.auth.decorator import admin_only
from newsroom.products import blueprint
from newsroom.utils import get_json_or_400, get_entity_or_404
from newsroom.utils import query_resource
from .products import SETTINGS_CONTEXT


def get_products_settings_data():
    return get_settings_data(SETTINGS_CONTEXT.PRODUCTS)


def get_section_filters_settings_data():
    return get_settings_data(SETTINGS_CONTEXT.SECTION_FILTERS)


def get_settings_data(context):
    """Get the settings data for products or section filter

    :param context
    """
    lookup = {'is_section_filter': context == SETTINGS_CONTEXT.SECTION_FILTERS}

    data = {
        'products': list(query_resource('products', lookup=lookup)),
        'sections': current_app.sections,
        'settings_context': context,
        'navigations': [],
        'companies': []
    }
    if context == SETTINGS_CONTEXT.PRODUCTS:
        data['navigations'] = list(query_resource('navigations')),
        data['companies'] = list(query_resource('companies')),
    return data


@blueprint.route('/products', methods=['GET'])
@admin_only
def index():
    lookup = None
    if flask.request.args.get('q'):
        lookup = flask.request.args.get('q')
    products = list(query_resource('products', lookup=lookup))
    return jsonify(products), 200


@blueprint.route('/products/search', methods=['GET'])
@admin_only
def search():
    lookup = None
    if flask.request.args.get('q'):
        regex = re.compile('.*{}.*'.format(flask.request.args.get('q')), re.IGNORECASE)
        lookup = {'name': regex}
    products = list(query_resource('products', lookup=lookup))
    return jsonify(products), 200


def validate_product(product):
    if not product.get('name'):
        return jsonify({'name': gettext('Name not found')}), 400


@blueprint.route('/products/new', methods=['POST'])
@admin_only
def create():
    product = get_json_or_400()

    validation = validate_product(product)
    if validation:
        return validation

    if product.get('navigations'):
        product['navigations'] = [str(get_entity_or_404(_id, 'navigations')['_id'])
                                  for _id in product.get('navigations').split(',')]

    ids = get_resource_service('products').post([product])
    return jsonify({'success': True, '_id': ids[0]}), 201


@blueprint.route('/products/<id>', methods=['POST'])
@admin_only
def edit(id):
    get_entity_or_404(ObjectId(id), 'products')
    data = get_json_or_400()
    updates = {
        'name': data.get('name'),
        'description': data.get('description'),
        'sd_product_id': data.get('sd_product_id'),
        'query': data.get('query'),
        'is_enabled': data.get('is_enabled'),
        'product_type': data.get('product_type', 'wire'),
        'is_section_filter': data.get('is_section_filter', False)
    }

    validation = validate_product(updates)
    if validation:
        return validation

    get_resource_service('products').patch(id=ObjectId(id), updates=updates)
    return jsonify({'success': True}), 200


@blueprint.route('/products/<id>/companies', methods=['POST'])
@admin_only
def update_companies(id):
    updates = flask.request.get_json()
    get_resource_service('products').patch(id=ObjectId(id), updates=updates)
    return jsonify({'success': True}), 200


@blueprint.route('/products/<id>/navigations', methods=['POST'])
@admin_only
def update_navigations(id):
    updates = flask.request.get_json()
    get_resource_service('products').patch(id=ObjectId(id), updates=updates)
    return jsonify({'success': True}), 200


@blueprint.route('/products/<id>', methods=['DELETE'])
@admin_only
def delete(id):
    """ Deletes the products by given id """
    get_entity_or_404(ObjectId(id), 'products')
    get_resource_service('products').delete({'_id': ObjectId(id)})
    return jsonify({'success': True}), 200
