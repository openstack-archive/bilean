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

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import utils
from bilean.db import api as db_api
from bilean.resources import base as resource_base

from oslo_log import log as logging
from oslo_utils import timeutils

LOG = logging.getLogger(__name__)


class Event(object):
    """Class to deal with consumption record."""

    def __init__(self, timestamp, **kwargs):
        self.timestamp = timestamp
        self.user_id = kwargs.get('user_id')
        self.action = kwargs.get('action')
        self.resource_type = kwargs.get('resource_type')
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
    def load_all(cls, context, user_id=None, limit=None, marker=None,
                 sort_keys=None, sort_dir=None, filters=None,
                 start_time=None, end_time=None, project_safe=True,
                 show_deleted=False,):
        '''Retrieve all events from database.'''

        records = db_api.event_get_all(context, user_id=user_id, limit=limit,
                                       marker=marker, filters=filters,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       start_time=start_time,
                                       end_time=end_time,
                                       project_safe=project_safe,
                                       show_deleted=show_deleted)

        for record in records:
            yield cls.from_db_record(record)

    def store(self, context):
        '''Store the event into database and return its ID.'''
        values = {
            'timestamp': self.timestamp,
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


def record(context, user, timestamp=None, action='charge', cause_resource=None,
           resource_action=None, extra_cost=0, value=0):
    """Generate events for specify user

    :param context: oslo.messaging.context
    :param user: object user to mark event
    :param action: action of event, include 'charge' and 'recharge'
    :param cause_resource: object resource which triggered the action
    :param resource_action: action of resource
    :param extra_cost: extra cost of the resource
    :param timestamp: timestamp when event occurs
    :param value: value of recharge, needed when action is 'recharge'
    """
    if timestamp is None:
        timestamp = timeutils.utcnow()
    try:
        if action == 'charge':
            resources = resource_base.Resource.load_all(
                context, user_id=user.id, project_safe=False)
            seconds = (timestamp - user.last_bill).total_seconds()
            res_mapping = {}
            for resource in resources:
                if cause_resource and resource.id == cause_resource.id:
                    if resource_action == 'create':
                        usage = extra_cost
                    elif resource_action == 'update':
                        usage = resource.rate * seconds + extra_cost
                else:
                    usage = resource.rate * seconds
                if res_mapping.get(resource.resource_type) is None:
                    res_mapping[resource.resource_type] = usage
                else:
                    res_mapping[resource.resource_type] += usage

            if resource_action == 'delete':
                usage = cause_resource.rate * seconds + extra_cost
                if res_mapping.get(cause_resource.resource_type) is None:
                    res_mapping[cause_resource.resource_type] = 0
                res_mapping[cause_resource.resource_type] += usage

            for res_type in res_mapping.keys():
                event = Event(timestamp,
                              user_id=user.id,
                              action=action,
                              resource_type=res_type,
                              value=res_mapping.get(res_type))
                event.store(context)
        elif action == 'recharge':
            event = Event(timestamp,
                          user_id=user.id,
                          action=action,
                          value=value)
            event.store(context)
        else:
            msg = _("Unsupported event action '%s'.") % action
            raise exception.BileanException(msg=msg)
    except Exception as exc:
        LOG.error(_("Error generate events: %s") % six.text_type(exc))
