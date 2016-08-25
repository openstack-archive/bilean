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

'''Implementation of SQLAlchemy backend.'''
import six
import sys

from oslo_config import cfg
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils
from oslo_log import log as logging
from oslo_utils import timeutils

from sqlalchemy.orm.session import Session

from bilean.common import consts
from bilean.common import exception
from bilean.common.i18n import _
from bilean.common.i18n import _LW
from bilean.db.sqlalchemy import filters as db_filters
from bilean.db.sqlalchemy import migration
from bilean.db.sqlalchemy import models

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

_facade = None


def get_facade():
    global _facade

    if not _facade:
        _facade = db_session.EngineFacade.from_config(CONF)
    return _facade

get_engine = lambda: get_facade().get_engine()
get_session = lambda: get_facade().get_session()


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def model_query(context, *args):
    session = _session(context)
    query = session.query(*args)
    return query


def _get_sort_keys(sort_keys, mapping):
    '''Returns an array containing only whitelisted keys

    :param sort_keys: an array of strings
    :param mapping: a mapping from keys to DB column names
    :returns: filtered list of sort keys
    '''
    if isinstance(sort_keys, six.string_types):
        sort_keys = [sort_keys]
    return [mapping[key] for key in sort_keys or [] if key in mapping]


def _paginate_query(context, query, model, limit=None, marker=None,
                    sort_keys=None, sort_dir=None, default_sort_keys=None):
    if not sort_keys:
        sort_keys = default_sort_keys or []
        if not sort_dir:
            sort_dir = 'asc'

    model_marker = None
    if marker:
        model_marker = model_query(context, model).get(marker)
    try:
        query = utils.paginate_query(query, model, limit, sort_keys,
                                     model_marker, sort_dir)
    except utils.InvalidSortKey:
        raise exception.InvalidParameter(name='sort_keys', value=sort_keys)
    return query


def soft_delete_aware_query(context, *args, **kwargs):
    """Query helper that accounts for context's `show_deleted` field.

    :param show_deleted: if True, overrides context's show_deleted field.
    """

    query = model_query(context, *args)
    show_deleted = kwargs.get('show_deleted') or context.show_deleted

    if not show_deleted:
        query = query.filter_by(deleted_at=None)

    return query


def _session(context):
    return (context and context.session) or get_session()


def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return migration.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return migration.db_version(engine)


# users
def user_get(context, user_id, show_deleted=False, project_safe=True):
    query = model_query(context, models.User)
    user = query.get(user_id)

    deleted_ok = show_deleted or context.show_deleted
    if user is None or user.deleted_at is not None and not deleted_ok:
        return None

    if project_safe and context.project != user.id:
        return None

    return user


def user_update(context, user_id, values):
    user = user_get(context, user_id, project_safe=False)

    if user is None:
        raise exception.UserNotFound(user=user_id)

    user.update(values)
    user.save(_session(context))
    return user


def user_create(context, values):
    user_ref = models.User()
    user_ref.update(values)
    user_ref.save(_session(context))
    return user_ref


def user_delete(context, user_id):
    session = _session(context)
    user = user_get(context, user_id)
    if user is None:
        return

    # Delete all related resource records
    for resource in user.resources:
        session.delete(resource)

    # Delete all related event records
    for event in user.events:
        session.delete(event)

    user.soft_delete(session=session)
    session.flush()


def user_get_all(context, show_deleted=False, limit=None,
                 marker=None, sort_keys=None, sort_dir=None,
                 filters=None):
    query = soft_delete_aware_query(context, models.User,
                                    show_deleted=show_deleted)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.USER_CREATED_AT: models.User.created_at.key,
        consts.USER_UPDATED_AT: models.User.updated_at.key,
        consts.USER_NAME: models.User.name.key,
        consts.USER_BALANCE: models.User.balance.key,
        consts.USER_STATUS: models.User.status.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.User, filters)
    return _paginate_query(context, query, models.User,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['id']).all()


# rules
def rule_get(context, rule_id, show_deleted=False):
    query = model_query(context, models.Rule)
    rule = query.filter_by(id=rule_id).first()

    deleted_ok = show_deleted or context.show_deleted
    if rule is None or rule.deleted_at is not None and not deleted_ok:
        return None

    return rule


def rule_get_all(context, show_deleted=False, limit=None,
                 marker=None, sort_keys=None, sort_dir=None,
                 filters=None):
    query = soft_delete_aware_query(context, models.Rule,
                                    show_deleted=show_deleted)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.RULE_NAME: models.Rule.name.key,
        consts.RULE_TYPE: models.Rule.type.key,
        consts.RULE_CREATED_AT: models.Rule.created_at.key,
        consts.RULE_UPDATED_AT: models.Rule.updated_at.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Rule, filters)
    return _paginate_query(context, query, models.Rule,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['id']).all()


def rule_create(context, values):
    rule_ref = models.Rule()
    rule_ref.update(values)
    rule_ref.save(_session(context))
    return rule_ref


def rule_update(context, rule_id, values):
    rule = rule_get(context, rule_id)

    if rule is None:
        raise exception.RuleNotFound(rule=rule_id)

    rule.update(values)
    rule.save(_session(context))


def rule_delete(context, rule_id):
    rule = rule_get(context, rule_id)

    if rule is None:
        return

    session = Session.object_session(rule)
    rule.soft_delete(session=session)
    session.flush()


# resources
def resource_get(context, resource_id, show_deleted=False, project_safe=True):
    query = model_query(context, models.Resource)
    resource = query.get(resource_id)

    deleted_ok = show_deleted or context.show_deleted
    if resource is None or resource.deleted_at is not None and not deleted_ok:
        return None

    if project_safe and context.project != resource.user_id:
        return None

    return resource


def resource_get_all(context, user_id=None, show_deleted=False,
                     limit=None, marker=None, sort_keys=None, sort_dir=None,
                     filters=None, project_safe=True):
    query = soft_delete_aware_query(context, models.Resource,
                                    show_deleted=show_deleted)

    if project_safe:
        query = query.filter_by(user_id=context.project)

    elif user_id:
        query = query.filter_by(user_id=user_id)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.RES_CREATED_AT: models.Resource.created_at.key,
        consts.RES_UPDATED_AT: models.Resource.updated_at.key,
        consts.RES_RESOURCE_TYPE: models.Resource.resource_type.key,
        consts.RES_USER_ID: models.Resource.user_id.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Resource, filters)
    return _paginate_query(context, query, models.Resource,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['id']).all()


def resource_create(context, values):
    resource_ref = models.Resource()
    resource_ref.update(values)
    resource_ref.save(_session(context))
    return resource_ref


def resource_update(context, resource_id, values):
    project_safe = True
    if context.is_admin:
        project_safe = False
    resource = resource_get(context, resource_id, show_deleted=True,
                            project_safe=project_safe)

    if resource is None:
        raise exception.ResourceNotFound(resource=resource_id)

    resource.update(values)
    resource.save(_session(context))
    return resource


def resource_delete(context, resource_id, soft_delete=True):
    resource = resource_get(context, resource_id, project_safe=False)

    if resource is None:
        return

    session = Session.object_session(resource)
    if soft_delete:
        resource.soft_delete(session=session)
    else:
        session.delete(resource)
    session.flush()


# events
def event_get(context, event_id, project_safe=True):
    query = model_query(context, models.Event)
    event = query.get(event_id)

    if event is None:
        return None

    if project_safe and context.project != event.user_id:
        return None

    return event


def event_get_all(context, limit=None, marker=None, sort_keys=None,
                  sort_dir=None, filters=None, project_safe=True):
    query = model_query(context, models.Event)

    if context.is_admin:
        project_safe = False
    if project_safe:
        query = query.filter_by(user_id=context.project)
    if filters is None:
        filters = {}

    sort_key_map = {
        consts.EVENT_LEVEL: models.Event.level.key,
        consts.EVENT_TIMESTAMP: models.Event.timestamp.key,
        consts.EVENT_USER_ID: models.Event.user_id.key,
        consts.EVENT_STATUS: models.Event.status.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Event, filters)
    return _paginate_query(context, query, models.Event,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['id']).all()


def event_create(context, values):
    event_ref = models.Event()
    event_ref.update(values)
    event_ref.save(_session(context))
    return event_ref


# jobs
def job_create(context, values):
    job_ref = models.Job()
    job_ref.update(values)
    job_ref.save(_session(context))
    return job_ref


def job_get_all(context, scheduler_id=None):
    query = model_query(context, models.Job)
    if scheduler_id:
        query = query.filter_by(scheduler_id=scheduler_id)

    return query.all()


def job_delete(context, job_id):
    job = model_query(context, models.Job).get(job_id)

    if job is None:
        return

    session = Session.object_session(job)
    session.delete(job)
    session.flush()


# policies
def policy_get(context, policy_id, show_deleted=False):
    query = model_query(context, models.Policy)
    policy = query.get(policy_id)

    deleted_ok = show_deleted or context.show_deleted
    if policy is None or policy.deleted_at is not None and not deleted_ok:
        return None

    return policy


def policy_get_all(context, limit=None, marker=None,
                   sort_keys=None, sort_dir=None,
                   filters=None, show_deleted=False):
    query = soft_delete_aware_query(context, models.Policy,
                                    show_deleted=show_deleted)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.POLICY_NAME: models.Policy.name.key,
        consts.POLICY_CREATED_AT: models.Policy.created_at.key,
        consts.POLICY_UPDATED_AT: models.Policy.updated_at.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Policy, filters)
    return _paginate_query(context, query, models.Policy,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['id']).all()


def policy_create(context, values):
    policy_ref = models.Policy()
    policy_ref.update(values)
    policy_ref.save(_session(context))
    return policy_ref


def policy_update(context, policy_id, values):
    policy = policy_get(context, policy_id)

    if policy is None:
        raise exception.PolicyNotFound(policy=policy_id)

    policy.update(values)
    policy.save(_session(context))


def policy_delete(context, policy_id):
    policy = policy_get(context, policy_id)

    if policy is None:
        return

    session = Session.object_session(policy)
    policy.soft_delete(session=session)
    session.flush()


# locks
def user_lock_acquire(user_id, action_id):
    session = get_session()
    session.begin()

    lock = session.query(models.UserLock).get(user_id)
    if lock is None:
        lock = models.UserLock(user_id=user_id, action_id=action_id)
        session.add(lock)

    session.commit()
    return lock.action_id


def user_lock_release(user_id, action_id):
    session = get_session()
    session.begin()

    success = False
    lock = session.query(models.UserLock).get(user_id)
    if lock is not None and lock.action_id == action_id:
        session.delete(lock)
        success = True

    session.commit()
    return success


def user_lock_steal(user_id, action_id):
    session = get_session()
    session.begin()
    lock = session.query(models.UserLock).get(user_id)
    if lock is not None:
        lock.action_id = action_id
        lock.save(session)
    else:
        lock = models.UserLock(user_id=user_id, action_id=action_id)
        session.add(lock)
    session.commit()
    return lock.action_id


# actions
def action_create(context, values):
    action = models.Action()
    action.update(values)
    action.save(_session(context))
    return action


def action_update(context, action_id, values):
    session = get_session()
    action = session.query(models.Action).get(action_id)
    if not action:
        raise exception.ActionNotFound(action=action_id)

    action.update(values)
    action.save(session)


def action_get(context, action_id, project_safe=True, refresh=False):
    session = _session(context)
    action = session.query(models.Action).get(action_id)
    if action is None:
        return None

    if not context.is_admin and project_safe:
        if action.project != context.project:
            return None

    session.refresh(action)
    return action


def action_get_all_by_owner(context, owner_id):
    query = model_query(context, models.Action).\
        filter_by(owner=owner_id)
    return query.all()


def action_get_all(context, filters=None, limit=None, marker=None,
                   sort_keys=None, sort_dir=None):

    query = model_query(context, models.Action)

    if filters:
        query = db_filters.exact_filter(query, models.Action, filters)

    sort_key_map = {
        consts.ACTION_CREATED_AT: models.Action.created_at.key,
        consts.ACTION_UPDATED_AT: models.Action.updated_at.key,
        consts.ACTION_NAME: models.Action.name.key,
        consts.ACTION_STATUS: models.Action.status.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Action, filters)
    return _paginate_query(context, query, models.Action,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['id']).all()


def action_check_status(context, action_id, timestamp):
    session = _session(context)
    q = session.query(models.ActionDependency)
    count = q.filter_by(dependent=action_id).count()
    if count > 0:
        return consts.ACTION_WAITING

    action = session.query(models.Action).get(action_id)
    if action.status == consts.ACTION_WAITING:
        session.begin()
        action.status = consts.ACTION_READY
        action.status_reason = _('All depended actions completed.')
        action.end_time = timestamp
        action.save(session)
        session.commit()

    return action.status


def dependency_get_depended(context, action_id):
    session = _session(context)
    q = session.query(models.ActionDependency).filter_by(dependent=action_id)
    return [d.depended for d in q.all()]


def dependency_get_dependents(context, action_id):
    session = _session(context)
    q = session.query(models.ActionDependency).filter_by(depended=action_id)
    return [d.dependent for d in q.all()]


def dependency_add(context, depended, dependent):
    if isinstance(depended, list) and isinstance(dependent, list):
        raise exception.NotSupport(
            _('Multiple dependencies between lists not support'))

    session = _session(context)

    if isinstance(depended, list):
        session.begin()
        for d in depended:
            r = models.ActionDependency(depended=d, dependent=dependent)
            session.add(r)

        query = session.query(models.Action).filter_by(id=dependent)
        query.update({'status': consts.ACTION_WAITING,
                      'status_reason': _('Waiting for depended actions.')},
                     synchronize_session=False)
        session.commit()
        return

    # Only dependent can be a list now, convert it to a list if it
    # is not a list
    if not isinstance(dependent, list):  # e.g. B,C,D depend on A
        dependents = [dependent]
    else:
        dependents = dependent

    session.begin()
    for d in dependents:
        r = models.ActionDependency(depended=depended, dependent=d)
        session.add(r)

    q = session.query(models.Action).filter(models.Action.id.in_(dependents))
    q.update({'status': consts.ACTION_WAITING,
              'status_reason': _('Waiting for depended actions.')},
             synchronize_session=False)
    session.commit()


def action_mark_succeeded(context, action_id, timestamp):
    session = _session(context)
    session.begin()

    query = session.query(models.Action).filter_by(id=action_id)
    values = {
        'owner': None,
        'status': consts.ACTION_SUCCEEDED,
        'status_reason': _('Action completed successfully.'),
        'end_time': timestamp,
    }
    query.update(values, synchronize_session=False)

    subquery = session.query(models.ActionDependency).filter_by(
        depended=action_id)
    subquery.delete(synchronize_session=False)
    session.commit()


def _mark_failed(session, action_id, timestamp, reason=None):
    # mark myself as failed
    query = session.query(models.Action).filter_by(id=action_id)
    values = {
        'owner': None,
        'status': consts.ACTION_FAILED,
        'status_reason': (six.text_type(reason) if reason else
                          _('Action execution failed')),
        'end_time': timestamp,
    }
    query.update(values, synchronize_session=False)

    query = session.query(models.ActionDependency)
    query = query.filter_by(depended=action_id)
    dependents = [d.dependent for d in query.all()]
    query.delete(synchronize_session=False)

    for d in dependents:
        _mark_failed(session, d, timestamp)


def action_mark_failed(context, action_id, timestamp, reason=None):
    session = _session(context)
    session.begin()
    _mark_failed(session, action_id, timestamp, reason)
    session.commit()


def _mark_cancelled(session, action_id, timestamp, reason=None):
    query = session.query(models.Action).filter_by(id=action_id)
    values = {
        'owner': None,
        'status': consts.ACTION_CANCELLED,
        'status_reason': (six.text_type(reason) if reason else
                          _('Action execution failed')),
        'end_time': timestamp,
    }
    query.update(values, synchronize_session=False)

    query = session.query(models.ActionDependency)
    query = query.filter_by(depended=action_id)
    dependents = [d.dependent for d in query.all()]
    query.delete(synchronize_session=False)

    for d in dependents:
        _mark_cancelled(session, d, timestamp)


def action_mark_cancelled(context, action_id, timestamp, reason=None):
    session = _session(context)
    session.begin()
    _mark_cancelled(session, action_id, timestamp, reason)
    session.commit()


def action_acquire(context, action_id, owner, timestamp):
    session = _session(context)
    with session.begin():
        action = session.query(models.Action).get(action_id)
        if not action:
            return None

        if action.owner and action.owner != owner:
            return None

        if action.status != consts.ACTION_READY:
            msg = _LW('The action is not in an executable status: '
                    '%s') % action.status
            LOG.warn(msg)
            return None
        action.owner = owner
        action.start_time = timestamp
        action.status = consts.ACTION_RUNNING
        action.status_reason = _('The action is being processed.')

        return action


def action_acquire_first_ready(context, owner, timestamp):
    session = _session(context)

    with session.begin():
        action = session.query(models.Action).\
            filter_by(status=consts.ACTION_READY).\
            filter_by(owner=None).first()

        if action:
            action.owner = owner
            action.start_time = timestamp
            action.status = consts.ACTION_RUNNING
            action.status_reason = _('The action is being processed.')

            return action


def action_abandon(context, action_id):
    '''Abandon an action for other workers to execute again.

    This API is always called with the action locked by the current
    worker. There is no chance the action is gone or stolen by others.
    '''

    query = model_query(context, models.Action)
    action = query.get(action_id)

    action.owner = None
    action.start_time = None
    action.status = consts.ACTION_READY
    action.status_reason = _('The action was abandoned.')
    action.save(query.session)
    return action


def action_lock_check(context, action_id, owner=None):
    action = model_query(context, models.Action).get(action_id)
    if not action:
        raise exception.ActionNotFound(action=action_id)

    if owner:
        return owner if owner == action.owner else action.owner
    else:
        return action.owner if action.owner else None


def action_signal(context, action_id, value):
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        return

    action.control = value
    action.save(query.session)


def action_signal_query(context, action_id):
    action = model_query(context, models.Action).get(action_id)
    if not action:
        return None

    return action.control


def action_delete(context, action_id, force=False):
    session = _session(context)
    action = session.query(models.Action).get(action_id)
    if not action:
        return
    if ((action.status == 'WAITING') or (action.status == 'RUNNING') or
            (action.status == 'SUSPENDED')):

        raise exception.ResourceBusyError(resource_type='action',
                                          resource_id=action_id)
    session.begin()
    session.delete(action)
    session.commit()
    session.flush()


# services
def service_create(context, host, binary, topic=None):
    time_now = timeutils.utcnow()
    svc = models.Service(host=host, binary=binary,
                         topic=topic, created_at=time_now,
                         updated_at=time_now)
    svc.save(_session(context))
    return svc


def service_update(context, service_id, values=None):

    service = service_get(context, service_id)
    if not service:
        return

    if values is None:
        values = {}

    values.update({'updated_at': timeutils.utcnow()})
    service.update(values)
    service.save(_session(context))
    return service


def service_delete(context, service_id):
    session = _session(context)
    session.query(models.Service).filter_by(
        id=service_id).delete(synchronize_session='fetch')


def service_get(context, service_id):
    return model_query(context, models.Service).get(service_id)


def service_get_by_host_and_binary(context, host, binary):
    query = model_query(context, models.Service)
    return query.filter_by(host=host).filter_by(binary=binary).first()


def service_get_all(context):
    return model_query(context, models.Service).all()


# consumptions
def consumption_get(context, consumption_id, project_safe=True):
    query = model_query(context, models.Consumption)
    consumption = query.get(consumption_id)

    if consumption is None:
        return None

    if project_safe and context.project != consumption.user_id:
        return None

    return consumption


def consumption_get_all(context, user_id=None, limit=None, marker=None,
                        sort_keys=None, sort_dir=None, filters=None,
                        project_safe=True):
    query = model_query(context, models.Consumption)

    if context.is_admin:
        project_safe = False
    if project_safe:
        query = query.filter_by(user_id=context.project)
    elif user_id:
        query = query.filter_by(user_id=user_id)
    if filters is None:
        filters = {}

    sort_key_map = {
        consts.CONSUMPTION_USER_ID: models.Consumption.user_id.key,
        consts.CONSUMPTION_RESOURCE_TYPE: models.Consumption.resource_type.key,
        consts.CONSUMPTION_START_TIME: models.Consumption.start_time.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Consumption, filters)
    return _paginate_query(context, query, models.Consumption,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['id']).all()


def consumption_create(context, values):
    consumption_ref = models.Consumption()
    consumption_ref.update(values)
    consumption_ref.save(_session(context))
    return consumption_ref


def consumption_delete(context, consumption_id):
    session = _session(context)
    session.query(models.Consumption).filter_by(
        id=consumption_id).delete(synchronize_session='fetch')


# recharges
def recharge_create(context, values):
    recharge_ref = models.Recharge()
    recharge_ref.update(values)
    recharge_ref.save(_session(context))
    return recharge_ref


def recharge_get(context, recharge_id, project_safe=True):
    query = model_query(context, models.Recharge)
    recharge = query.get(recharge_id)

    if recharge is None:
        return None

    if project_safe and context.project != recharge.user_id:
        return None

    return recharge


def recharge_get_all(context, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, project_safe=True):
    query = model_query(context, models.Recharge)

    if context.is_admin:
        project_safe = False
    if project_safe:
        query = query.filter_by(user_id=context.project)
    if filters is None:
        filters = {}

    sort_key_map = {
        consts.RECHARGE_USER_ID: models.Recharge.user_id.key,
        consts.RECHARGE_TYPE: models.Recharge.type.key,
        consts.RECHARGE_TIMESTAMP: models.Recharge.timestamp.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Recharge, filters)
    return _paginate_query(context, query, models.Recharge,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['id']).all()
