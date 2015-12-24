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


def user_get(context, user_id):
    return IMPL.user_get(context, user_id)


def user_update(context, user_id, values):
    return IMPL.user_update(context, user_id, values)


def user_create(context, values):
    return IMPL.user_create(context, values)


def user_delete(context, user_id):
    return IMPL.user_delete(context, user_id)


def user_get_all(context):
    return IMPL.user_get_all(context)


def user_get_by_keystone_user_id(context, user_id):
    return IMPL.user_get_by_keystone_user_id(context, user_id)


def user_delete_by_keystone_user_id(context, user_id):
    return IMPL.user_delete_by_keystone_user_id(context, user_id)


def user_update_by_keystone_user_id(context, user_id, values):
    return IMPL.user_update_by_keystone_user_id(context, user_id, values)


def rule_get(context, rule_id):
    return IMPL.rule_get(context, rule_id)


def rule_get_all(context):
    return IMPL.rule_get_all(context)


def get_rule_by_filters(context, **filters):
    return IMPL.get_rule_by_filters(context, **filters)


def rule_create(context, values):
    return IMPL.rule_create(context, values)


def rule_update(context, rule_id, values):
    return IMPL.rule_update(context, rule_id, values)


def rule_delete(context, rule_id):
    return IMPL.rule_delete(context, rule_id)


def resource_get(context, resource_id):
    return IMPL.resource_get(context, resource_id)


def resource_get_all(context, **filters):
    return IMPL.resource_get_all(context, **filters)


def resource_get_by_physical_resource_id(context,
                                         physical_resource_id,
                                         resource_type):
    return IMPL.resource_get_by_physical_resource_id(
        context, physical_resource_id, resource_type)


def resource_create(context, values):
    return IMPL.resource_create(context, values)


def resource_update(context, resource_id, values):
    return IMPL.resource_update(context, resource_id, values)


def resource_update_by_resource(context, resource):
    return IMPL.resource_update_by_resource(context, resource)


def resource_delete(context, resource_id):
    IMPL.resource_delete(context, resource_id)


def resource_delete_by_user_id(context, user_id):
    IMPL.resource_delete(context, user_id)


def resource_delete_by_physical_resource_id(context,
                                            physical_resource_id,
                                            resource_type):
    return IMPL.resource_delete_by_physical_resource_id(
        context, physical_resource_id, resource_type)


def event_get(context, event_id):
    return IMPL.event_get(context, event_id)


def event_get_by_user_id(context, user_id):
    return IMPL.event_get_by_user_id(context, user_id)


def event_get_by_user_and_resource(context,
                                   user_id,
                                   resource_type,
                                   action=None):
    return IMPL.event_get_by_user_and_resource(context,
                                               user_id,
                                               resource_type,
                                               action)


def events_get_all_by_filters(context, **filters):
    return IMPL.events_get_all_by_filters(context, **filters)


def event_create(context, values):
    return IMPL.event_create(context, values)


def event_delete(context, event_id):
    return IMPL.event_delete(context, event_id)


def event_delete_by_user_id(context, user_id):
    return IMPL.event_delete_by_user_id(context, user_id)


def job_create(context, values):
    return IMPL.job_create(context, values)


def job_get(context, job_id):
    return IMPL.job_get(context, job_id)


def job_get_by_engine_id(context, engine_id):
    return IMPL.job_get_by_engine_id(context, engine_id)


def job_update(context, job_id, values):
    return IMPL.job_update(context, job_id, values)


def job_delete(context, job_id):
    return IMPL.job_delete(context, job_id)
