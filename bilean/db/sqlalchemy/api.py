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
import sys

from oslo_config import cfg
from oslo_db.sqlalchemy import session as db_session
from oslo_log import log as logging

from sqlalchemy.orm.session import Session
from sqlalchemy.sql import func

from bilean.common import exception
from bilean.common.i18n import _
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


def user_get(context, user_id):
    result = model_query(context, models.User).get(user_id)

    if not result:
        raise exception.NotFound(_('User with id %s not found') % user_id)

    return result


def user_update(context, user_id, values):
    user = user_get(context, user_id)

    if not user:
        raise exception.NotFound(_('Attempt to update a user with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': user_id,
                                     'msg': 'that does not exist'})

    user.update(values)
    user.save(_session(context))
    return user_get(context, user_id)


def user_create(context, values):
    user_ref = models.User()
    user_ref.update(values)
    user_ref.save(_session(context))
    return user_ref


def user_delete(context, user_id):
    user = user_get(context, user_id)
    session = Session.object_session(user)
    session.delete(user)
    session.flush()


def user_get_all(context):
    results = model_query(context, models.User).all()

    if not results:
        return None

    return results


def rule_get(context, rule_id):
    result = model_query(context, models.Rule).get(rule_id)

    if not result:
        raise exception.NotFound(_('Rule with id %s not found') % rule_id)

    return result


def rule_get_all(context):
    return model_query(context, models.Rule).all()


def get_rule_by_filters(context, **filters):
    filter_keys = filters.keys()
    query = model_query(context, models.Rule)
    if "resource_type" in filter_keys:
        query = query.filter_by(resource_type=filters["resource_type"])
    if "size" in filter_keys:
        query = query.filter_by(size=filters["size"])
    return query.all()


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
    session = Session.object_session(rule)
    session.delete(rule)
    session.flush()


def resource_get(context, resource_id):
    result = model_query(context, models.Resource).get(resource_id)

    if not result:
        raise exception.NotFound(_('Resource with id %s not found') %
                                 resource_id)

    return result


def resource_get_by_physical_resource_id(context,
                                         physical_resource_id,
                                         resource_type):
    result = (model_query(context, models.Resource)
              .filter_by(resource_ref=physical_resource_id)
              .filter_by(resource_type=resource_type)
              .first())

    if not result:
        raise exception.NotFound(_('Resource with physical_resource_id: '
                                   '%(resource_id)s, resource_type: '
                                   '%(resource_type)s not found.') % {
                                       'resource_id': physical_resource_id,
                                       'resource_type': resource_type})

    return result


def resource_get_all(context, **filters):
    if filters.get('show_deleted') is None:
        filters['show_deleted'] = False
    query = soft_delete_aware_query(context, models.Resource, **filters)
    if "resource_type" in filters:
        query = query.filter_by(resource_type=filters["resource_type"])
    if "user_id" in filters:
        query = query.filter_by(user_id=filters["user_id"])
    return query.all()


def resource_get_by_user_id(context, user_id, show_deleted=False):
    query = soft_delete_aware_query(
        context, models.Resource, show_deleted=show_deleted
    ).filter_by(user_id=user_id).all()
    return query


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


def resource_update_by_resource(context, res):
    resource = resource_get_by_physical_resource_id(
        context, res['resource_ref'], res['resource_type'])

    if not resource:
        raise exception.NotFound(_('Attempt to update a resource: '
                                 '%(res)s %(msg)s') % {
                                     'res': res,
                                     'msg': 'that does not exist'})

    resource.update(res)
    resource.save(_session(context))
    return resource


def resource_delete(context, resource_id, soft_delete=True):
    resource = resource_get(context, resource_id)
    session = Session.object_session(resource)
    if soft_delete:
        resource.soft_delete(session=session)
    else:
        session.delete(resource)
    session.flush()


def resource_delete_by_physical_resource_id(context,
                                            physical_resource_id,
                                            resource_type,
                                            soft_delete=True):
    resource = resource_get_by_physical_resource_id(
        context, physical_resource_id, resource_type)
    session = Session.object_session(resource)
    if soft_delete:
        resource.soft_delete(session=session)
    else:
        session.delete(resource)
    session.flush()


def resource_delete_by_user_id(context, user_id):
    resource = resource_get_by_user_id(context, user_id)
    session = Session.object_session(resource)
    session.delete(resource)
    session.flush()


def event_get(context, event_id):
    result = model_query(context, models.Event).get(event_id)

    if not result:
        raise exception.NotFound(_('Event with id %s not found') % event_id)

    return result


def event_get_by_user_id(context, user_id):
    query = model_query(context, models.Event).filter_by(user_id=user_id)
    return query


def event_get_by_user_and_resource(context,
                                   user_id,
                                   resource_type,
                                   action=None):
    query = (model_query(context, models.Event)
             .filter_by(user_id=user_id)
             .filter_by(resource_type=resource_type)
             .filter_by(action=action).all())
    return query


def events_get_all_by_filters(context,
                              user_id=None,
                              resource_type=None,
                              start=None,
                              end=None,
                              action=None,
                              aggregate=None):
    if aggregate == 'sum':
        query_prefix = model_query(
            context, models.Event.resource_type, func.sum(models.Event.value)
        ).group_by(models.Event.resource_type)
    elif aggregate == 'avg':
        query_prefix = model_query(
            context, models.Event.resource_type, func.avg(models.Event.value)
        ).group_by(models.Event.resource_type)
    else:
        query_prefix = model_query(context, models.Event)
    if not context.is_admin:
        if context.tenant_id:
            query_prefix = query_prefix.filter_by(user_id=context.tenant_id)
    elif user_id:
        query_prefix = query_prefix.filter_by(user_id=user_id)
    if resource_type:
        query_prefix = query_prefix.filter_by(resource_type=resource_type)
    if action:
        query_prefix = query_prefix.filter_by(action=action)
    if start:
        query_prefix = query_prefix.filter(models.Event.created_at >= start)
    if end:
        query_prefix = query_prefix.filter(models.Event.created_at <= end)

    return query_prefix.all()


def event_create(context, values):
    event_ref = models.Event()
    event_ref.update(values)
    event_ref.save(_session(context))
    return event_ref


def event_delete(context, event_id):
    event = event_get(context, event_id)
    session = Session.object_session(event)
    session.delete(event)
    session.flush()


def event_delete_by_user_id(context, user_id):
    event = event_get(context, user_id)
    session = Session.object_session(event)
    session.delete(event)
    session.flush()


def job_create(context, values):
    job_ref = models.Job()
    job_ref.update(values)
    job_ref.save(_session(context))
    return job_ref


def job_get(context, job_id):
    result = model_query(context, models.Job).get(job_id)

    if not result:
        raise exception.NotFound(_('Job with id %s not found') % job_id)

    return result


def job_get_by_engine_id(context, engine_id):
    query = (model_query(context, models.Job)
             .filter_by(engine_id=engine_id).all())
    return query


def job_update(context, job_id, values):
    job = job_get(context, job_id)

    if not job:
        raise exception.NotFound(_('Attempt to update a job with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': job_id,
                                     'msg': 'that does not exist'})

    job.update(values)
    job.save(_session(context))
    return job


def job_delete(context, job_id):
    job = job_get(context, job_id)
    session = Session.object_session(job)
    session.delete(job)
    session.flush()
