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
from bilean.common.i18n import _LI
from bilean.common import utils
from bilean.db import api as db_api
from bilean.drivers import base as driver_base
from bilean.engine import event as event_mod
from bilean import notifier as bilean_notifier
from bilean.resources import base as resource_base

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

    ALLOW_DELAY_TIME = 10

    def __init__(self, user_id, **kwargs):
        self.id = user_id
        self.name = kwargs.get('name')
        self.policy_id = kwargs.get('policy_id')
        self.balance = kwargs.get('balance', 0)
        self.rate = kwargs.get('rate', 0.0)
        self.credit = kwargs.get('credit', 0)
        self.last_bill = kwargs.get('last_bill')

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Init user')

        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.deleted_at = kwargs.get('deleted_at')

        if self.name is None:
            self.name = self._retrieve_name(self.id)

    def store(self, context):
        """Store the user record into database table."""

        values = {
            'name': self.name,
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
        keystoneclient = driver_base.BileanDriver().identity()
        try:
            projects = keystoneclient.project_list()
        except exception.InternalError as ex:
            LOG.exception(_('Failed in retrieving project list: %s'),
                          six.text_type(ex))
            return False

        users = cls.load_all(context)
        user_ids = [user.id for user in users]
        for project in projects:
            if project.id not in user_ids:
                user = cls(project.id, name=project.name, status=cls.INIT,
                           status_reason='Init from keystone')
                user.store(context)
                users.append(user)
        return users

    def _retrieve_name(cls, user_id):
        '''Get user name form keystone.'''
        keystoneclient = driver_base.BileanDriver().identity()
        try:
            project = keystoneclient.project_find(user_id)
        except exception.InternalError as ex:
            LOG.exception(_('Failed in retrieving project: %s'),
                          six.text_type(ex))
            return None
        return project.name

    @classmethod
    def _from_db_record(cls, record):
        '''Construct a user object from database record.

        :param record: a DB user object that contains all fields;
        '''
        kwargs = {
            'name': record.name,
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
             show_deleted=False, project_safe=True):
        '''Retrieve a user from database.'''
        if context.is_admin:
            project_safe = False
        if user is None:
            user = db_api.user_get(context, user_id,
                                   show_deleted=show_deleted,
                                   project_safe=project_safe)
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

    @classmethod
    def delete(cls, context, user_id=None, user=None):
        '''Delete a user from database.'''
        if user is not None:
            db_api.user_delete(context, user_id=user.id)
            return True
        elif user_id is not None:
            db_api.user_delete(context, user_id=user_id)
            return True
        return False

    @classmethod
    def from_dict(cls, values):
        id = values.pop('id', None)
        return cls(id, **values)

    def to_dict(self):
        user_dict = {
            'id': self.id,
            'name': self.name,
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

    def set_status(self, context, status, reason=None):
        '''Set status of the user.'''
        self.status = status
        if reason:
            self.status_reason = reason
        self.store(context)

    def update_with_resource(self, context, resource,
                             resource_action='create'):
        '''Update user with resource'''

        now = timeutils.utcnow()
        extra_cost = 0
        if 'create' == resource_action:
            d_rate = resource.rate
            if resource.properties.get('created_at') is not None:
                created_at = timeutils.parse_strtime(
                    resource.properties.get('created_at'))
                extra_seconds = (now - created_at).total_seconds()
                extra_cost = d_rate * extra_seconds
        elif 'delete' == resource_action:
            d_rate = -resource.rate
            if resource.properties.get('deleted_at') is not None:
                deleted_at = timeutils.parse_strtime(
                    resource.properties.get('deleted_at'))
                extra_seconds = (now - deleted_at).total_seconds()
                extra_cost = d_rate * extra_seconds
        elif 'update' == resource_action:
            d_rate = resource.d_rate
            if resource.properties.get('updated_at') is not None:
                updated_at = timeutils.parse_strtime(
                    resource.properties.get('updated_at'))
                extra_seconds = (now - updated_at).total_seconds()
                extra_cost = d_rate * extra_seconds

        self._settle_account(context, extra_cost=extra_cost,
                             cause_resource=resource,
                             resource_action=resource_action)
        self._change_rate(context, d_rate)
        self.store(context)

    def do_create_resource(self, context, resource):
        delta_rate = resource.rate
        if delta_rate == 0:
            return
        extra_cost = 0
        create_time = resource.properties.get('created_at')
        if create_time is not None:
            created_at = timeutils.parse_strtime(create_time)
            now = timeutils.utcnow()
            delayed_seconds = (now - created_at).total_seconds()
            # Engine handle resource creation is delayed because of something,
            # we suppose less than ALLOW_DELAY_TIME is acceptable.
            if delayed_seconds > ALLOW_DELAY_TIME:
                extra_cost = delta_rate * delayed_seconds

        self._settle_account(context, extra_cost=extra_cost)
        self._change_rate(delta_rate)

    def do_update_resource(self, context, resource):
        delta_rate = resource.d_rate
        if delta_rate == 0:
            return
        extra_cost = 0
        update_time = resoure.properties.get('updated_at')
        if update_time is not None:
            updated_at = timeutils.parse_strtime(update_time)
            now = timeutils.utcnow()
            delayed_seconds = (now - updated_at).total_seconds()
            # Engine handle resource update is delayed because of something,
            # we suppose less than ALLOW_DELAY_TIME is acceptable.
            if delayed_seconds > ALLOW_DELAY_TIME:
                 extra_cost = d_rate * extra_seconds

        self._settle_account(context, extra_cost=extra_cost)
        self._change_rate(delta_rate)

    def _change_rate(self, d_rate):
        """Chnage user's rate by delta_rate."""
        old_rate = self.rate
        new_rate = old_rate + d_rate
        if old_rate == 0 and new_rate > 0:
            self.last_bill = timeutils.utcnow()
            reason = _("Status change to 'ACTIVE' caus resource creation.")
            self.status = self.ACTIVE
            self.status_reason = reason
        elif d_rate < 0:
            if new_rate == 0 and self.balance >= 0:
                reason = _("Status change to 'FREE' because of resource "
                           "deletion.")
                self.status = self.FREE
                self.status_reason = reason
            elif self.status == self.WARNING and not self._notify_or_not():
                reason = _("Status change from 'WARNING' to 'ACTIVE' "
                           "because of resource deletion.")
                self.status = self.ACTIVE
                self.status_reason = reason
        self.rate = new_rate

    def do_recharge(self, context, value, recharge_type=None, timestamp=None,
                    metadata=None):
        '''Do recharge for user.'''
        self.balance += value
        if self.status == self.INIT and self.balance > 0:
            self.status = self.FREE
            self.status_reason = "Recharged"
        elif self.status == self.FREEZE and self.balance > 0:
            reason = _("Status change from 'FREEZE' to 'FREE' because "
                       "of recharge.")
            self.status = self.FREE
            self.status_reason = reason
        elif self.status == self.WARNING:
            if not self._notify_or_not():
                reason = _("Status change from 'WARNING' to 'ACTIVE' because "
                           "of recharge.")
                self.status = self.ACTIVE
                self.status_reason = reason
        self.store(context)

        # Create recharge record
        values = {'value': value,
                  'recharge_type': recharge_type,
                  'timestamp': timestamp,
                  'metadata': metadata,
        }
        db_api.recharge_create(context, values)

    def _notify_or_not(self):
        '''Check if user should be notified.'''
        cfg.CONF.import_opt('prior_notify_time',
                            'bilean.scheduler.cron_scheduler',
                            group='scheduler')
        prior_notify_time = cfg.CONF.scheduler.prior_notify_time * 3600
        rest_usage = prior_notify_time * self.rate
        if self.balance > rest_usage:
            return False
        return True

    def do_delete(self, context):
        db_api.user_delete(context, self.id)
        return True

    def _settle_account(self, context, cause_resource=None,
                        resource_action=None, extra_cost=0):
        if self.status not in [self.ACTIVE, self.WARNING]:
            LOG.info(_LI("Ignore settlement action because user is in '%s' "
                         "status."), self.status)
            return
        now = timeutils.utcnow()
        total_seconds = (now - self.last_bill).total_seconds()
        cost = self.rate * total_seconds + extra_cost
        self.balance -= cost
        self.last_bill = now

    def settle_account(self, context, task=None):
        '''Settle account for user.'''

        notifier = bilean_notifier.Notifier()
        self._settle_account(context)

        if task == 'notify' and self._notify_or_not():
            self.status_reason = "The balance is almost used up"
            self.status = self.WARNING
            # Notify user
            msg = {'user': self.id, 'notification': self.status_reason}
            notifier.info('billing.notify', msg)
        elif task == 'freeze' and self.balance <= 0:
            reason = _("Balance overdraft")
            LOG.info(_LI("Freeze user %(user_id)s, reason: %(reason)s"),
                     {'user_id': self.id, 'reason': reason})
            resources = resource_base.Resource.load_all(
                context, user_id=self.id, project_safe=False)
            for resource in resources:
                resource.do_delete(context)
            self.rate = 0
            self.status = self.FREEZE
            self.status_reason = reason
            # Notify user
            msg = {'user': self.id, 'notification': self.status_reason}
            notifier.info('billing.notify', msg)

        self.store(context)
