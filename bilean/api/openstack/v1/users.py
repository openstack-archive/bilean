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
from bilean.common import consts
from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import serializers
from bilean.common import utils
from bilean.common import wsgi
from bilean.rpc import client as rpc_client

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class UserController(object):
    """WSGI controller for Users in Bilean v1 API

    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'users'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            'status': 'mixed',
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

        users = self.rpc_client.user_list(req.context, filters=filters,
                                          **params)

        return {'users': users}

    @util.policy_enforce
    def get(self, req, user_id):
        """Get detailed information for a user"""
        user = self.rpc_client.user_get(req.context, user_id)
        return {'user': user}

    @util.policy_enforce
    def recharge(self, req, user_id, body):
        """Recharge for a specify user

        :param user_id: Id of user to recharge
        """
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()

        value = body.get('value', None)
        if value is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'value' key in request body."))

        user = self.rpc_client.user_recharge(req.context, user_id, value)
        return {'user': user}


def create_resource(options):
    """User resource factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(UserController(options), deserializer, serializer)
