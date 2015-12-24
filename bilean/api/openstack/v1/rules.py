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

import itertools
import six

from webob import exc

from bilean.api.openstack.v1 import util
from bilean.api import validator
from bilean.common.i18n import _
from bilean.common import params
from bilean.common import serializers
from bilean.common import wsgi
from bilean.rpc import client as rpc_client


class RuleData(object):
    '''The data accompanying a POST/PUT request to create/update a rule.'''

    def __init__(self, data):
        self.data = data

    def name(self):
        if params.RULE_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No rule name specified"))
        return self.data[params.RULE_NAME]

    def spec(self):
        if params.RULE_SPEC not in self.data:
            raise exc.HTTPBadRequest(_("No rule spec provided"))
        return self.data[params.RULE_SPEC]

    def metadata(self):
        return self.data.get(params.RULE_METADATA, None)


class RuleController(object):
    """WSGI controller for Rules in Bilean v1 API

    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'rules'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        """Lists summary information for all rules"""

        rule_list = self.rpc_client.list_rules(req.context)

        return dict(rules=rule_list)

    @util.policy_enforce
    def show(self, req, rule_id):
        """Gets detailed information for a rule"""

        return self.rpc_client.show_rule(req.context, rule_id)

    @util.policy_enforce
    def create(self, req, body):
        """Create a new rule"""
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()

        rule_data = body.get('rule')
        data = RuleData(rule_data)
        result = self.rpc_client.rule_create(req.context,
                                             data.name(),
                                             data.spec(),
                                             data.metadata())
        return {'rule': result}

    @util.policy_enforce
    def delete(self, req, rule_id):
        """Delete a rule with given rule_id"""

        res = self.rpc_client.delete_rule(req.context, rule_id)

        if res is not None:
            raise exc.HTTPBadRequest(res['Error'])

        raise exc.HTTPNoContent()


def create_resource(options):
    """Rule resource factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(RuleController(options), deserializer, serializer)
