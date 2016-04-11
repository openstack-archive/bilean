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

RPC_ATTRS = (
    ENGINE_TOPIC,
    SCHEDULER_TOPIC,
    NOTIFICATION_TOPICS,
    ENGINE_DISPATCHER_TOPIC,
    RPC_API_VERSION,
) = (
    'bilean-engine',
    'bilean-scheduler',
    'billing_notifications',
    'bilean_engine_dispatcher',
    '1.0',
)

USER_STATUSES = (
    USER_INIT, USER_FREE, USER_ACTIVE, USER_WARNING, USER_FREEZE,
) = (
    'INIT', 'FREE', 'ACTIVE', 'WARNING', 'FREEZE',
)

ACTION_NAMES = (
    USER_CREATE_RESOURCE, USER_UPDATE_RESOURCE, USER_DELETE_RESOURCE,
    USER_SETTLE_ACCOUNT,
) = (
    'USER_CREATE_RESOURCE', 'USER_UPDATE_RESOURCE', 'USER_DELETE_RESOURCE',
    'USER_SETTLE_ACCOUNT',
)

ACTION_STATUSES = (
    ACTION_INIT, ACTION_WAITING, ACTION_READY, ACTION_RUNNING,
    ACTION_SUCCEEDED, ACTION_FAILED, ACTION_CANCELLED
) = (
    'INIT', 'WAITING', 'READY', 'RUNNING',
    'SUCCEEDED', 'FAILED', 'CANCELLED',
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
    USER_ID, USER_NAME, USER_POLICY_ID, USER_BALANCE, USER_RATE, USER_CREDIT,
    USER_LAST_BILL, USER_STATUS, USER_STATUS_REASION, USER_CREATED_AT,
    USER_UPDATED_AT, USER_DELETED_AT,
) = (
    'id', 'name', 'policy_id', 'balance', 'rate', 'credit',
    'last_bill', 'status', 'status_reason', 'created_at',
    'updated_at', 'deleted_at',
)

RESOURCE_KEYS = (
    RES_ID, RES_USER_ID, RES_RULE_ID, RES_RESOURCE_TYPE, RES_PROPERTIES,
    RES_RATE, RES_LAST_BILL, RES_CREATED_AT, RES_UPDATED_AT, RES_DELETED_AT,
) = (
    'id', 'user_id', 'rule_id', 'resource_type', 'properties',
    'rate', 'last_bill', 'created_at', 'updated_at', 'deleted_at',
)

RULE_KEYS = (
    RULE_ID, RULE_NAME, RULE_TYPE, RULE_SPEC, RULE_METADATA,
    RULE_UPDATED_AT, RULE_CREATED_AT, RULE_DELETED_AT,
) = (
    'id', 'name', 'type', 'spec', 'metadata',
    'updated_at', 'created_at', 'deleted_at',
)

EVENT_KEYS = (
    EVENT_ID, EVENT_TIMESTAMP, EVENT_OBJ_ID, EVENT_OBJ_TYPE, EVENT_ACTION,
    EVENT_USER_ID, EVENT_LEVEL, EVENT_STATUS, EVENT_STATUS_REASON,
    EVENT_METADATA,
) = (
    'id', 'timestamp', 'obj_id', 'obj_type', 'action',
    'user_id', 'level', 'status', 'status_reason', 'metadata',
)

POLICY_KEYS = (
    POLICY_ID, POLICY_NAME, POLICY_IS_DEFAULT, POLICY_RULES, POLICY_METADATA,
    POLICY_CREATED_AT, POLICY_UPDATED_AT, POLICY_DELETED_AT,
) = (
    'id', 'name', 'is_default', 'rules', 'metadata',
    'created_at', 'updated_at', 'deleted_at',
)

CONSUMPTION_KEYS = (
    CONSUMPTION_ID, CONSUMPTION_USER_ID, CONSUMPTION_RESOURCE_ID,
    CONSUMPTION_RESOURCE_TYPE, CONSUMPTION_START_TIME, CONSUMPTION_END_TIME,
    CONSUMPTION_RATE, CONSUMPTION_COST, CONSUMPTION_METADATA,
) = (
    'id', 'user_id', 'resource_id',
    'resource_type', 'start_time', 'end_time',
    'rate', 'cost', 'metadata',
)

RECHARGE_KEYS = (
    RECHARGE_ID, RECHARGE_USER_ID, RECHARGE_TYPE, RECHARGE_TIMESTAMP,
    RECHARGE_METADATA,
) = (
    'id', 'user_id', 'type', 'timestamp', 'metadata',
)

RECHARGE_TYPES = (
    SELF_RECHARGE, SYSTEM_BONUS,
) = (
    'Recharge', 'System bonus',
)
