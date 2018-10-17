import newsroom
import superdesk
from collections import namedtuple

settings_context = ['products', 'section_filters']
SETTINGS_CONTEXT = namedtuple('SETTINGS_CONTEXT', ['PRODUCTS', 'SECTION_FILTERS'])(*settings_context)


class ProductsResource(newsroom.Resource):
    """
    Products schema
    """
    schema = {
        'name': {
            'type': 'string',
            'unique': True,
            'required': True
        },
        'description': {
            'type': 'string'
        },
        'sd_product_id': {
            'type': 'string'
        },
        'query': {
            'type': 'string'
        },
        'is_enabled': {
            'type': 'boolean',
            'default': True
        },
        'navigations': {
            'type': 'list',
            'nullable': True,
        },
        'companies': {
            'type': 'list',
            'nullable': True,
        },
        'product_type': {
            'type': 'string',
            'default': 'wire'
        },
        # section filters are products applied to the sections
        'is_section_filter': {
            'type': 'boolean',
            'default': False
        },
    }
    datasource = {
        'source': 'products',
        'default_sort': [('name', 1)]
    }
    item_methods = ['GET', 'PATCH', 'DELETE']
    resource_methods = ['GET', 'POST']
    query_objectid_as_string = True  # needed for companies/navigations lookup to work


class ProductsService(newsroom.Service):
    pass


def get_products_by_navigation(navigation_id):
    return list(superdesk.get_resource_service('products').
                get(req=None, lookup={'navigations': str(navigation_id),
                                      'is_enabled': True,
                                      'is_section_filter': False}))


def get_products_by_company(company_id, navigation_id=None, product_type=None):
    """Get the list of products for a company

    :param company_id: Company Id
    :param navigation_id: Navigation Id
    :param product_type: Type of the product
    """
    lookup = {'is_enabled': True, 'companies': str(company_id), 'is_section_filter': False}
    if navigation_id:
        lookup['navigations'] = str(navigation_id)
    if product_type:
        lookup['product_type'] = product_type

    products = list(superdesk.get_resource_service('products').get(req=None, lookup=lookup))
    return products


def get_section_filters(product_type):
    """Get the list of base products for product type

    :param product_type: Type of product
    """
    lookup = {'is_enabled': True, 'is_section_filter': True, 'product_type': product_type}
    products = list(superdesk.get_resource_service('products').get(req=None, lookup=lookup))
    return products


def get_section_filters_dict():
    """Get the list of base products for product type

    :param product_type: Type of product
    """
    lookup = {'is_enabled': True, 'is_section_filter': True}
    products = list(superdesk.get_resource_service('products').get(req=None, lookup=lookup))
    filters = {}
    for product in products:
        if not filters.get(product.get('product_type')):
            filters[product.get('product_type')] = []
        filters[product.get('product_type')].append(product)

    return filters


def get_products_dict_by_company(company_id):
    lookup = {'is_enabled': True, 'companies': str(company_id), 'is_section_filter': False}
    return list(superdesk.get_resource_service('products').get(req=None, lookup=lookup))
