
import logging
import newsroom

from flask import json, abort, url_for
from eve.utils import ParsedRequest

from planning.events.events_schema import events_schema
from planning.planning.planning import planning_schema
from superdesk.metadata.item import not_analyzed
from planning.common import WORKFLOW_STATE_SCHEMA
from newsroom.wire.search import get_local_date, set_bookmarks_query
from newsroom.wire.search import query_string, set_product_query
from superdesk.resource import Resource, not_enabled
from newsroom.auth import get_user
from newsroom.companies import get_user_company
from newsroom.utils import get_user_dict, get_company_dict, filter_active_users
from newsroom.email import send_coverage_notification_email

logger = logging.getLogger(__name__)


class AgendaResource(newsroom.Resource):
    """
    Agenda schema
    """
    schema = {}

    # identifiers
    schema['guid'] = events_schema['guid']
    schema['event_id'] = events_schema['guid']
    schema['recurrence_id'] = {
        'type': 'string',
        'mapping': not_analyzed,
        'nullable': True,
    }

    # content metadata
    schema['name'] = events_schema['name']
    schema['slugline'] = not_analyzed
    schema['definition_short'] = events_schema['definition_short']
    schema['definition_long'] = events_schema['definition_long']
    schema['abstract'] = planning_schema['abstract']
    schema['headline'] = planning_schema['headline']
    schema['firstcreated'] = events_schema['firstcreated']
    schema['version'] = events_schema['version']
    schema['versioncreated'] = events_schema['versioncreated']
    schema['ednote'] = events_schema['ednote']

    # aggregated fields
    schema['genre'] = planning_schema['genre']
    schema['subject'] = planning_schema['subject']
    schema['anpa_category'] = planning_schema['anpa_category']
    schema['priority'] = planning_schema['priority']
    schema['urgency'] = planning_schema['urgency']
    schema['place'] = planning_schema['place']

    # dates
    schema['dates'] = {
        'type': 'dict',
        'schema': {
            'start': {'type': 'datetime'},
            'end': {'type': 'datetime'},
            'tz': {'type': 'string'},
        }
    }

    # coverages
    schema['coverages'] = {
        'type': 'object',
        'mapping': {
            'type': 'nested',
            'properties': {
                'planning_id': not_analyzed,
                'coverage_id': not_analyzed,
                'scheduled': {'type': 'date'},
                'coverage_type': not_analyzed,
                'workflow_status': not_analyzed,
                'coverage_status': not_analyzed,
                'coverage_provider': not_analyzed,
                'delivery_id': not_analyzed,
                'delivery_href': not_analyzed,
            },
        },
    }

    # attachments
    schema['files'] = {
        'type': 'list',
        'mapping': not_enabled,
    }

    # state
    schema['state'] = WORKFLOW_STATE_SCHEMA

    # other searchable fields needed in UI
    schema['calendars'] = events_schema['calendars']
    schema['location'] = events_schema['location']

    # event details
    schema['event'] = {
        'type': 'object',
        'mapping': not_enabled,
    }

    # planning details which can be more than one per event
    schema['planning_items'] = {
        'type': 'list',
        'mapping': not_enabled,
    }

    schema['bookmarks'] = Resource.not_analyzed_field('list')  # list of user ids who bookmarked this item
    schema['downloads'] = Resource.not_analyzed_field('list')  # list of user ids who downloaded this item
    schema['shares'] = Resource.not_analyzed_field('list')  # list of user ids who shared this item
    schema['prints'] = Resource.not_analyzed_field('list')  # list of user ids who printed this item
    schema['copies'] = Resource.not_analyzed_field('list')  # list of user ids who copied this item

    # matching products from superdesk
    schema['products'] = {
        'type': 'list',
        'mapping': {
            'type': 'object',
            'properties': {
                'code': not_analyzed,
                'name': not_analyzed
            }
        }
    }

    resource_methods = ['GET']
    datasource = {
        'source': 'agenda',
        'search_backend': 'elastic',
        'default_sort': [('dates.start', 1)],
    }

    item_methods = ['GET']


def _agenda_query():
    return {
        'bool': {
            'must': [{'term': {'_type': 'agenda'}}],
        }
    }


def _event_date_range(args):
    _range = {}
    offset = int(args.get('timezone_offset', '0'))
    if args.get('date_from'):
        _range['gte'] = get_local_date(args['date_from'], '00:00:00', offset)
    if args.get('date_to'):
        _range['lte'] = get_local_date(args['date_to'], '23:59:59', offset)
    return {'range': {'dates.start': _range}}


aggregations = {
    'calendar': {'terms': {'field': 'calendars.name', 'size': 20}},
    'location': {'terms': {'field': 'location.name', 'size': 20}},
    'coverage': {'terms': {'field': 'coverages.coverage_type', 'size': 10}},
    'genre': {'terms': {'field': 'genre.name', 'size': 50}},
    'service': {'terms': {'field': 'service.name', 'size': 50}},
    'subject': {'terms': {'field': 'subject.name', 'size': 20}},
    'urgency': {'terms': {'field': 'urgency'}},
    'place': {'terms': {'field': 'place.name', 'size': 50}},
}


def get_aggregation_field(key):
    return aggregations[key]['terms']['field']


def _filter_terms(filters):
    return [{'terms': {get_aggregation_field(key): val}} for key, val in filters.items() if val]


class AgendaService(newsroom.Service):
    def get(self, req, lookup):
        query = _agenda_query()
        user = get_user()
        company = get_user_company(user)
        set_product_query(query, company, navigation_id=req.args.get('navigation'))

        if req.args.get('q'):
            query['bool']['must'].append(query_string(req.args['q']))

        if req.args.get('id'):
            query['bool']['must'].append({'term': {'_id': req.args['id']}})

        if req.args.get('bookmarks'):
            set_bookmarks_query(query, req.args['bookmarks'])

        if req.args.get('date_from') or req.args.get('date_to'):
            query['bool']['must'].append(_event_date_range(req.args))

        source = {'query': query}
        source['sort'] = [{'dates.start': 'asc'}]
        source['size'] = 25
        source['from'] = int(req.args.get('from', 0))

        filters = None

        if req.args.get('filter'):
            filters = json.loads(req.args['filter'])

        if filters:
            source['post_filter'] = {'bool': {'must': [_filter_terms(filters)]}}

        if source['from'] >= 1000:
            # https://www.elastic.co/guide/en/elasticsearch/guide/current/pagination.html#pagination
            return abort(400)

        if not source['from']:  # avoid aggregations when handling pagination
            source['aggs'] = aggregations

        internal_req = ParsedRequest()
        internal_req.args = {'source': json.dumps(source)}
        return super().get(internal_req, lookup)

    def get_items(self, item_ids):
        query = {
            'bool': {
                'must': [
                    {'terms': {'_id': item_ids}}
                ],
            }
        }

        return self.get_items_by_query(query, size=len(item_ids))

    def get_items_by_query(self, query, size=50):
        try:
            source = {'query': query}

            if size:
                source['size'] = size

            req = ParsedRequest()
            req.args = {'source': json.dumps(source)}

            return super().get(req, None)
        except Exception as exc:
            logger.error('Error in get_items for agenda query: {}'.format(json.dumps(source)),
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

    def set_delivery(self, wire_item):
        if not wire_item.get('coverage_id'):
            return

        query = {
            'bool': {
                'must': [
                    {'nested': {
                        'path': 'coverages',
                        'query': {
                            'bool': {
                                'must': [
                                    {'term': {'coverages.coverage_id': wire_item['coverage_id']}}
                                ]
                            }
                        },
                    }}
                ],
            }
        }

        agenda_items = self.get_items_by_query(query)
        for item in agenda_items:
            wire_item.setdefault('agenda_id', item['_id'])
            wire_item.setdefault('agenda_href', url_for('agenda.item', _id=item['_id']))
            coverages = item['coverages']
            for coverage in coverages:
                if coverage['coverage_id'] == wire_item['coverage_id'] and not coverage.get('delivery'):
                    coverage['delivery_id'] = wire_item['guid']
                    coverage['delivery_href'] = url_for('wire.item', _id=wire_item['guid'])
                    self.system_update(item['_id'], {'coverages': coverages}, item)
                    self.notify_new_coverage(item, wire_item)
                    break

    def notify_new_coverage(self, agenda, wire_item):
        user_dict = get_user_dict()
        company_dict = get_company_dict()
        notify_user_ids = filter_active_users(agenda.get('bookmarks', []), user_dict, company_dict)
        for user_id in notify_user_ids:
            user = user_dict[str(user_id)]
            send_coverage_notification_email(user, agenda, wire_item)
