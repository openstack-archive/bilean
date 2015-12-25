#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import six

from bilean.common.i18n import _
from bilean.db import api as db_api
from bilean.engine import resource as bilean_resources

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class Event(object):
    """Class to deal with consumption record."""

    def __init__(self, timestamp, **kwargs):
        self.timestamp = timestamp
        self.user_id = kwargs.get('user_id', None)
        self.action = kwargs.get('action', None)
        self.resource_type = kwargs.get('resource_type', None)
        self.action = kwargs.get('action', None)
        self.value = kwargs.get('value', 0)

    @classmethod
    def from_db_record(cls, record):
        '''Construct an event object from a database record.'''

        kwargs = {
            'id': record.id,
            'user_id': record.user_id,
            'action': record.action,
            'resource_type': record.resource_type,
            'action': record.action,
            'value': record.value,
        }
        return cls(record.timestamp, **kwargs)

    @classmethod
    def load(cls, context, db_event=None, event_id=None, project_safe=True):
        '''Retrieve an event record from database.'''
        if db_event is not None:
            return cls.from_db_record(db_event)

        record = db_api.event_get(context, event_id, project_safe=project_safe)
        if record is None:
            raise exception.EventNotFound(event=event_id)

        return cls.from_db_record(record)

    @classmethod
    def load_all(cls, context, filters=None, limit=None, marker=None,
                 sort_keys=None, sort_dir=None, project_safe=True):
        '''Retrieve all events from database.'''

        records = db_api.event_get_all(context, limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters,
                                       project_safe=project_safe)

        for record in records:
            yield cls.from_db_record(record)

    def store(self, context):
        '''Store the event into database and return its ID.'''
        values = {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'action': self.action,
            'value': self.value,
        }

        event = db_api.event_create(context, values)
        self.id = event.id

        return self.id

    @classmethod
    def from_dict(cls, **kwargs):
        timestamp = kwargs.pop('timestamp')
        return cls(timestamp, kwargs)

    def to_dict(self):
        evt = {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'action': self.action,
            'value': self.value,
            'timestamp': utils.format_time(self.timestamp),
        }
        return evt


def record(context, user_id, action=None, seconds=0, value=0):
    """Generate events for specify user

    :param context: oslo.messaging.context
    :param user_id: ID of user to mark event
    :param action: action of event, include 'charge' and 'recharge'
    :param seconds: use time length, needed when action is 'charge'
    :param value: value of recharge, needed when action is 'recharge'
    """
    try:
        if action == 'charge':
            resources = bilean_resources.resource_get_all(
                context, user_id=user_id)
            for resource in resources:
                usage = resource['rate'] / 3600.0 * time_length
                event_create(context,
                             user_id=user_id,
                             resource_id=resource['id'],
                             resource_type=resource['resource_type'],
                             action=action,
                             value=usage)
        else:
            event_create(context,
                         user_id=user_id,
                         action=action,
                         value=recharge_value)
    except Exception as exc:
        LOG.error(_("Error generate events: %s") % six.text_type(exc))
