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

from webob import exc

from bilean.api.openstack.v1 import util
from bilean.api import validator
from bilean.common import consts
from bilean.common.i18n import _
from bilean.common import serializers
from bilean.common import utils
from bilean.common import wsgi
from bilean.rpc import client as rpc_client


class RuleData(object):
    '''The data accompanying a POST/PUT request to create/update a rule.'''

    def __init__(self, data):
        self.data = data

    def name(self):
        if consts.RULE_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No rule name specified"))
        return self.data[consts.RULE_NAME]

    def spec(self):
        if consts.RULE_SPEC not in self.data:
            raise exc.HTTPBadRequest(_("No rule spec provided"))
        return self.data[consts.RULE_SPEC]

    def metadata(self):
        return self.data.get(consts.RULE_METADATA)


class RuleController(object):
    """WSGI controller for Rules in Bilean v1 API

    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'rules'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    @util.policy_enforce
    def index(self, req):
        """List summary information for all rules"""
        filter_whitelist = {
            'name': 'mixed',
            'type': 'mixed',
            'metadata': 'mixed',
        }
        param_whitelist = {
            'limit': 'single',
            'marker': 'single',
            'sort_dir': 'single',
            'sort_keys': 'multi',
            'show_deleted': 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        if not filters:
            filters = None

        rules = self.rpc_client.rule_list(req.context, filters=filters,
                                          **params)

        return {'rules': rules}

    @util.policy_enforce
    def get(self, req, rule_id):
        """Get detailed information for a rule"""
        rule = self.rpc_client.rule_get(req.context,
                                        rule_id)

        return {'rule': rule}

    @util.policy_enforce
    def create(self, req, body):
        """Create a new rule"""
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()

        rule_data = body.get('rule')
        if rule_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'rule' key in request body."))

        data = RuleData(rule_data)
        rule = self.rpc_client.rule_create(req.context,
                                           data.name(),
                                           data.spec(),
                                           data.metadata())
        return {'rule': rule}

    @util.policy_enforce
    def delete(self, req, rule_id):
        """Delete a rule with given rule_id"""
        self.rpc_client.rule_delete(req.context, rule_id)


def create_resource(options):
    """Rule resource factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(RuleController(options), deserializer, serializer)
