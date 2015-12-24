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

from bilean.common.i18n import _LE
from bilean.rpc import client as rpc_client

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class Action(object):
    def __init__(self, cnxt, action, data):
        self.rpc_client = rpc_client.EngineClient()
        self.cnxt = cnxt
        self.action = action
        self.data = data

    def execute(self):
        """Wrapper of action execution."""
        action_name = self.action.lower()
        method_name = "do_" + action_name
        method = getattr(self, method_name, None)
        if method is None:
            LOG.error(_LE('Unsupported action: %s.') % self.action)
            return None
        return method()

    def do_create(self):
        return NotImplemented

    def do_update(self):
        return NotImplemented

    def do_delete(self):
        return NotImplemented

    
class ResourceAction(Action):
    """Notification controller for Resources."""

    def do_create(self):
        """Create a new resource"""
        return self.rpc_client.resource_create(self.cnxt, self.data)

    def do_update(self):
        """Update a resource"""
        return self.rpc_client.resource_update(self.cnxt, self.data)

    def do_delete(self):
        """Delete a resource"""
        return self.rpc_client.resource_delete(self.cnxt, self.data)


class UserAction(Action):
    """Notification controller for Users."""

    def do_create(self):
        """Create a new user"""
        return self.rpc_client.user_create(self.cnxt, user_id=self.data)

    def do_delete(self):
        """Delete a user"""
        return self.rpc_client.delete_user(self.cnxt, user_id=self.data)
