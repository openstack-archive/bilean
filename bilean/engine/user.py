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

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import utils
from bilean.db import api as db_api
from bilean.engine import event as event_mod
from bilean.engine import resource as resource_mod

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

LOG = logging.getLogger(__name__)


class User(object):
    """User object contains all user operations"""

    statuses = (
        INIT, FREE, ACTIVE, WARNING, FREEZE,
    ) = (
        'INIT', 'FREE', 'ACTIVE', 'WARNING', 'FREEZE',
    )

    def __init__(self, user_id, **kwargs):
        self.id = user_id
        self.policy_id = kwargs.get('policy_id', None)
        self.balance = kwargs.get('balance', 0)
        self.rate = kwargs.get('rate', 0.0)
        self.credit = kwargs.get('credit', 0)
        self.last_bill = kwargs.get('last_bill', None)

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Init user')

        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)
        self.deleted_at = kwargs.get('deleted_at', None)

    def store(self, context):
        """Store the user record into database table."""

        values = {
            'policy_id': self.policy_id,
            'balance': self.balance,
            'rate': self.rate,
            'credit': self.credit,
            'last_bill': self.last_bill,
            'status': self.status,
            'status_reason': self.status_reason,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'deleted_at': self.deleted_at,
        }

        if self.created_at:
            db_api.user_update(context, self.id, values)
        else:
            values.update(id=self.id)
            user = db_api.user_create(context, values)
            self.created_at = user.created_at

        return self.id

    @classmethod
    def init_users(cls, context):
        """Init users from keystone."""
        k_client = context.clients.client('keystone')
        tenants = k_client.tenants.list()
        tenant_ids = [tenant.id for tenant in tenants]

        users = cls.load_all(context)
        user_ids = [user.id for user in users]
        for tid in tenant_ids:
            if tid not in user_ids:
                user = cls(tid, status=cls.INIT,
                           status_reason='Init from keystone')
                user.store(context)
        return True

    @classmethod
    def _from_db_record(cls, record):
        '''Construct a user object from database record.

        :param record: a DB user object that contains all fields;
        '''
        kwargs = {
            'policy_id': record.policy_id,
            'balance': record.balance,
            'rate': record.rate,
            'credit': record.credit,
            'last_bill': record.last_bill,
            'status': record.status,
            'status_reason': record.status_reason,
            'created_at': record.created_at,
            'updated_at': record.updated_at,
            'deleted_at': record.deleted_at,
        }

        return cls(record.id, **kwargs)

    @classmethod
    def load(cls, context, user_id=None, user=None, realtime=False,
             show_deleted=False, tenant_safe=True):
        '''Retrieve a user from database.'''
        if user is None:
            user = db_api.user_get(context, user_id,
                                   show_deleted=show_deleted,
                                   tenant_safe=tenant_safe)
            if user is None:
                raise exception.UserNotFound(user=user_id)

        u = cls._from_db_record(user)
        if not realtime:
            return u
        if u.rate > 0 and u.status != u.FREEZE:
            seconds = (timeutils.utcnow() - u.last_bill).total_seconds()
            u.balance -= u.rate * seconds
        return u

    @classmethod
    def load_all(cls, context, show_deleted=False, limit=None,
                 marker=None, sort_keys=None, sort_dir=None,
                 filters=None):
        '''Retrieve all users of from database.'''

        records = db_api.user_get_all(context, show_deleted=show_deleted,
                                      limit=limit, marker=marker,
                                      sort_keys=sort_keys, sort_dir=sort_dir,
                                      filters=filters)

        return [cls._from_db_record(record) for record in records]

    def to_dict(self):
        user_dict = {
            'id': self.id,
            'policy_id': self.policy_id,
            'balance': self.balance,
            'rate': self.rate,
            'credit': self.credit,
            'last_bill': utils.format_time(self.last_bill),
            'status': self.status,
            'status_reason': self.status_reason,
            'created_at': utils.format_time(self.created_at),
            'updated_at': utils.format_time(self.updated_at),
            'deleted_at': utils.format_time(self.deleted_at),
        }
        return user_dict

    def set_status(self, status, reason=None):
        '''Set status of the user.'''
        self.status = status
        if reason:
            self.status_reason = reason

    def update_with_resource(self, context, resource, action='create'):
        '''Update user with resource'''
        if 'create' == action:
            d_rate = resource.rate
            if self.rate > 0:
                self.do_bill(context)
        elif 'delete' == action:
            self.do_bill(context)
            d_rate = -resource.rate
        elif 'update' == action:
            self.do_bill(context)
            d_rate = resource.d_rate
        self._change_user_rate(context, d_rate)
        self.store(context)

    def _change_user_rate(self, context, d_rate):
        # Update the rate of user
        old_rate = self.rate
        new_rate = old_rate + d_rate
        if old_rate == 0 and new_rate > 0:
            self.last_bill = timeutils.utcnow()
        if d_rate > 0 and self.status == self.FREE:
            self.status = self.ACTIVE
        elif d_rate < 0:
            if new_rate == 0 and self.balance > 0:
                self.status = self.FREE
            elif self.status == self.WARNING:
                p_time = cfg.CONF.bilean_task.prior_notify_time * 3600
                rest_usage = p_time * new_rate
                if self.balance > rest_usage:
                    self.status = self.ACTIVE
        self.rate = new_rate

    def do_recharge(self, context, value):
        '''Do recharge for user.'''
        if self.rate > 0 and self.status != self.FREEZE:
            self.do_bill(context)
        self.balance += value
        if self.status == self.INIT and self.balance > 0:
            self.set_status(self.ACTIVE, reason='Recharged')
        elif self.status == self.FREEZE and self.balance > 0:
            reason = _("Status change from freeze to active because "
                       "of recharge.")
            self.set_status(self.ACTIVE, reason=reason)
        elif self.status == self.WARNING:
            prior_notify_time = cfg.CONF.bilean_task.prior_notify_time * 3600
            rest_usage = prior_notify_time * self.rate
            if self.balance > rest_usage:
                reason = _("Status change from warning to active because "
                           "of recharge.")
                self.set_status(self.ACTIVE, reason=reason)
        event_mod.record(context, self.id, action='recharge', value=value)
        self.store(context)

    def _freeze(self, context, reason=None):
        '''Freeze user when balance overdraft.'''
        LOG.info(_("Freeze user because of: %s") % reason)
        self._release_resource(context)
        LOG.info(_("Balance of user %s overdraft, change user's "
                   "status to 'freeze'") % self.id)
        self.status = self.FREEZE
        self.status_reason = reason

    def _release_resource(self, context):
        '''Do freeze user, delete all resources ralated to user.'''
        filters = {'user_id': self.id}
        resources = resource_mod.Resource.load_all(context, filters=filters)
        for resource in resources:
            resource.do_delete(context)

    def do_delete(self, context):
        db_api.user_delete(context, self.id)
        return True

    def do_bill(self, context):
        '''Do bill once, pay the cost until now.'''
        now = timeutils.utcnow()
        total_seconds = (now - self.last_bill).total_seconds()
        self.balance = self.balance - self.rate * total_seconds
        self.last_bill = now
        if self.balance < 0:
            self._freeze(context, reason="Balance overdraft")
        self.store(context)
        event_mod.record(context, self.id,
                         action='charge',
                         seconds=total_seconds)
