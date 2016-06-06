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

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common.i18n import _LE
from bilean.common.i18n import _LI
from bilean.engine.actions import base
from bilean.engine import event as EVENT
from bilean.engine.flows import flow as bilean_flow
from bilean.engine import lock as bilean_lock
from bilean.engine import user as user_mod
from bilean.plugins import base as plugin_base

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class UserAction(base.Action):
    """An action that can be performed on a user."""

    ACTIONS = (
        USER_CREATE_RESOURCE, USER_UPDATE_RESOUCE, USER_DELETE_RESOURCE,
        USER_SETTLE_ACCOUNT,
    ) = (
        'USER_CREATE_RESOURCE', 'USER_UPDATE_RESOUCE', 'USER_DELETE_RESOURCE',
        'USER_SETTLE_ACCOUNT',
    )

    def __init__(self, target, action, context, **kwargs):
        """Constructor for a user action object.

        :param target: ID of the target user object on which the action is to
                       be executed.
        :param action: The name of the action to be executed.
        :param context: The context used for accessing the DB layer.
        :param dict kwargs: Additional parameters that can be passed to the
                            action.
        """
        super(UserAction, self).__init__(target, action, context, **kwargs)

        try:
            self.user = user_mod.User.load(self.context, user_id=self.target)
        except Exception:
            self.user = None

    def do_create_resource(self):
        resource = plugin_base.Resource.from_dict(self.inputs)
        try:
            flow_engine = bilean_flow.get_create_resource_flow(
                self.context, self.target, resource)
            with bilean_flow.DynamicLogListener(flow_engine, logger=LOG):
                flow_engine.run()
        except Exception as ex:
            LOG.error(_LE("Faied to execute action(%(action_id)s), error: "
                          "%(error_msg)s"), {"action_id": self.id,
                                             "error_msg": six.text_type(ex)})
            return self.RES_ERROR, _('Resource creation failed.')

        return self.RES_OK, _('Resource creation successfully.')

    def do_update_resource(self):
        try:
            values = self.inputs
            resource_id = values.pop('id', None)
            resource = plugin_base.Resource.load(
                self.context, resource_id=resource_id)
        except exception.ResourceNotFound:
            LOG.error(_LE('The resource(%s) trying to update not found.'),
                      resource_id)
            return self.RES_ERROR, _('Resource not found.')

        try:
            flow_engine = bilean_flow.get_update_resource_flow(
                self.context, self.target, resource, values)
            with bilean_flow.DynamicLogListener(flow_engine, logger=LOG):
                flow_engine.run()
        except Exception as ex:
            LOG.error(_LE("Faied to execute action(%(action_id)s), error: "
                          "%(error_msg)s"), {"action_id": self.id,
                                             "error_msg": six.text_type(ex)})
            return self.RES_ERROR, _('Resource update failed.')

        LOG.info(_LI('Successfully updated resource: %s'), resource.id)
        return self.RES_OK, _('Resource update successfully.')

    def do_delete_resource(self):
        try:
            resource_id = self.inputs.get('resource_id')
            resource = plugin_base.Resource.load(
                self.context, resource_id=resource_id)
        except exception.ResourceNotFound:
            LOG.error(_LE('The resource(%s) trying to delete not found.'),
                      resource_id)
            return self.RES_ERROR, _('Resource not found.')

        try:
            flow_engine = bilean_flow.get_delete_resource_flow(
                self.context, self.target, resource)
            with bilean_flow.DynamicLogListener(flow_engine, logger=LOG):
                flow_engine.run()
        except Exception as ex:
            LOG.error(_LE("Faied to execute action(%(action_id)s), error: "
                          "%(error_msg)s"), {"action_id": self.id,
                                             "error_msg": six.text_type(ex)})
            return self.RES_ERROR, _('Resource deletion failed.')

        LOG.info(_LI('Successfully deleted resource: %s'), resource.id)
        return self.RES_OK, _('Resource deletion successfully.')

    def do_settle_account(self):
        try:
            flow_engine = bilean_flow.get_settle_account_flow(
                self.context, self.target, task=self.inputs.get('task'))
            with bilean_flow.DynamicLogListener(flow_engine, logger=LOG):
                flow_engine.run()
        except Exception as ex:
            LOG.error(_LE("Faied to execute action(%(action_id)s), error: "
                          "%(error_msg)s"), {"action_id": self.id,
                                             "error_msg": six.text_type(ex)})
            return self.RES_ERROR, _('Settle account failed.')

        return self.RES_OK, _('Settle account successfully.')

    def _execute(self):
        """Private function that finds out the handler and execute it."""

        action_name = self.action.lower()
        method_name = action_name.replace('user', 'do')
        method = getattr(self, method_name, None)

        if method is None:
            reason = _('Unsupported action: %s') % self.action
            EVENT.error(self.context, self.user, self.action, 'Failed', reason)
            return self.RES_ERROR, reason

        return method()

    def execute(self, **kwargs):
        """Interface function for action execution.

        :param dict kwargs: Parameters provided to the action, if any.
        :returns: A tuple containing the result and the related reason.
        """

        try:
            res = bilean_lock.user_lock_acquire(self.context, self.target,
                                                self.id, self.owner)
            if not res:
                LOG.error(_LE('Failed grabbing the lock for user: %s'),
                          self.target)
                res = self.RES_ERROR
                reason = _('Failed in locking user')
            else:
                res, reason = self._execute()
        finally:
            bilean_lock.user_lock_release(self.target, self.id)

        return res, reason
