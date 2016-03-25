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

MIN_VALUE = 1
MAX_VALUE = 100000000

MIN_RESOURCE_NUM = 1
MAX_RESOURCE_NUM = 1000

RPC_ATTRs = (
    ENGINE_TOPIC,
    SCHEDULER_TOPIC,
    NOTIFICATION_TOPICS,
    RPC_API_VERSION,
) = (
    'bilean-engine',
    'bilean-scheduler',
    'billing_notifications',
    '1.1',
)

RPC_PARAMS = (
    PARAM_SHOW_DELETED, PARAM_SHOW_NESTED, PARAM_LIMIT, PARAM_MARKER,
    PARAM_GLOBAL_PROJECT, PARAM_SHOW_DETAILS,
    PARAM_SORT_DIR, PARAM_SORT_KEYS,
) = (
    'show_deleted', 'show_nested', 'limit', 'marker',
    'global_project', 'show_details',
    'sort_dir', 'sort_keys',
)

USER_KEYS = (
    USER_ID, USER_POLICY_ID, USER_BALANCE, USER_RATE, USER_CREDIT,
    USER_LAST_BILL, USER_STATUS, USER_STATUS_REASION, USER_CREATED_AT,
    USER_UPDATED_AT, USER_DELETED_AT,
) = (
    'id', 'policy_id', 'balance', 'rate', 'credit',
    'last_bill', 'status', 'status_reason', 'created_at',
    'updated_at', 'deleted_at',
)

RESOURCE_KEYS = (
    RES_ID, RES_USER_ID, RES_RULE_ID, RES_RESOURCE_TYPE, RES_PROPERTIES,
    RES_RATE, RES_CREATED_AT, RES_UPDATED_AT, RES_DELETED_AT,
) = (
    'id', 'user_id', 'rule_id', 'resource_type', 'properties',
    'rate', 'created_at', 'updated_at', 'deleted_at',
)

RULE_KEYS = (
    RULE_ID, RULE_NAME, RULE_TYPE, RULE_SPEC, RULE_METADATA,
    RULE_UPDATED_AT, RULE_CREATED_AT, RULE_DELETED_AT,
) = (
    'id', 'name', 'type', 'spec', 'metadata',
    'updated_at', 'created_at', 'deleted_at',
)

EVENT_KEYS = (
    EVENT_ID, EVENT_USER_ID, EVENT_ACTION, EVENT_TIMESTAMP,
    EVENT_RESOURCE_TYPE, EVENT_VALUE, EVENT_DELETED_AT,
) = (
    'id', 'user_id', 'action', 'timestamp',
    'resource_type', 'value', 'deleted_at',
)

POLICY_KEYS = (
    POLICY_ID, POLICY_NAME, POLICY_IS_DEFAULT, POLICY_RULES, POLICY_METADATA,
    POLICY_CREATED_AT, POLICY_UPDATED_AT, POLICY_DELETED_AT,
) = (
    'id', 'name', 'is_default', 'rules', 'metadata',
    'created_at', 'updated_at', 'deleted_at',
)
