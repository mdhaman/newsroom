import logging
from datetime import datetime, timedelta

from eve.utils import ParsedRequest
from flask import current_app as app, json, abort
from flask_babel import gettext
from superdesk import get_resource_service
from werkzeug.exceptions import Forbidden

import newsroom
from newsroom.auth import get_user
from newsroom.companies import get_user_company
from newsroom.products.products import get_products_by_company, get_products_by_navigation
from newsroom.settings import get_setting
from newsroom.template_filters import is_admin
from newsroom.wire.utils import get_local_date, get_end_date

logger = logging.getLogger(__name__)


class FeaturedQuery(Exception):
    """Raise when query is for featured items."""
    pass


def get_bookmarks_count(user_id, product_type):
    return get_resource_service('{}_search'.format(product_type)).get_bookmarks_count(user_id)


def get_aggregations():
    return app.config.get('WIRE_AGGS', {})


class WireSearchResource(newsroom.Resource):
    datasource = {
        'search_backend': 'elastic',
        'source': 'items',
        'projection': {
            'slugline': 1,
            'headline': 1,
            'body_html': 1,
            'firstcreated': 1,
            'versioncreated': 1,
            'nextversion': 1,
            'ancestors': 1,
            'wordcount': 1,
        },
        'elastic_filter': {'bool': {'must': [{'term': {'_type': 'items'}}]}},
    }

    item_methods = ['GET']
    resource_methods = ['GET']


def get_aggregation_field(key):
    return get_aggregations()[key]['terms']['field']


def set_product_query(query, company, section, user=None, navigation_id=None):
    """
    Checks the user for admin privileges
    If user is administrator then there's no filtering
    If user is not administrator then products apply if user has a company
    If user is not administrator and has no company then everything will be filtered
    :param query: search query
    :param company: company
    :param section: section i.e. wire, agenda, marketplace etc
    :param user: user to check against (used for notification checking)
    :param navigation_id: navigation to filter products
    If not provided session user will be checked
    """
    products = None

    if is_admin(user):
        if navigation_id:
            products = get_products_by_navigation(navigation_id)
        else:
            return  # admin will see everything by default

    if company:
        products = get_products_by_company(company['_id'], navigation_id, product_type=section)
    else:
        # user does not belong to a company so blocking all stories
        abort(403, gettext('User does not belong to a company.'))

    query['bool']['should'] = []
    product_ids = [p['sd_product_id'] for p in products if p.get('sd_product_id')]
    if product_ids:
        query['bool']['should'].append({'terms': {'products.code': product_ids}})

    for product in products:
        if product.get('query'):
            if product['query'] == '_featured':
                if navigation_id:  # only return featured when nav item is selected
                    raise FeaturedQuery
            else:
                query['bool']['should'].append(query_string(product['query']))
                if product.get('planning_item_query'):
                    query['bool']['should'].append(planning_items_query_string(product.get('planning_item_query')))

    query['bool']['minimum_should_match'] = 1

    wire_time_limit_days = get_setting('wire_time_limit_days')
    if company and not is_admin(user) and not company.get('archive_access', False) and wire_time_limit_days:
        query['bool']['must'].append({'range': {'versioncreated': {
            'gte': 'now-%dd/d' % int(wire_time_limit_days),
        }}})

    if not query['bool']['should']:
        abort(403, gettext('Your company doesn\'t have any products defined.'))


def query_string(query):
    return {
        'query_string': {
            'query': query,
            'default_operator': 'AND',
            'lenient': True,
        }
    }


def planning_items_query_string(query, fields=None):
    query_string_syntax = query_string(query)

    if fields:
        query_string_syntax['query_string']['fields'] = fields
    else:
        query_string_syntax['query_string']['fields'] = ['planning_items.*']

    return {
        'nested': {
            'path': 'planning_items',
            'inner_hits': {
            },
            'query': query_string_syntax
        }
    }


def versioncreated_range(created):
    _range = {}
    offset = int(created.get('timezone_offset', '0'))
    if created.get('created_from'):
        _range['gte'] = get_local_date(created['created_from'], '00:00:00', offset)
    if created.get('created_to'):
        _range['lte'] = get_end_date(created['created_to'], get_local_date(created['created_to'], '23:59:59', offset))
    return {'range': {'versioncreated': _range}}


def _filter_terms(filters):
    return [{'terms': {get_aggregation_field(key): val}} for key, val in filters.items() if val]


def set_bookmarks_query(query, user_id):
    query['bool']['must'].append({
        'term': {'bookmarks': str(user_id)},
    })


def _items_query():
    return {
        'bool': {
            'must_not': [
                {'term': {'type': 'composite'}},
                {'constant_score': {'filter': {'exists': {'field': 'nextversion'}}}},
            ],
            'must': [{'term': {'_type': 'items'}}],
        }
    }


class WireSearchService(newsroom.Service):
    section = 'wire'

    def get_bookmarks_count(self, user_id):
        query = _items_query()
        user = get_user()
        get_resource_service('section_filters').apply_section_filter(query, self.section)
        company = get_user_company(user)
        try:
            set_product_query(query, company, self.section)
        except Forbidden:
            return 0
        set_bookmarks_query(query, user_id)
        source = {'query': query, 'size': 0}
        internal_req = ParsedRequest()
        internal_req.args = {'source': json.dumps(source)}
        return super().get(internal_req, None).count()

    def get(self, req, lookup, size=25, aggs=True):
        query = _items_query()
        user = get_user()
        company = get_user_company(user)

        get_resource_service('section_filters').apply_section_filter(query, self.section)
        set_product_query(query, company, self.section, navigation_id=req.args.get('navigation'))

        if req.args.get('q'):
            query['bool']['must'].append(query_string(req.args['q']))

        if req.args.get('newsOnly') and not (req.args.get('navigation') or req.args.get('product_type')):
            news_only_filter = get_setting('news_only_filter')
            if news_only_filter:
                query['bool']['must_not'].append(query_string(news_only_filter))
            elif app.config.get('NEWS_ONLY_FILTERS'):
                for f in app.config.get('NEWS_ONLY_FILTERS', []):
                    query['bool']['must_not'].append(f)

        if req.args.get('bookmarks'):
            set_bookmarks_query(query, req.args['bookmarks'])

        filters = None

        if req.args.get('filter'):
            filters = json.loads(req.args['filter'])

        if not app.config.get('FILTER_BY_POST_FILTER', False):
            if filters:
                query['bool']['must'] += _filter_terms(filters)

            if req.args.get('created_from') or req.args.get('created_to'):
                query['bool']['must'].append(versioncreated_range(req.args))

        source = {'query': query}
        source['sort'] = [{'versioncreated': 'desc'}]
        source['size'] = size
        source['from'] = int(req.args.get('from', 0))

        if app.config.get('FILTER_BY_POST_FILTER', False):
            if filters or req.args.get('created_from') or req.args.get('created_to'):
                source['post_filter'] = {'bool': {'must': []}}
            if filters:
                source['post_filter']['bool']['must'] += _filter_terms(filters)
            if req.args.get('created_from') or req.args.get('created_to'):
                source['post_filter']['bool']['must'].append(versioncreated_range(req.args))

        if source['from'] >= 1000:
            # https://www.elastic.co/guide/en/elasticsearch/guide/current/pagination.html#pagination
            return abort(400)

        if not source['from'] and aggs:  # avoid aggregations when handling pagination
            source['aggs'] = get_aggregations()

        internal_req = ParsedRequest()
        internal_req.args = {'source': json.dumps(source)}
        return super().get(internal_req, lookup)

    def has_permissions(self, item):
        """Test if current user has permissions to view given item."""
        req = ParsedRequest()
        req.args = {}
        try:
            results = self.get(req, {'_id': item['_id']}, size=0, aggs=False)
            return results.count() > 0
        except Forbidden:
            return False

    def get_product_items(self, product_id, size):
        query = _items_query()

        product = get_resource_service('products').find_one(req=None, _id=product_id)

        if not product:
            return

        query['bool']['should'] = []
        get_resource_service('section_filters').apply_section_filter(query, product.get('product_type'))

        if product.get('sd_product_id'):
            query['bool']['should'].append({'term': {'products.code': product['sd_product_id']}})

        if product.get('query'):
            query['bool']['should'].append(query_string(product['query']))

        query['bool']['minimum_should_match'] = 1

        source = {'query': query}
        source['sort'] = [{'versioncreated': 'desc'}]
        source['size'] = size
        source['from'] = 0
        source['post_filter'] = {'bool': {'must': []}}

        internal_req = ParsedRequest()
        internal_req.args = {'source': json.dumps(source)}
        return list(super().get(internal_req, None))

    def get_matching_topics(self, item_id, topics, users, companies):
        """
        Returns a list of topic ids matching to the given item_id
        :param item_id: item id to be tested against all topics
        :param topics: list of topics
        :param users: user_id, user dictionary
        :param companies: company_id, company dictionary
        :return:
        """
        query = {
            'bool': {
                'must_not': [
                    {'term': {'type': 'composite'}},
                    {'constant_score': {'filter': {'exists': {'field': 'nextversion'}}}},
                ],
                'must': [
                    {'term': {'_id': item_id}}
                ]
            }
        }
        aggs = {
            'topics': {
                'filters': {
                    'filters': {}
                }
            }
        }

        queried_topics = []
        # get all section filters
        section_filters = get_resource_service('section_filters').get_section_filters_dict()

        for topic in topics:
            query['bool']['must'] = [{'term': {'_id': item_id}}]

            # apply the base product query for each topic type
            get_resource_service('section_filters').apply_section_filter(query,
                                                                         topic.get('topic_type'),
                                                                         section_filters)

            user = users.get(str(topic['user']))
            if not user:
                continue

            topic_filter = {'bool': {'must': []}}

            if topic.get('query'):
                topic_filter['bool']['must'].append(query_string(topic['query']))

            if topic.get('created'):
                topic_filter['bool']['must'].append(versioncreated_range(dict(
                    created_from=topic['created'].get('from'),
                    created_to=topic['created'].get('to'),
                    timezone_offset=topic.get('timezone_offset', '0')
                )))

            if topic.get('filter'):
                topic_filter['bool']['must'] += _filter_terms(topic['filter'])

            company = companies.get(str(user.get('company', '')))

            # for now even if there's no active company matching for the user
            # continuing with the search
            try:
                set_product_query(query, company, topic.get('topic_type'), user=user)
            except Forbidden:
                logger.info('Notification for user:{} and topic:{} is skipped'
                            .format(user.get('_id'), topic.get('_id')))
                continue

            aggs['topics']['filters']['filters'][str(topic['_id'])] = topic_filter
            queried_topics.append(topic)

        source = {'query': query}
        source['aggs'] = aggs
        source['size'] = 0

        req = ParsedRequest()
        req.args = {'source': json.dumps(source)}
        topic_matches = []

        try:
            search_results = super().get(req, None)

            for topic in queried_topics:
                if search_results.hits['aggregations']['topics']['buckets'][str(topic['_id'])]['doc_count'] > 0:
                    topic_matches.append(topic['_id'])

        except Exception as exc:
            logger.error('Error in get_matching_topics for query: {}'.format(json.dumps(source)),
                         exc, exc_info=True)

        return topic_matches

    def get_items(self, item_ids):
        try:
            query = {
                'bool': {
                    'must_not': [
                        {'term': {'type': 'composite'}},
                    ],
                    'must': [
                        {'terms': {'_id': item_ids}}
                    ],
                }
            }

            source = {'query': query}
            source['size'] = len(item_ids)

            req = ParsedRequest()
            req.args = {'source': json.dumps(source)}

            return super().get(req, None)

        except Exception as exc:
            logger.error('Error in get_items for query: {}'.format(json.dumps(source)),
                         exc, exc_info=True)

    def get_matching_bookmarks(self, item_ids, active_users, active_companies):
        """
        Returns a list of user ids bookmarked any of the given items
        :param item_ids: list of ids of items to be searched
        :param active_users: user_id, user dictionary
        :param active_companies: company_id, company dictionary
        :return:
        """
        bookmark_users = []

        search_results = self.get_items(item_ids)

        if not search_results:
            return bookmark_users

        for result in search_results.hits['hits']['hits']:
            bookmarks = result['_source'].get('bookmarks', [])
            for bookmark in bookmarks:
                user = active_users.get(bookmark)
                if user and str(user.get('company', '')) in active_companies:
                    bookmark_users.append(bookmark)

        return bookmark_users

    def get_product_item_report(self, product, section_filters=None):
        query = _items_query()

        if not product:
            return

        query['bool']['should'] = []
        get_resource_service('section_filters').apply_section_filter(query,
                                                                     product.get('product_type'),
                                                                     section_filters)

        if product.get('sd_product_id'):
            query['bool']['should'].append({'term': {'products.code': product['sd_product_id']}})

        if product.get('query'):
            query['bool']['should'].append(query_string(product['query']))

        query['bool']['minimum_should_match'] = 1
        query['bool']['must_not'].append({'term': {'pubstatus': 'canceled'}})

        now = datetime.utcnow()

        source = {'query': query}
        source['size'] = 0
        source['aggs'] = {
            "today": {
                "date_range": {
                    "field": "versioncreated",
                    "ranges": [
                        {
                            "from": now.strftime('%Y-%m-%d')
                        }
                    ]
                }
            },
            "last_24_hours": {
                "date_range": {
                    "field": "versioncreated",
                    "ranges": [
                        {
                            "from": "now-1d/d"
                        }
                    ]
                }
            },
            "this_week": {
                "date_range": {
                    "field": "versioncreated",
                    "ranges": [
                        {
                            "from": (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
                        }
                    ]
                }
            },
            "last_7_days": {
                "date_range": {
                    "field": "versioncreated",
                    "ranges": [
                        {
                            "from": (now - timedelta(days=7)).strftime('%Y-%m-%d')
                        }
                    ]
                }
            },
            "this_month": {
                "date_range": {
                    "field": "versioncreated",
                    "ranges": [
                        {
                            "from": (now.replace(day=1)).strftime('%Y-%m-%d')
                        }
                    ]
                }
            },
            "previous_month": {
                "date_range": {
                    "field": "versioncreated",
                    "ranges": [
                        {
                            "from": (((now.replace(day=1)) - timedelta(days=1)).replace(day=1)).strftime('%Y-%m-%d'),
                            "to": (now.replace(day=1)).strftime('%Y-%m-%d'),
                        }
                    ]
                }
            },
            "last_6_months": {
                "date_range": {
                    "field": "versioncreated",
                    "ranges": [
                        {
                            "from": (now - timedelta(days=180)).strftime('%Y-%m-%d')
                        }
                    ]
                }
            },
        }

        internal_req = ParsedRequest()
        internal_req.args = {'source': json.dumps(source)}
        return super().get(internal_req, None)

    def get_navigation_story_count(self, navigations):
        """Get story count by navigation"""
        query = _items_query()
        get_resource_service('section_filters').apply_section_filter(query, self.section)

        aggs = {
            'navigations': {
                'filters': {
                    'filters': {}
                }
            }
        }

        for navigation in navigations:
            navigation_id = navigation.get('_id')
            products = get_products_by_navigation(navigation_id) or []
            navigation_filter = {'bool': {'should': [], 'minimum_should_match': 1}}
            for product in products:
                if product.get('query'):
                    navigation_filter['bool']['should'].append(query_string(product.get('query')))

            if navigation_filter['bool']['should']:
                aggs['navigations']['filters']['filters'][str(navigation_id)] = navigation_filter

        source = {'query': query, 'aggs': aggs, 'size': 0}
        req = ParsedRequest()
        req.args = {'source': json.dumps(source)}

        try:
            results = super().get(req, None)
            buckets = results.hits['aggregations']['navigations']['buckets']
            for navigation in navigations:
                navigation_id = navigation.get('_id')
                doc_count = buckets.get(str(navigation_id), {}).get('doc_count', 0)
                if doc_count > 0:
                    navigation['story_count'] = doc_count

        except Exception as exc:
            logger.error('Error in get_navigation_story_count for query: {}'.format(json.dumps(source)),
                         exc, exc_info=True)
