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

from sqlalchemy.orm.session import Session

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import params
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


def user_get(context, user_id, show_deleted=False, tenant_safe=True):
    query = model_query(context, models.User)
    user = query.get(user_id)

    deleted_ok = show_deleted or context.show_deleted
    if user is None or user.deleted_at is not None and not deleted_ok:
        return None

    if tenant_safe and context.tenant_id != user.user_id:
        return None

    return user


def user_update(context, user_id, values):
    user = user_get(context, user_id)

    if not user:
        raise exception.NotFound(_('Attempt to update a user with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': user_id,
                                     'msg': 'that does not exist'})

    user.update(values)
    user.save(_session(context))


def user_create(context, values):
    user_ref = models.User()
    user_ref.update(values)
    user_ref.save(_session(context))
    return user_ref


def user_delete(context, user_id):
    session = _session(context)
    user = user_get(context, user_id)
    if not user:
        raise exception.NotFound(_('Attempt to delete a user with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': user_id,
                                     'msg': 'that does not exist'})
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
        params.USER_CREATED_AT: models.User.created_at.key,
        params.USER_UPDATED_AT: models.User.updated_at.key,
        params.USER_BALANCE: models.User.balance.key,
        params.USER_STATUS: models.User.status.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.User, filters)
    return _paginate_query(context, query, models.User,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['created_at']).all()


def rule_get(context, rule_id, show_deleted=False):
    query = model_query(context, models.Rule)
    rule = query.get(rule_id)

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
        params.RULE_NAME: models.Rule.name.key,
        params.RULE_TYPE: models.Rule.type.key,
        params.RULE_CREATED_AT: models.Rule.created_at.key,
        params.RULE_UPDATED_AT: models.Rule.updated_at.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Rule, filters)
    return _paginate_query(context, query, models.Rule,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['created_at']).all()


def rule_create(context, values):
    rule_ref = models.Rule()
    rule_ref.update(values)
    rule_ref.save(_session(context))
    return rule_ref


def rule_update(context, rule_id, values):
    rule = rule_get(context, rule_id)

    if not rule:
        raise exception.NotFound(_('Attempt to update a rule with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': rule_id,
                                     'msg': 'that does not exist'})

    rule.update(values)
    rule.save(_session(context))


def rule_delete(context, rule_id):
    rule = rule_get(context, rule_id)

    if not rule:
        raise exception.NotFound(_('Attempt to delete a rule with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': rule_id,
                                     'msg': 'that does not exist'})
    session = Session.object_session(rule)
    rule.soft_delete(session=session)
    session.flush()


def resource_get(context, resource_id, show_deleted=False, tenant_safe=True):
    query = model_query(context, models.Resource)
    resource = query.get(resource_id)

    deleted_ok = show_deleted or context.show_deleted
    if resource is None or resource.deleted_at is not None and not deleted_ok:
        return None

    if tenant_safe and context.tenant_id != resource.user_id:
        return None

    return resource


def resource_get_all(context, user_id=None, show_deleted=False,
                     limit=None, marker=None, sort_keys=None, sort_dir=None,
                     filters=None, tenant_safe=True):
    query = soft_delete_aware_query(context, models.Resource,
                                    show_deleted=show_deleted)

    if tenant_safe:
        query = query.filter_by(user_id=context.tenant_id)

    elif user_id:
        query = query.filter_by(user_id=user_id)

    if filters is None:
        filters = {}

    sort_key_map = {
        params.RES_CREATED_AT: models.Resource.created_at.key,
        params.RES_UPDATED_AT: models.Resource.updated_at.key,
        params.RES_RESOURCE_TYPE: models.Resource.resource_type.key,
        params.RES_USER_ID: models.Resource.user_id.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Resource, filters)
    return _paginate_query(context, query, models.Node,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['created_at']).all()


def resource_create(context, values):
    resource_ref = models.Resource()
    resource_ref.update(values)
    resource_ref.save(_session(context))
    return resource_ref


def resource_update(context, resource_id, values):
    resource = resource_get(context, resource_id)

    if not resource:
        raise exception.NotFound(_('Attempt to update a resource with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': resource_id,
                                     'msg': 'that does not exist'})

    resource.update(values)
    resource.save(_session(context))
    return resource


def resource_delete(context, resource_id, soft_delete=True):
    resource = resource_get(context, resource_id)

    if not resource:
        raise exception.NotFound(_('Attempt to delete a resource with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': resource_id,
                                     'msg': 'that does not exist'})
    session = Session.object_session(resource)
    if soft_delete:
        resource.soft_delete(session=session)
    else:
        session.delete(resource)
    session.flush()


def event_get(context, event_id, tenant_safe=True):
    query = model_query(context, models.Event)
    event = query.get(event_id)

    if event is None:
        return None

    if tenant_safe and context.tenant_id != event.user_id:
        return None

    return event


def event_get_all(context, user_id=None, show_deleted=False,
                  filters=None, limit=None, marker=None, sort_keys=None,
                  sort_dir=None, tenant_safe=True, start_time=None,
                  end_time=None):
    query = soft_delete_aware_query(context, models.Event,
                                    show_deleted=show_deleted)

    if tenant_safe:
        query = query.filter_by(user_id=context.tenant_id)

    elif user_id:
        query = query.filter_by(user_id=user_id)

    if start_time:
        query = query.filter_by(models.Event.timestamp >= start_time)
    if end_time:
        query = query.filter_by(models.Event.timestamp <= end_time)

    if filters is None:
        filters = {}

    sort_key_map = {
        params.EVENT_ACTION: models.Event.action.key,
        params.EVENT_RESOURCE_TYPE: models.Event.resource_type.key,
        params.EVENT_TIMESTAMP: models.Event.timestamp.key,
        params.EVENT_USER_ID: models.Event.user_id.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Resource, filters)
    return _paginate_query(context, query, models.Node,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['timestamp']).all()


def event_create(context, values):
    event_ref = models.Event()
    event_ref.update(values)
    event_ref.save(_session(context))
    return event_ref


def job_create(context, values):
    job_ref = models.Job()
    job_ref.update(values)
    job_ref.save(_session(context))
    return job_ref


def job_get_all(context, engine_id=None):
    query = model_query(context, models.Job)
    if engine_id:
        query = query.filter_by(engine_id=engine_id)

    return query.all()


def job_delete(context, job_id):
    job = model_query(context, models.Job).get(job_id)

    if job is None:
        raise exception.NotFound(_('Attempt to delete a job with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': job_id,
                                     'msg': 'that does not exist'})
    session = Session.object_session(job)
    session.delete(job)
    session.flush()
