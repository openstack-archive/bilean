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

from oslo_log import log as logging
from oslo_utils import timeutils

from bilean.common import params

LOG = logging.getLogger(__name__)


def format_user(user, detail=False):
    '''Format user object to dict

    Return a representation of the given user that matches the API output
    expectations.
    '''
    updated_at = user.updated_at and timeutils.isotime(user.updated_at)
    info = {
        params.USER_ID: user.id,
        params.USER_BALANCE: user.balance,
        params.USER_RATE: user.rate,
        params.USER_CREDIT: user.credit,
        params.USER_STATUS: user.status,
        params.USER_UPDATED_AT: updated_at,
        params.USER_LAST_BILL: user.last_bill
    }
    if detail:
        info[params.USER_CREATED_AT] = user.created_at
        info[params.USER_STATUS_REASION] = user.status_reason

    return info


def format_bilean_resource(resource, detail=False):
    '''Format resource object to dict

    Return a representation of the given resource that matches the API output
    expectations.
    '''
    updated_at = resource.updated_at and timeutils.isotime(resource.updated_at)
    info = {
        params.RES_ID: resource.id,
        params.RES_RESOURCE_TYPE: resource.resource_type,
        params.RES_SIZE: resource.size,
        params.RES_RATE: resource.rate,
        params.RES_STATUS: resource.status,
        params.RES_USER_ID: resource.user_id,
        params.RES_RESOURCE_REF: resource.resource_ref,
        params.RES_UPDATED_AT: updated_at,
    }
    if detail:
        info[params.RES_CREATED_AT] = resource.created_at
        info[params.RES_RULE_ID] = resource.rule_id
        info[params.RES_STATUS_REASION] = resource.status_reason

    return info


def format_rule(rule):
    '''Format rule object to dict

    Return a representation of the given rule that matches the API output
    expectations.
    '''
    updated_at = rule.updated_at and timeutils.isotime(rule.updated_at)
    info = {
        params.RULE_ID: rule.id,
        params.RULE_RESOURCE_TYPE: rule.resource_type,
        params.RULE_SIZE: rule.size,
        params.RULE_PARAMS: rule.params,
        params.RULE_UPDATED_AT: updated_at,
        params.RULE_CREATED_AT: rule.created_at,
    }

    return info
