# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import six
import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from bilean.common import context as req_context
from bilean.common import exception
from bilean.common.i18n import _, _LE
from bilean.common import utils
from bilean.db import api as db_api
from bilean.engine import event as EVENT

wallclock = time.time
LOG = logging.getLogger(__name__)

# Action causes
CAUSES = (
    CAUSE_RPC, CAUSE_DERIVED,
) = (
    'RPC Request',
    'Derived Action',
)


class Action(object):
    '''An action can be performed on a user, rule or policy.'''

    RETURNS = (
        RES_OK, RES_ERROR, RES_RETRY, RES_CANCEL, RES_TIMEOUT,
    ) = (
        'OK', 'ERROR', 'RETRY', 'CANCEL', 'TIMEOUT',
    )

    # Action status definitions:
    #  INIT:      Not ready to be executed because fields are being modified,
    #             or dependency with other actions are being analyzed.
    #  READY:     Initialized and ready to be executed by a worker.
    #  RUNNING:   Being executed by a worker thread.
    #  SUCCEEDED: Completed with success.
    #  FAILED:    Completed with failure.
    #  CANCELLED: Action cancelled because worker thread was cancelled.
    STATUSES = (
        INIT, WAITING, READY, RUNNING, SUSPENDED,
        SUCCEEDED, FAILED, CANCELLED
    ) = (
        'INIT', 'WAITING', 'READY', 'RUNNING', 'SUSPENDED',
        'SUCCEEDED', 'FAILED', 'CANCELLED',
    )

    # Signal commands
    COMMANDS = (
        SIG_CANCEL, SIG_SUSPEND, SIG_RESUME,
    ) = (
        'CANCEL', 'SUSPEND', 'RESUME',
    )

    def __new__(cls, target, action, context, **kwargs):
        if (cls != Action):
            return super(Action, cls).__new__(cls)

        target_type = action.split('_')[0]
        if target_type == 'USER':
            from bilean.engine.actions import user_action
            ActionClass = user_action.UserAction
        # elif target_type == 'RULE':
        #     from bilean.engine.actions import rule_action
        #     ActionClass = rule_action.RuleAction
        # elif target_type == 'POLICY':
        #     from bilean.engine.actions import policy_action
        #     ActionClass = policy_action.PolicyAction

        return super(Action, cls).__new__(ActionClass)

    def __init__(self, target, action, context, **kwargs):
        # context will be persisted into database so that any worker thread
        # can pick the action up and execute it on behalf of the initiator

        self.id = kwargs.get('id', None)
        self.name = kwargs.get('name', '')

        self.context = context

        self.action = action
        self.target = target

        # Why this action is fired, it can be a UUID of another action
        self.cause = kwargs.get('cause', '')

        # Owner can be an UUID format ID for the worker that is currently
        # working on the action.  It also serves as a lock.
        self.owner = kwargs.get('owner', None)

        self.start_time = utils.make_decimal(kwargs.get('start_time', 0))
        self.end_time = utils.make_decimal(kwargs.get('end_time', 0))

        # Timeout is a placeholder in case some actions may linger too long
        self.timeout = kwargs.get('timeout', cfg.CONF.default_action_timeout)

        # Return code, useful when action is not automatically deleted
        # after execution
        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', '')

        # All parameters are passed in using keyword arguments which is
        # a dictionary stored as JSON in DB
        self.inputs = kwargs.get('inputs', {})
        self.outputs = kwargs.get('outputs', {})

        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)

        self.data = kwargs.get('data', {})

    def store(self, context):
        """Store the action record into database table.

        :param context: An instance of the request context.
        :return: The ID of the stored object.
        """

        timestamp = timeutils.utcnow()

        values = {
            'name': self.name,
            'context': self.context.to_dict(),
            'target': self.target,
            'action': self.action,
            'cause': self.cause,
            'owner': self.owner,
            'start_time': utils.format_decimal(self.start_time),
            'end_time': utils.format_decimal(self.end_time),
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'data': self.data,
        }

        if self.id:
            self.updated_at = timestamp
            values['updated_at'] = timestamp
            db_api.action_update(context, self.id, values)
        else:
            self.created_at = timestamp
            values['created_at'] = timestamp
            action = db_api.action_create(context, values)
            self.id = action.id

        return self.id

    @classmethod
    def _from_db_record(cls, record):
        """Construct a action object from database record.

        :param context: the context used for DB operations;
        :param record: a DB action object that contains all fields.
        :return: An `Action` object deserialized from the DB action object.
        """
        context = req_context.RequestContext.from_dict(record.context)
        kwargs = {
            'id': record.id,
            'name': record.name,
            'cause': record.cause,
            'owner': record.owner,
            'start_time': record.start_time,
            'end_time': record.end_time,
            'timeout': record.timeout,
            'status': record.status,
            'status_reason': record.status_reason,
            'inputs': record.inputs or {},
            'outputs': record.outputs or {},
            'created_at': record.created_at,
            'updated_at': record.updated_at,
            'data': record.data,
        }

        return cls(record.target, record.action, context, **kwargs)

    @classmethod
    def load(cls, context, action_id=None, db_action=None):
        """Retrieve an action from database.

        :param context: Instance of request context.
        :param action_id: An UUID for the action to deserialize.
        :param db_action: An action object for the action to deserialize.
        :return: A `Action` object instance.
        """
        if db_action is None:
            db_action = db_api.action_get(context, action_id)
            if db_action is None:
                raise exception.ActionNotFound(action=action_id)

        return cls._from_db_record(db_action)

    @classmethod
    def load_all(cls, context, filters=None, limit=None, marker=None,
                 sort_keys=None, sort_dir=None):
        """Retrieve all actions from database."""

        records = db_api.action_get_all(context, filters=filters,
                                        limit=limit, marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir)

        for record in records:
            yield cls._from_db_record(record)

    @classmethod
    def create(cls, context, target, action, **kwargs):
        """Create an action object.

        :param context: The requesting context.
        :param target: The ID of the target.
        :param action: Name of the action.
        :param dict kwargs: Other keyword arguments for the action.
        :return: ID of the action created.
        """
        params = {
            'user': context.user,
            'project': context.project,
            'domain': context.domain,
            'is_admin': context.is_admin,
            'request_id': context.request_id,
            'trusts': context.trusts,
        }
        ctx = req_context.RequestContext.from_dict(params)
        obj = cls(target, action, ctx, **kwargs)
        return obj.store(context)

    @classmethod
    def delete(cls, context, action_id):
        """Delete an action from database."""
        db_api.action_delete(context, action_id)

    def signal(self, cmd):
        '''Send a signal to the action.'''
        if cmd not in self.COMMANDS:
            return

        if cmd == self.SIG_CANCEL:
            expected_statuses = (self.INIT, self.WAITING, self.READY,
                                 self.RUNNING)
        elif cmd == self.SIG_SUSPEND:
            expected_statuses = (self.RUNNING)
        else:     # SIG_RESUME
            expected_statuses = (self.SUSPENDED)

        if self.status not in expected_statuses:
            reason = _("Action (%(action)s) is in unexpected status "
                       "(%(actual)s) while expected status should be one of "
                       "(%(expected)s).") % dict(action=self.id,
                                                 expected=expected_statuses,
                                                 actual=self.status)
            EVENT.error(self.context, self, cmd, status_reason=reason)
            return

        db_api.action_signal(self.context, self.id, cmd)

    def execute(self, **kwargs):
        '''Execute the action.

        In theory, the action encapsulates all information needed for
        execution.  'kwargs' may specify additional parameters.
        :param kwargs: additional parameters that may override the default
                       properties stored in the action record.
        '''
        return NotImplemented

    def set_status(self, result, reason=None):
        """Set action status based on return value from execute."""

        timestamp = wallclock()

        if result == self.RES_OK:
            status = self.SUCCEEDED
            db_api.action_mark_succeeded(self.context, self.id, timestamp)

        elif result == self.RES_ERROR:
            status = self.FAILED
            db_api.action_mark_failed(self.context, self.id, timestamp,
                                      reason=reason or 'ERROR')

        elif result == self.RES_TIMEOUT:
            status = self.FAILED
            db_api.action_mark_failed(self.context, self.id, timestamp,
                                      reason=reason or 'TIMEOUT')

        elif result == self.RES_CANCEL:
            status = self.CANCELLED
            db_api.action_mark_cancelled(self.context, self.id, timestamp)

        else:  # result == self.RES_RETRY:
            status = self.READY
            # Action failed at the moment, but can be retried
            # We abandon it and then notify other dispatchers to execute it
            db_api.action_abandon(self.context, self.id)

        if status == self.SUCCEEDED:
            EVENT.info(self.context, self, self.action, status, reason)
        elif status == self.READY:
            EVENT.warning(self.context, self, self.action, status, reason)
        else:
            EVENT.error(self.context, self, self.action, status, reason)

        self.status = status
        self.status_reason = reason

    def get_status(self):
        timestamp = wallclock()
        status = db_api.action_check_status(self.context, self.id, timestamp)
        self.status = status
        return status

    def is_timeout(self):
        time_lapse = wallclock() - self.start_time
        return time_lapse > self.timeout

    def _check_signal(self):
        # Check timeout first, if true, return timeout message
        if self.timeout is not None and self.is_timeout():
            EVENT.debug(self.context, self, self.action, 'TIMEOUT')
            return self.RES_TIMEOUT

        result = db_api.action_signal_query(self.context, self.id)
        return result

    def is_cancelled(self):
        return self._check_signal() == self.SIG_CANCEL

    def is_suspended(self):
        return self._check_signal() == self.SIG_SUSPEND

    def is_resumed(self):
        return self._check_signal() == self.SIG_RESUME

    def to_dict(self):
        if self.id:
            dep_on = db_api.dependency_get_depended(self.context, self.id)
            dep_by = db_api.dependency_get_dependents(self.context, self.id)
        else:
            dep_on = []
            dep_by = []
        action_dict = {
            'id': self.id,
            'name': self.name,
            'action': self.action,
            'target': self.target,
            'cause': self.cause,
            'owner': self.owner,
            'start_time': utils.dec2str(self.start_time),
            'end_time': utils.dec2str(self.end_time),
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'depends_on': dep_on,
            'depended_by': dep_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'data': self.data,
        }
        return action_dict


def ActionProc(context, action_id):
    '''Action process.'''

    action = Action.load(context, action_id=action_id)
    if action is None:
        LOG.error(_LE('Action "%s" could not be found.'), action_id)
        return False

    reason = 'Action completed'
    success = True
    try:
        result, reason = action.execute()
    except Exception as ex:
        result = action.RES_ERROR
        reason = six.text_type(ex)
        LOG.exception(_('Unexpected exception occurred during action '
                        '%(action)s (%(id)s) execution: %(reason)s'),
                      {'action': action.action, 'id': action.id,
                       'reason': reason})
        success = False
    finally:
        # NOTE: locks on action is eventually released here by status update
        action.set_status(result, reason)

    return success
