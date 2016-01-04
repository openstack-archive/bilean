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
from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import serializers
from bilean.common import utils
from bilean.common import wsgi
from bilean.rpc import client as rpc_client

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class ResourceController(object):
    """WSGI controller for Resources in Bilean v1 API

    Implements the API actions, cause action 'create' and 'delete' is
    triggered by notification, it's not necessary to provide here.
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'resources'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    @util.policy_enforce
    def index(self, req):
        """Lists summary information for all resources"""
        filter_whitelist = {
            'resource_type': 'mixed',
            'rule_id': 'mixed',
        }
        param_whitelist = {
            'user_id': 'single',
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
        resources = self.rpc_client.resource_list(req.context, filters=filters,
                                                  **params)

        return {'resources': resources}

    @util.policy_enforce
    def get(self, req, resource_id):
        """Gets detailed information for a resource"""

        resource = self.rpc_client.resource_get(req.context, resource_id)

        return {'resource': resource}

    @util.policy_enforce
    def validate_creation(self, req, body):
        """Validate resources creation

        :param user_id: Id of user to validate
        :param body: dict body include resources and count

        :return True|False
        """
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()

        resources = body.get('resources', None)
        if not resources:
            msg = _("Resources is empty")
            raise exc.HTTPBadRequest(explanation=msg)
        if body.get('count', None):
            try:
                validator.validate_integer(body.get('count'), 'count',
                                           consts.MIN_RESOURCE_NUM,
                                           consts.MAX_RESOURCE_NUM)
            except exception.InvalidInput as e:
                raise exc.HTTPBadRequest(explanation=e.format_message())
        try:
            for resource in resources:
                validator.validate_resource(resource)
        except exception.InvalidInput as e:
            raise exc.HTTPBadRequest(explanation=e.format_message())
        except Exception as e:
            raise exc.HTTPBadRequest(explanation=e)

        return self.rpc_client.validate_creation(req.context, body)


def create_resource(options):
    """Resource resource  factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(ResourceController(options), deserializer, serializer)
