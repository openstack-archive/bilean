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


class PolicyData(object):
    '''The data accompanying a POST/PUT request to create/update a policy.'''

    def __init__(self, data):
        self.data = data

    def name(self):
        if consts.POLICY_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No policy name specified"))
        return self.data[consts.POLICY_NAME]

    def rules(self):
        return self.data.get(consts.POLICY_RULES)

    def metadata(self):
        return self.data.get(consts.RULE_METADATA)


class PolicyController(object):
    """WSGI controller for Policys in Bilean v1 API

    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'policies'

    SUPPORTED_ACTIONS = (
        ADD_RULES,
    ) = (
        'add_rules',
    )

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    @util.policy_enforce
    def index(self, req):
        """List summary information for all policies"""
        filter_whitelist = {
            'name': 'mixed',
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

        policies = self.rpc_client.policy_list(req.context, filters=filters,
                                               **params)

        return {'policies': policies}

    @util.policy_enforce
    def get(self, req, policy_id):
        """Get detailed information for a policy"""
        policy = self.rpc_client.policy_get(req.context,
                                            policy_id)

        return {'policy': policy}

    @util.policy_enforce
    def create(self, req, body):
        """Create a new policy"""
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()

        policy_data = body.get('policy')
        if policy_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'policy' key in request body."))

        data = PolicyData(policy_data)
        policy = self.rpc_client.policy_create(req.context,
                                               data.name(),
                                               data.rules(),
                                               data.metadata())
        return {'policy': policy}

    @util.policy_enforce
    def update(self, req, policy_id, body):
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()

        policy_data = body.get('policy')
        if policy_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'policy' key in request body."))

        name = policy_data.get(consts.POLICY_NAME)
        metadata = policy_data.get(consts.POLICY_METADATA)
        is_default = policy_data.get(consts.POLICY_IS_DEFAULT)

        policy = self.rpc_client.policy_update(req.context, policy_id, name,
                                               metadata, is_default)
        return {'policy': policy}

    @util.policy_enforce
    def delete(self, req, policy_id):
        """Delete a policy with given policy_id"""
        self.rpc_client.policy_delete(req.context, policy_id)

    @util.policy_enforce
    def action(self, req, policy_id, body=None):
        '''Perform specified action on a policy.'''
        body = body or {}
        if len(body) < 1:
            raise exc.HTTPBadRequest(_('No action specified'))

        if len(body) > 1:
            raise exc.HTTPBadRequest(_('Multiple actions specified'))

        action = list(body.keys())[0]
        if action not in self.SUPPORTED_ACTIONS:
            msg = _("Unrecognized action '%s' specified") % action
            raise exc.HTTPBadRequest(msg)

        if action == self.ADD_RULES:
            rules = body.get(action).get('rules')
            if rules is None or not isinstance(rules, list) or len(rules) == 0:
                raise exc.HTTPBadRequest(_('No rule to add'))
            policy = self.rpc_client.policy_add_rules(
                req.context, policy_id, rules)

            return {'policy': policy}


def create_resource(options):
    """Policy resource factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(PolicyController(options), deserializer, serializer)
