from superdesk.utc import utcnow
import datetime
from newsroom.company_expiry_alerts import CompanyExpiryAlerts
from .utils import post_json
from superdesk import get_resource_service
from .test_users import init as admin_init  # noqa
from .fixtures import items, init_items, init_auth # noqa


def test_company_expiry_alerts(client, app):
    now = utcnow()
    app.data.insert('companies', [{
        '_id': 'wont_expire',
        'phone': '2132132134',
        'sd_subscriber_id': '12345',
        'name': 'Press Co. Will Not Expire',
        'is_enabled': True,
        'contact_name': 'Tom',
        'expiry_date': now + datetime.timedelta(days=9)
    }, {
        '_id': 'will_expire',
        'phone': '2132132134',
        'sd_subscriber_id': '12345',
        'name': 'Press Co. That Will Expire',
        'is_enabled': True,
        'contact_name': 'Tom',
        'expiry_date': now + datetime.timedelta(days=2)
    }])

    post_json(client, '/settings/general_settings',
              {"company_expiry_alert_recipients": "admin@localhost.com, notanadmin@localhost.com"})

    companies = get_resource_service('companies').find({})
    expiry_time = (now + datetime.timedelta(days=7)).replace(hour=0, minute=0, second=0)
    assert companies.count() == 2

    with app.mail.record_messages() as outbox:
        CompanyExpiryAlerts().send_alerts()
        assert len(outbox) == 1
        assert outbox[0].recipients == ['admin@localhost.com', ' notanadmin@localhost.com']
        assert outbox[0].subject == 'Companies expiring within next 7 days ({})'\
            .format(expiry_time.strftime('%Y-%m-%d'))
        assert 'Press Co. That Will Expire' in outbox[0].body
        assert 'Press Co. Will Not Expire' not in outbox[0].body
