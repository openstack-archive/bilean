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

from bilean.common.i18n import _
from bilean.common import utils
from bilean.db import api as db_api
from bilean.engine import api
from bilean.engine import events

from oslo_log import log as logging
from oslo_utils import timeutils

LOG = logging.getLogger(__name__)


class User(object):
    """User object contains all user operations"""

    statuses = (
        INIT, ACTIVE, WARNING, FREEZE,
    ) = (
        'INIT', 'ACTIVE', 'WARNING', 'FREEZE',
    )

    def __init__(self, user_id, policy_id, **kwargs):
        self.id = user_id 
        self.policy_id = policy_id
        self.balance = kwargs.get('balance', 0)
        self.rate = kwargs.get('rate', 0.0)
        self.credit = kwargs.get('credit', 0)
        self.last_bill = kwargs.get('last_bill', None)

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Init user')

        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)
        self.deleted_at = kwargs.get('deleted_at', None)

    def store(context, values):
        """Store the user record into database table.
        """

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
    def _from_db_record(cls, context, record):
        '''Construct a user object from database record.

        :param context: the context used for DB operations;
        :param record: a DB user object that contains all fields;
        '''
        kwargs = {
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

        return cls(record.id, record.policy_id, **kwargs)

    @classmethod
    def load(cls, context, user_id=None, user=None, show_deleted=False,
             project_safe=True):
        '''Retrieve a user from database.'''
        if user is None:
            user = db_api.user_get(context, user_id,
                                   show_deleted=show_deleted,
                                   project_safe=project_safe)
            if user is None:
                raise exception.UserNotFound(user=user_id)

        return cls._from_db_record(context, user)

    @classmethod
    def load_all(cls, context, show_deleted=False, limit=None,
                 marker=None, sort_keys=None, sort_dir=None,
                 filters=None, project_safe=True):
        '''Retrieve all users of from database.'''

        records = db_api.user_get_all(context, show_deleted=show_deleted,
                                      limit=limit, marker=marker,
                                      sort_keys=sort_keys, sort_dir=sort_dir,
                                      filters=filters,
                                      project_safe=project_safe)

        return [cls._from_db_record(context, record) for record in records]

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
 
    def set_status(self, context, status, reason=None):
        '''Set status of the user.'''

        self.status = status
        values['status'] = status
        if reason:
            self.status_reason = reason
            values['status_reason'] = reason
        db_api.user_update(context, self.id, values)

    def do_delete(self, context):
        db_api.user_delete(context, self.id)
        return True

    def do_bill(self, context, user, update=False, bilean_controller=None):
        now = timeutils.utcnow()
        last_bill = user['last_bill']
        if not last_bill:
            LOG.error(_("Last bill info not found"))
            return
        total_seconds = (now - last_bill).total_seconds()
        if total_seconds < 0:
            LOG.error(_("Now time is earlier than last bill!"))
            return
        usage = user['rate'] / 3600.0 * total_seconds
        new_balance = user['balance'] - usage
        if not update:
            user['balance'] = new_balance
            return user
        else:
            update_values = {}
            update_values['balance'] = new_balance
            update_values['last_bill'] = now
            if new_balance < 0:
                if bilean_controller:
                    bilean_controller.do_freeze_action(context, user['id'])
                update_values['status'] = 'freeze'
                update_values['status_reason'] = 'balance overdraft'
                LOG.info(_("Balance of user %s overdraft, change user's status to "
                           "'freeze'") % user['id'])
            new_user = update_user(context, user['id'], update_values)
            events.generate_events(context,
                                   user['id'],
                                   'charge',
                                   time_length=total_seconds)
            return new_user
