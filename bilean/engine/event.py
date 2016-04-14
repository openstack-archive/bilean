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
from oslo_utils import reflection
from oslo_utils import timeutils

LOG = log.getLogger(__name__)


class Event(object):
    '''capturing an interesting happening in Bilean.'''

    def __init__(self, timestamp, level, entity=None, **kwargs):
        self.timestamp = timestamp
        self.level = level

        self.id = kwargs.get('id')
        self.user_id = kwargs.get('user_id')

        self.action = kwargs.get('action')
        self.status = kwargs.get('status')
        self.status_reason = kwargs.get('status_reason')

        self.obj_id = kwargs.get('obj_id')
        self.obj_type = kwargs.get('obj_type')
        self.obj_name = kwargs.get('obj_name')
        self.metadata = kwargs.get('metadata')

        cntx = kwargs.get('context')
        if cntx is not None:
            self.user_id = cntx.project

        if entity is not None:
            self.obj_id = entity.id
            self.obj_name = entity.name
            e_type = reflection.get_class_name(entity, fully_qualified=False)
            self.obj_type = e_type.upper()

    @classmethod
    def from_db_record(cls, record):
        '''Construct an event object from a database record.'''

        kwargs = {
            'id': record.id,
            'user_id': record.user_id,
            'action': record.action,
            'status': record.status,
            'status_reason': record.status_reason,
            'obj_id': record.obj_id,
            'obj_type': record.obj_type,
            'obj_name': record.obj_name,
            'metadata': record.meta_data,
        }
        return cls(record.timestamp, record.level, **kwargs)

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
            'level': self.level,
            'user_id': self.user_id,
            'action': self.action,
            'status': self.status,
            'status_reason': self.status_reason,
            'obj_id': self.obj_id,
            'obj_type': self.obj_type,
            'obj_name': self.obj_name,
            'meta_data': self.metadata,
        }

        event = db_api.event_create(context, values)
        self.id = event.id

        return self.id

    def to_dict(self):
        evt = {
            'id': self.id,
            'level': self.level,
            'user_id': self.user_id,
            'action': self.action,
            'status': self.status,
            'status_reason': self.status_reason,
            'obj_id': self.obj_id,
            'obj_type': self.obj_type,
            'obj_name': self.obj_name,
            'timestamp': utils.format_time(self.timestamp),
            'metadata': self.metadata,
        }
        return evt


def critical(context, entity, action, status=None, status_reason=None,
             timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(timestamp, logging.CRITICAL, entity,
                  action=action, status=status, status_reason=status_reason,
                  user_id=context.project)
    event.store(context)
    LOG.critical(_LC('%(name)s [%(id)s] - %(status)s: %(reason)s'),
                 {'name': event.obj_name,
                  'id': event.obj_id and event.obj_id[:8],
                  'status': status,
                  'reason': status_reason})


def error(context, entity, action, status=None, status_reason=None,
          timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(timestamp, logging.ERROR, entity,
                  action=action, status=status, status_reason=status_reason,
                  user_id=context.project)
    event.store(context)
    LOG.error(_LE('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s'),
              {'name': event.obj_name,
               'id': event.obj_id and event.obj_id[:8],
               'action': action,
               'status': status,
               'reason': status_reason})


def warning(context, entity, action, status=None, status_reason=None,
            timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(timestamp, logging.WARNING, entity,
                  action=action, status=status, status_reason=status_reason,
                  user_id=context.project)
    event.store(context)
    LOG.warning(_LW('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s'),
                {'name': event.obj_name,
                 'id': event.obj_id and event.obj_id[:8],
                 'action': action,
                 'status': status,
                 'reason': status_reason})


def info(context, entity, action, status=None, status_reason=None,
         timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(timestamp, logging.INFO, entity,
                  action=action, status=status, status_reason=status_reason,
                  user_id=context.project)
    event.store(context)
    LOG.info(_LI('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s'),
             {'name': event.obj_name,
              'id': event.obj_id and event.obj_id[:8],
              'action': action,
              'status': status,
              'reason': status_reason})


def debug(context, entity, action, status=None, status_reason=None,
          timestamp=None):
    timestamp = timestamp or timeutils.utcnow()
    event = Event(timestamp, logging.DEBUG, entity,
                  action=action, status=status, status_reason=status_reason,
                  user_id=context.project)
    event.store(context)
    LOG.debug(_('%(name)s [%(id)s] %(action)s - %(status)s: %(reason)s'),
              {'name': event.obj_name,
               'id': event.obj_id and event.obj_id[:8],
               'action': action,
               'status': status,
               'reason': status_reason})
