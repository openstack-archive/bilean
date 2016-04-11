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

import logging

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common.i18n import _LC
from bilean.common.i18n import _LE
from bilean.common.i18n import _LI
from bilean.common.i18n import _LW
from bilean.common import utils
from bilean.db import api as db_api

from oslo_log import log
from oslo_utils import timeutils

LOG = log.getLogger(__name__)


class Event(object):
    """Class to deal with consumption record."""

    def __init__(self, user_id, timestamp, level, **kwargs):
        self.user_id = user_id
        self.timestamp = timestamp
        self.level = level

        self.id = kwargs.get('id')
        self.action = kwargs.get('action')
        self.status = kwargs.get('status')
        self.status_reason = kwargs.get('status_reason')
        self.metadata = kwargs.get('metadata')

    @classmethod
    def from_db_record(cls, record):
        '''Construct an event object from a database record.'''

        kwargs = {
            'id': record.id,
            'action': record.action,
            'status': record.status,
            'status_reason': record.status_reason,
            'metadata': record.meta_data,
        }
        return cls(record.user_id, record.timestamp, record.level, **kwargs)

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
    def load_all(cls, context, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, project_safe=True):
        '''Retrieve all events from database.'''

        records = db_api.event_get_all(context, limit=limit,
                                       marker=marker,
                                       filters=filters,
                                       sort_keys=sort_keys,
                                       sort_dir=sort_dir,
                                       project_safe=project_safe)

        for record in records:
            yield cls.from_db_record(record)

    def store(self, context):
        '''Store the event into database and return its ID.'''
        values = {
            'timestamp': self.timestamp,
            'user_id': self.user_id,
            'action': self.action,
            'level': self.level,
            'status': self.status,
            'status_reason': self.status_reason,
            'meta_data': self.metadata,
        }

        event = db_api.event_create(context, values)
        self.id = event.id

        return self.id

    def to_dict(self):
        evt = {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'level': self.level,
            'status': self.status,
            'status_reason': self.status_reason,
            'timestamp': utils.format_time(self.timestamp),
            'metadata': self.metadata,
        }
        return evt


def critical(context, user_id, action, status=None, status_reason=None,
             timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(user_id, timestamp, logging.CRITICAL, action=action,
                  status=status, status_reason=status_reason)
    event.store(context)
    LOG.critical(_LC('User [%(id)s] %(action)s - %(status)s: %(reason)s'),
                 {'id': user_id,
                  'action': action,
                  'status': status,
                  'reason': status_reason})


def error(context, user_id, action, status=None, status_reason=None,
          timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(user_id, timestamp, logging.ERROR, action=action,
                  status=status, status_reason=status_reason)
    event.store(context)
    LOG.error(_LE('User [%(id)s] %(action)s - %(status)s: %(reason)s'),
              {'id': user_id,
               'action': action,
               'status': status,
               'reason': status_reason})


def warning(context, user_id, action, status=None, status_reason=None,
            timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(user_id, timestamp, logging.WARNING, action=action,
                  status=status, status_reason=status_reason)
    event.store(context)
    LOG.warn(_LW('User [%(id)s] %(action)s - %(status)s: %(reason)s'),
             {'id': user_id,
              'action': action,
              'status': status,
              'reason': status_reason})


def info(context, user_id, action, status=None, status_reason=None,
         timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(user_id, timestamp, logging.INFO, action=action,
                  status=status, status_reason=status_reason)
    event.store(context)
    LOG.info(_LI('User [%(id)s] %(action)s - %(status)s: %(reason)s'),
             {'id': user_id,
              'action': action,
              'status': status,
              'reason': status_reason})


def debug(context, user_id, action, status=None, status_reason=None,
          timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(user_id, timestamp, logging.DEBUG, action=action,
                  status=status, status_reason=status_reason)
    event.store(context)
    LOG.debug(_('User [%(id)s] %(action)s - %(status)s: %(reason)s'),
              {'id': user_id,
               'action': action,
               'status': status,
               'reason': status_reason})
