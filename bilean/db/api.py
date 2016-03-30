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


from oslo_config import cfg
from oslo_db import api

CONF = cfg.CONF


_BACKEND_MAPPING = {'sqlalchemy': 'bilean.db.sqlalchemy.api'}

IMPL = api.DBAPI.from_config(CONF, backend_mapping=_BACKEND_MAPPING)


def get_engine():
    return IMPL.get_engine()


def get_session():
    return IMPL.get_session()


def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return IMPL.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return IMPL.db_version(engine)


# users
def user_get(context, user_id, show_deleted=False, project_safe=True):
    return IMPL.user_get(context, user_id,
                         show_deleted=show_deleted,
                         project_safe=project_safe)


def user_update(context, user_id, values):
    return IMPL.user_update(context, user_id, values)


def user_create(context, values):
    return IMPL.user_create(context, values)


def user_delete(context, user_id):
    return IMPL.user_delete(context, user_id)


def user_get_all(context, show_deleted=False, limit=None,
                 marker=None, sort_keys=None, sort_dir=None,
                 filters=None):
    return IMPL.user_get_all(context, show_deleted=show_deleted,
                             limit=limit, marker=marker,
                             sort_keys=sort_keys, sort_dir=sort_dir,
                             filters=filters)


# rules
def rule_get(context, rule_id, show_deleted=False):
    return IMPL.rule_get(context, rule_id, show_deleted=False)


def rule_get_all(context, show_deleted=False, limit=None,
                 marker=None, sort_keys=None, sort_dir=None,
                 filters=None):
    return IMPL.rule_get_all(context, show_deleted=show_deleted,
                             limit=limit, marker=marker,
                             sort_keys=sort_keys, sort_dir=sort_dir,
                             filters=filters)


def rule_create(context, values):
    return IMPL.rule_create(context, values)


def rule_update(context, rule_id, values):
    return IMPL.rule_update(context, rule_id, values)


def rule_delete(context, rule_id):
    return IMPL.rule_delete(context, rule_id)


# resources
def resource_get(context, resource_id, show_deleted=False, project_safe=True):
    return IMPL.resource_get(context, resource_id,
                             show_deleted=show_deleted,
                             project_safe=project_safe)


def resource_get_all(context, user_id=None, show_deleted=False,
                     limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, project_safe=True):
    return IMPL.resource_get_all(context, user_id=user_id,
                                 show_deleted=show_deleted,
                                 limit=limit, marker=marker,
                                 sort_keys=sort_keys, sort_dir=sort_dir,
                                 filters=filters, project_safe=project_safe)


def resource_create(context, values):
    return IMPL.resource_create(context, values)


def resource_update(context, resource_id, values):
    return IMPL.resource_update(context, resource_id, values)


def resource_delete(context, resource_id, soft_delete=True):
    IMPL.resource_delete(context, resource_id, soft_delete=soft_delete)


# events
def event_get(context, event_id, project_safe=True):
    return IMPL.event_get(context, event_id, project_safe=project_safe)


def event_get_all(context, user_id=None, show_deleted=False,
                  filters=None, limit=None, marker=None,
                  sort_keys=None, sort_dir=None, project_safe=True,
                  start_time=None, end_time=None):
    return IMPL.event_get_all(context, user_id=user_id,
                              show_deleted=show_deleted,
                              filters=filters, limit=limit,
                              marker=marker, sort_keys=sort_keys,
                              sort_dir=sort_dir, project_safe=project_safe,
                              start_time=start_time, end_time=end_time)


def event_create(context, values):
    return IMPL.event_create(context, values)


def event_delete(context, event_id):
    return IMPL.event_delete(context, event_id)


# jobs
def job_create(context, values):
    return IMPL.job_create(context, values)


def job_get_all(context, scheduler_id=None):
    return IMPL.job_get_all(context, scheduler_id=scheduler_id)


def job_delete(context, job_id):
    return IMPL.job_delete(context, job_id)


# policies
def policy_get(context, policy_id, show_deleted=False):
    return IMPL.policy_get(context, policy_id, show_deleted=False)


def policy_get_all(context, limit=None, marker=None, sort_keys=None,
                   sort_dir=None, filters=None, show_deleted=False):
    return IMPL.policy_get_all(context, limit=limit, marker=marker,
                               sort_keys=sort_keys, sort_dir=sort_dir,
                               filters=filters, show_deleted=show_deleted)


def policy_create(context, values):
    return IMPL.policy_create(context, values)


def policy_update(context, policy_id, values):
    return IMPL.policy_update(context, policy_id, values)


def policy_delete(context, policy_id):
    return IMPL.policy_delete(context, policy_id)


# locks
def user_lock_acquire(user_id, action_id):
    return IMPL.user_lock_acquire(user_id, action_id)


def user_lock_release(user_id, action_id):
    return IMPL.user_lock_release(user_id, action_id)


def user_lock_steal(user_id, action_id):
    return IMPL.user_lock_steal(user_id, action_id)


# actions
def action_create(context, values):
    return IMPL.action_create(context, values)


def action_update(context, action_id, values):
    return IMPL.action_update(context, action_id, values)


def action_get(context, action_id, project_safe=True, refresh=False):
    return IMPL.action_get(context, action_id, project_safe=project_safe,
                           refresh=refresh)


def action_get_all_by_owner(context, owner):
    return IMPL.action_get_all_by_owner(context, owner)


def action_get_all(context, filters=None, limit=None, marker=None, sort=None,
                   project_safe=True):
    return IMPL.action_get_all(context, filters=filters, sort=sort,
                               limit=limit, marker=marker,
                               project_safe=project_safe)


def action_check_status(context, action_id, timestamp):
    return IMPL.action_check_status(context, action_id, timestamp)


def dependency_add(context, depended, dependent):
    return IMPL.dependency_add(context, depended, dependent)


def dependency_get_depended(context, action_id):
    return IMPL.dependency_get_depended(context, action_id)


def dependency_get_dependents(context, action_id):
    return IMPL.dependency_get_dependents(context, action_id)


def action_mark_succeeded(context, action_id, timestamp):
    return IMPL.action_mark_succeeded(context, action_id, timestamp)


def action_mark_failed(context, action_id, timestamp, reason=None):
    return IMPL.action_mark_failed(context, action_id, timestamp, reason)


def action_mark_cancelled(context, action_id, timestamp):
    return IMPL.action_mark_cancelled(context, action_id, timestamp)


def action_acquire(context, action_id, owner, timestamp):
    return IMPL.action_acquire(context, action_id, owner, timestamp)


def action_acquire_first_ready(context, owner, timestamp):
    return IMPL.action_acquire_first_ready(context, owner, timestamp)


def action_abandon(context, action_id):
    return IMPL.action_abandon(context, action_id)


def action_lock_check(context, action_id, owner=None):
    '''Check whether an action has been locked(by a owner).'''
    return IMPL.action_lock_check(context, action_id, owner)


def action_signal(context, action_id, value):
    '''Send signal to an action via DB.'''
    return IMPL.action_signal(context, action_id, value)


def action_signal_query(context, action_id):
    '''Query signal status for the sepcified action.'''
    return IMPL.action_signal_query(context, action_id)


def action_delete(context, action_id, force=False):
    return IMPL.action_delete(context, action_id, force)


# services
def service_create(context, host, binary, topic=None):
    return IMPL.service_create(context, host, binary, topic=topic)


def service_update(context, service_id, values=None):
    return IMPL.service_update(context, service_id, values=values)


def service_delete(context, service_id):
    return IMPL.service_delete(context, service_id)


def service_get(context, service_id):
    return IMPL.service_get(context, service_id)


def service_get_by_host_and_binary(context, host, binary):
    return IMPL.service_get_by_host_and_binary(context, host, binary)


def service_get_all(context):
    return IMPL.service_get_all(context)
