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
"""
SQLAlchemy models for heat data.
"""

import uuid

from bilean.db.sqlalchemy import types

from oslo_db.sqlalchemy import models
from oslo_serialization import jsonutils
from oslo_utils import timeutils

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session

BASE = declarative_base()


def get_session():
    from bilean.db.sqlalchemy import api as db_api
    return db_api.get_session()


class BileanBase(models.ModelBase, models.TimestampMixin):
    """Base class for Heat Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}

    def expire(self, session=None, attrs=None):
        """Expire this object ()."""
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.expire(self, attrs)

    def refresh(self, session=None, attrs=None):
        """Refresh this object."""
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.refresh(self, attrs)

    def delete(self, session=None):
        """Delete this object."""
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.delete(self)
        session.flush()

    def update_and_save(self, values, session=None):
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.begin()
        for k, v in values.iteritems():
            setattr(self, k, v)
        session.commit()


class SoftDelete(object):
    deleted_at = sqlalchemy.Column(sqlalchemy.DateTime)
    deleted = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

    def soft_delete(self, session=None):
        """Mark this object as deleted."""
        self.update_and_save({'deleted_at': timeutils.utcnow(),
                              'deleted': True}, session=session)


class StateAware(object):

    status = sqlalchemy.Column('status', sqlalchemy.String(10))
    _status_reason = sqlalchemy.Column('status_reason', sqlalchemy.String(255))

    @property
    def status_reason(self):
        return self._status_reason

    @status_reason.setter
    def status_reason(self, reason):
        self._status_reason = reason and reason[:255] or ''


class User(BASE, BileanBase, StateAware):
    """Represents a user to record account"""

    __tablename__ = 'user'
    id = sqlalchemy.Column(sqlalchemy.String(36), primary_key=True)
    balance = sqlalchemy.Column(sqlalchemy.Float, default=0.0)
    rate = sqlalchemy.Column(sqlalchemy.Float, default=0.0)
    credit = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    last_bill = sqlalchemy.Column(
        sqlalchemy.DateTime, default=timeutils.utcnow())
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime)


class Rule(BASE, BileanBase):
    """Represents a rule created to bill someone resource"""

    __tablename__ = 'rule'
    id = sqlalchemy.Column(sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    name = sqlalchemy.Column(sqlalchemy.String(255))
    type = sqlalchemy.Column(sqlalchemy.String(255))
    spec = sqlalchemy.Column(types.Dict)
    meta_data = sqlalchemy.Column(types.Dict)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime)


class Resource(BASE, BileanBase, StateAware, SoftDelete):
    """Represents a meta resource with rate"""

    __tablename__ = 'resource'
    id = sqlalchemy.Column(sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()))
    resource_ref = sqlalchemy.Column(sqlalchemy.String(36), nullable=False)
    user_id = sqlalchemy.Column(
        sqlalchemy.String(36),
        sqlalchemy.ForeignKey('user.id'),
        nullable=False)
    rule_id = sqlalchemy.Column(
        sqlalchemy.String(36),
        sqlalchemy.ForeignKey('rule.id'),
        nullable=False)
    user = relationship(User, backref=backref('resource'))
    rule = relationship(Rule, backref=backref('resource'))
    resource_type = sqlalchemy.Column(sqlalchemy.String(36), nullable=False)
    size = sqlalchemy.Column(sqlalchemy.String(36), nullable=False)
    rate = sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime)


class Event(BASE, BileanBase):
    """Represents an event generated by the bilean engine."""

    __tablename__ = 'event'

    id = sqlalchemy.Column(sqlalchemy.String(36), primary_key=True,
                           default=lambda: str(uuid.uuid4()),
                           unique=True)
    user_id = sqlalchemy.Column(sqlalchemy.String(36),
                                sqlalchemy.ForeignKey('user.id'),
                                nullable=False)
    user = relationship(User, backref=backref('event'))
    resource_id = sqlalchemy.Column(sqlalchemy.String(36))
    action = sqlalchemy.Column(sqlalchemy.String(36))
    resource_type = sqlalchemy.Column(sqlalchemy.String(36))
    value = sqlalchemy.Column(sqlalchemy.Float)


class Job(BASE, BileanBase):
    """Represents a job for per user"""

    __tablename__ = 'job'

    id = sqlalchemy.Column(sqlalchemy.String(50), primary_key=True,
                           unique=True)
    engine_id = sqlalchemy.Column(sqlalchemy.String(36))
    job_type = sqlalchemy.Column(sqlalchemy.String(10))
    parameters = sqlalchemy.Column(types.Dict())
