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

import os

from oslo_log import log as logging
import taskflow.engines
from taskflow.listeners import base
from taskflow.listeners import logging as logging_listener
from taskflow.patterns import linear_flow
from taskflow import task
from taskflow.types import failure as ft

from bilean.common import exception
from bilean.common import utils
from bilean.engine import policy as policy_mod
from bilean.engine import user as user_mod
from bilean.plugins import base as plugin_base
from bilean import scheduler as bilean_scheduler

LOG = logging.getLogger(__name__)


class DynamicLogListener(logging_listener.DynamicLoggingListener):
    """This is used to attach to taskflow engines while they are running.

    It provides a bunch of useful features that expose the actions happening
    inside a taskflow engine, which can be useful for developers for debugging,
    for operations folks for monitoring and tracking of the resource actions
    and more...
    """

    #: Exception is an excepted case, don't include traceback in log if fails.
    _NO_TRACE_EXCEPTIONS = (exception.InvalidInput)

    def __init__(self, engine,
                 task_listen_for=base.DEFAULT_LISTEN_FOR,
                 flow_listen_for=base.DEFAULT_LISTEN_FOR,
                 retry_listen_for=base.DEFAULT_LISTEN_FOR,
                 logger=LOG):
        super(DynamicLogListener, self).__init__(
            engine,
            task_listen_for=task_listen_for,
            flow_listen_for=flow_listen_for,
            retry_listen_for=retry_listen_for,
            log=logger)

    def _format_failure(self, fail):
        if fail.check(*self._NO_TRACE_EXCEPTIONS) is not None:
            exc_info = None
            exc_details = '%s%s' % (os.linesep, fail.pformat(traceback=False))
            return (exc_info, exc_details)
        else:
            return super(DynamicLogListener, self)._format_failure(fail)


class CreateResourceTask(task.Task):
    """Create resource and store to db."""

    def execute(self, context, resource, **kwargs):
        user = user_mod.User.load(context, user_id=resource.user_id)
        pid = user.policy_id
        try:
            if pid:
                policy = policy_mod.Policy.load(context, policy_id=pid)
            else:
                policy = policy_mod.Policy.load_default(context)
        except exception.PolicyNotFound as e:
            LOG.error("Error when find policy: %s", e)
        if policy is not None:
            rule = policy.find_rule(context, resource.resource_type)

            # Update resource with rule_id and rate
            resource.rule_id = rule.id
            resource.rate = utils.make_decimal(rule.get_price(resource))
        resource.store(context)

    def revert(self, context, resource, result, **kwargs):
        if isinstance(result, ft.Failure):
            LOG.error("Error when creating resource: %s",
                      resource.to_dict())
            return

        resource.delete(context, soft_delete=False)


class UpdateResourceTask(task.Task):
    """Update resource."""

    def execute(self, context, resource, values, resource_bak, **kwargs):
        old_rate = resource.rate
        resource.properties = values.get('properties')
        rule = plugin_base.Rule.load(context, rule_id=resource.rule_id)
        resource.rate = utils.make_decimal(rule.get_price(resource))
        resource.delta_rate = resource.rate - old_rate
        resource.store(context)

    def revert(self, context, resource, resource_bak, result, **kwargs):
        if isinstance(result, ft.Failure):
            LOG.error("Error when updating resource: %s", resource.id)
            return

        # restore resource
        res = plugin_base.Resource.from_dict(resource_bak)
        res.store(context)


class DeleteResourceTask(task.Task):
    """Delete resource from db."""

    def execute(self, context, resource, **kwargs):
        resource.delete(context)

    def revert(self, context, resource, result, **kwargs):
        if isinstance(result, ft.Failure):
            LOG.error("Error when deleting resource: %s", resource.id)
            return

        resource.deleted_at = None
        resource.store(context)


class CreateConsumptionTask(task.Task):
    """Generate consumption record and store to db."""

    def execute(self, context, resource, *args, **kwargs):
        consumption = resource.consumption
        if consumption is not None:
            consumption.store(context)

    def revert(self, context, resource, result, *args, **kwargs):
        if isinstance(result, ft.Failure):
            LOG.error("Error when storing consumption of resource: %s",
                      resource.id)
            return

        consumption = resource.consumption
        if consumption is not None:
            consumption.delete(context)


class LoadUserTask(task.Task):
    """Load user from db."""

    default_provides = set(['user_bak', 'user_obj'])

    def execute(self, context, user_id, **kwargs):
        user_obj = user_mod.User.load(context, user_id=user_id)
        return {
            'user_bak': user_obj.to_dict(),
            'user_obj': user_obj,
        }


class SettleAccountTask(task.Task):
    def execute(self, context, user_obj, user_bak, task, **kwargs):
        user_obj.settle_account(context, task=task)

    def revert(self, context, user_bak, result, **kwargs):
        if isinstance(result, ft.Failure):
            LOG.error("Error when settling account for user: %s",
                      user_bak.get('id'))
            return

        # Restore user
        user = user_mod.User.from_dict(user_bak)
        user.store(context)


class UpdateUserRateTask(task.Task):
    """Update user's rate ."""

    def execute(self, context, user_obj, user_bak, resource, *args, **kwargs):
        user_obj.update_rate(context, resource.delta_rate,
                             timestamp=resource.last_bill)

    def revert(self, context, user_obj, user_bak, resource, result,
               *args, **kwargs):
        if isinstance(result, ft.Failure):
            LOG.error("Error when updating user: %s", user_obj.id)
            return

        # Restore user
        user = user_mod.User.from_dict(user_bak)
        user.store(context)


class UpdateUserJobsTask(task.Task):
    """Update user jobs."""

    def execute(self, user_obj, **kwargs):
        res = bilean_scheduler.notify(bilean_scheduler.UPDATE_JOBS,
                                      user=user_obj.to_dict())
        if not res:
            LOG.error("Error when updating user jobs: %s", user_obj.id)
            raise


def get_settle_account_flow(context, user_id, task=None):
    """Constructs and returns settle account task flow."""

    flow_name = user_id + '_settle_account'
    flow = linear_flow.Flow(flow_name)
    kwargs = {
        'context': context,
        'user_id': user_id,
        'task': task,
    }
    flow.add(LoadUserTask(),
             SettleAccountTask())
    if task != 'freeze':
        flow.add(UpdateUserJobsTask())
    return taskflow.engines.load(flow, store=kwargs)


def get_create_resource_flow(context, user_id, resource):
    """Constructs and returns user task flow.

    :param context: The request context.
    :param user_id: The ID of user.
    :param resource: Object resource to create.
    """

    flow_name = user_id + '_create_resource'
    flow = linear_flow.Flow(flow_name)
    kwargs = {
        'context': context,
        'user_id': user_id,
        'resource': resource,
    }
    flow.add(CreateResourceTask(),
             LoadUserTask(),
             UpdateUserRateTask(),
             UpdateUserJobsTask())
    return taskflow.engines.load(flow, store=kwargs)


def get_delete_resource_flow(context, user_id, resource):
    """Constructs and returns user task flow.

    :param context: The request context.
    :param user_id: The ID of user.
    :param resource: Object resource to delete.
    """

    flow_name = user_id + '_delete_resource'
    flow = linear_flow.Flow(flow_name)
    kwargs = {
        'context': context,
        'user_id': user_id,
        'resource': resource,
    }
    flow.add(DeleteResourceTask(),
             CreateConsumptionTask(),
             LoadUserTask(),
             UpdateUserRateTask(),
             UpdateUserJobsTask())
    return taskflow.engines.load(flow, store=kwargs)


def get_update_resource_flow(context, user_id, resource, values):
    """Constructs and returns user task flow.

    :param context: The request context.
    :param user_id: The ID of user.
    :param resource: Object resource to update.
    :param values: The values to update.
    """

    flow_name = user_id + '_update_resource'
    flow = linear_flow.Flow(flow_name)
    kwargs = {
        'context': context,
        'user_id': user_id,
        'resource': resource,
        'resource_bak': resource.to_dict(),
        'values': values,
    }
    flow.add(UpdateResourceTask(),
             CreateConsumptionTask(),
             LoadUserTask(),
             UpdateUserRateTask(),
             UpdateUserJobsTask())
    return taskflow.engines.load(flow, store=kwargs)
