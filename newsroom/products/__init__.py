import superdesk
from flask import Blueprint
from flask_babel import gettext

from .products import ProductsResource, ProductsService

blueprint = Blueprint('products', __name__)

from . import views   # noqa


def init_app(app):
    superdesk.register_resource('products', ProductsResource, ProductsService, _app=app)
    app.settings_app(
        'products',
        gettext('Products'),
        weight=400,
        data=views.get_products_settings_data
    )
    app.settings_app(
        'section_filters',
        gettext('Section Filters'),
        weight=401,
        data=views.get_section_filters_settings_data
    )

