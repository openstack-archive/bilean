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

from bilean.db import api as db_api
from bilean.engine import api


def resource_get(context, resource_id):
    return db_api.resource_get(context, resource_id)


def resource_get_all(context, **search_opts):
    resources = db_api.resource_get_all(context, **search_opts)
    if resources:
        return [api.format_bilean_resource(resource) for resource in resources]
    return []


def resource_get_by_physical_resource_id(context,
                                         physical_resource_id,
                                         resource_type):
    return db_api.resource_get_by_physical_resource_id(
        context, physical_resource_id, resource_type)


def resource_create(context, values):
    return db_api.resource_create(context, values)


def resource_update(context, resource_id, values):
    return db_api.resource_update(context, resource_id, values)


def resource_update_by_resource(context, resource):
    return db_api.resource_update_by_resource(context, resource)


def resource_delete(context, resource_id):
    db_api.resource_delete(context, resource_id)


def resource_delete_by_physical_resource_id(context,
                                            physical_resource_id,
                                            resource_type):
    db_api.resource_delete_by_physical_resource_id(
        context, physical_resource_id, resource_type)


def resource_delete_by_user_id(context, user_id):
    db_api.resource_delete(context, user_id)
