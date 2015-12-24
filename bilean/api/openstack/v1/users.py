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


def format_user(req, res, keys=None):
    keys = keys or []
    include_key = lambda k: k in keys if keys else True

    def transform(key, value):
        if not include_key(key):
            return
        else:
            yield (key, value)

    return dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in res.items()))


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
    def index(self, req, tenant_id):
        """Lists summary information for all users"""

        user_list = self.rpc_client.list_users(req.context)

        return {'users': [format_user(req, u) for u in user_list]}

    @util.policy_enforce
    def show(self, req, tenant_id, user_id):
        """Gets detailed information for a user"""
        try:
            return self.rpc_client.show_user(req.context, user_id)
        except exception.NotFound:
            msg = _("User with id: %s could be found") % user_id
            raise exc.HTTPNotFound(explanation=msg)

    @util.policy_enforce
    def update(self, req, tenant_id, user_id, body):
        """Update a specify user

        :param user_id: Id of user to update
        """
        if not validator.is_valid_body(body):
            raise exc.HTTPUnprocessableEntity()

        update_dict = {}

        if 'balance' in body:
            balance = body.get('balance')
            try:
                validator.validate_float(balance, 'User_balance', 0, 1000000)
            except exception.InvalidInput as e:
                raise exc.HTTPBadRequest(explanation=e.format_message())
            update_dict['balance'] = balance
        if 'credit' in body:
            credit = body.get('credit')
            try:
                validator.validate_integer(credit, 'User_credit', 0, 100000)
            except exception.InvalidInput as e:
                raise exc.HTTPBadRequest(explanation=e.format_message())
            update_dict['credit'] = credit
        if 'status' in body:
            status = body.get('status')
            try:
                validator.validate_string(status, 'User_status',
                                          available_fields=['active',
                                                            'freeze'])
            except exception.InvalidInput as e:
                raise exc.HTTPBadRequest(explanation=e.format_message())
            update_dict['status'] = status
        if 'action' in body:
            action = body.get('action')
            try:
                validator.validate_string(action, 'Action',
                                          available_fields=['recharge',
                                                            'update',
                                                            'deduct'])
            except exception.InvalidInput as e:
                raise exc.HTTPBadRequest(explanation=e.format_message())
            update_dict['action'] = action

        try:
            return self.rpc_client.update_user(req.context,
                                               user_id,
                                               update_dict)
        except exception.NotFound:
            msg = _("User with id: %s could be found") % user_id
            raise exc.HTTPNotFound(explanation=msg)
        except Exception as e:
            LOG.error(e)


def create_resource(options):
    """User resource  factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(UserController(options), deserializer, serializer)
