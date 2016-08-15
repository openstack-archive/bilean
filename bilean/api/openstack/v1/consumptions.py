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

from bilean.api.openstack.v1 import util
from bilean.common import consts
from bilean.common import serializers
from bilean.common import utils
from bilean.common import wsgi
from bilean.rpc import client as rpc_client


class ConsumptionController(object):
    """WSGI controller for Consumptions in Bilean v1 API."""
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'consumptions'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    @util.policy_enforce
    def index(self, req):
        """Lists all consumptions."""
        filter_whitelist = {
            'resource_type': 'mixed',
        }
        param_whitelist = {
            'user_id': 'single',
            'start_time': 'single',
            'end_time': 'single',
            'limit': 'single',
            'marker': 'single',
            'sort_dir': 'single',
            'sort_keys': 'multi',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        if not filters:
            filters = None
        consumptions = self.rpc_client.consumption_list(req.context,
                                                        filters=filters,
                                                        **params)

        return {'consumptions': consumptions}

    @util.policy_enforce
    def statistics(self, req):
        '''Consumptions statistics.'''
        filter_whitelist = {
            'resource_type': 'mixed',
        }
        param_whitelist = {
            'user_id': 'single',
            'start_time': 'single',
            'end_time': 'single',
            'summary': 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_SUMMARY
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        if not filters:
            filters = None
        statistics = self.rpc_client.consumption_statistics(req.context,
                                                            filters=filters,
                                                            **params)

        return {'statistics': statistics}


def create_resource(ops):
    """Consumption resource factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(ConsumptionController(ops), deserializer, serializer)
