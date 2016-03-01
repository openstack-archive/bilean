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


class UserController(object):
    """WSGI controller for Users in Bilean v1 API

    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'users'

    SUPPORTED_ACTIONS = (
        RECHARGE, ATTACH_POLICY,
    ) = (
        'recharge', 'attach_policy',
    )

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
    def action(self, req, user_id, body=None):
        """Perform specified action on a user."""
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()

        if len(body) < 1:
            raise exc.HTTPBadRequest(_('No action specified'))

        if len(body) > 1:
            raise exc.HTTPBadRequest(_('Multiple actions specified'))

        action = list(body.keys())[0]
        if action not in self.SUPPORTED_ACTIONS:
            msg = _("Unrecognized action '%s' specified") % action
            raise exc.HTTPBadRequest(msg)

        if action == self.ATTACH_POLICY:
            policy = body.get(action).get('policy', None)
            if policy is None:
                raise exc.HTTPBadRequest(_("Malformed request data, no policy "
                                           "specified to attach."))
            user = self.rpc_client.user_attach_policy(
                req.context, user_id, policy)
        elif action == self.RECHARGE:
            value = body.get(action).get('value', None)
            if value is None:
                raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                           "'value' key in request body."))
            try:
                validator.validate_float(value, 'recharge_value',
                                         consts.MIN_VALUE, consts.MAX_VALUE)
            except exception.InvalidInput as e:
                raise exc.HTTPBadRequest(explanation=e.format_message())

            user = self.rpc_client.user_recharge(req.context, user_id, value)

        return {'user': user}


def create_resource(options):
    """User resource factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(UserController(options), deserializer, serializer)
