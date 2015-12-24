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

from webob import exc

from bilean.api.openstack.v1 import util
from bilean.api import validator
from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import serializers
from bilean.common import wsgi
from bilean.rpc import client as rpc_client

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def format_resource(req, res, keys=None):
    keys = keys or []
    include_key = lambda k: k in keys if keys else True

    def transform(key, value):
        if not include_key(key):
            return
        else:
            yield (key, value)

    return dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in res.items()))


class ResourceController(object):
    """WSGI controller for Resources in Bilean v1 API

    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'resources'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    @util.policy_enforce
    def index(self, req, tenant_id):
        """Lists summary information for all resources"""
        resource_list = self.rpc_client.list_resources(req.context)

        return dict(resources=resource_list)

    @util.policy_enforce
    def show(self, req, resource_id):
        """Gets detailed information for a resource"""

        resource = self.rpc_client.show_resource(req.context, resource_id)

        return {'resource': format_resource(req, resource)}

    @util.policy_enforce
    def validate_creation(self, req, body):
        """Validate resources creation

        :param user_id: Id of user to validate
        :param body: dict body include resources and count

        :return True|False
        """
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()
        if not body.get('resources'):
            msg = _("Resources is empty")
            raise exc.HTTPBadRequest(explanation=msg)
        if body.get('count'):
            try:
                validator.validate_integer(
                    body.get('count'), 'count', 0, 1000)
            except exception.InvalidInput as e:
                raise exc.HTTPBadRequest(explanation=e.format_message())
        resources = body.get('resources')
        try:
            for resource in resources:
                validator.validate_resource(resource)
        except exception.InvalidInput as e:
            raise exc.HTTPBadRequest(explanation=e.format_message())
        except Exception as e:
            raise exc.HTTPBadRequest(explanation=e)
        try:
            return self.rpc_client.validate_creation(req.context, body)
        except Exception as e:
            LOG.error(e)


def create_resource(options):
    """Resource resource  factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(ResourceController(options), deserializer, serializer)
