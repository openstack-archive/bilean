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


def list_rules(context):
    rules = db_api.rule_get_all(context)
    return rules


def create_rule(context, values):
    return db_api.rule_create(context, values)


def get_rule(context, rule_id):
    return db_api.rule_get(context, rule_id)


def delete_rule(context, rule_id):
    return db_api.rule_delete(context, rule_id)


def get_rule_by_filters(context, **filters):
    return db_api.get_rule_by_filters(context, **filters)


def update_rule(context, rule_id, values):
    return db_api.rule_update(context, rule_id, values)
