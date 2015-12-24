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

from bilean.engine.clients import client_plugin

from oslo_config import cfg

from keystoneclient import exceptions
from keystoneclient.v2_0 import client as keystone_client


class KeystoneClientPlugin(client_plugin.ClientPlugin):

    exceptions_module = exceptions

    @property
    def kclient(self):
        return keystone_client.Client(
            username=cfg.CONF.authentication.service_username,
            password=cfg.CONF.authentication.service_password,
            tenant_name=cfg.CONF.authentication.service_project_name,
            auth_url=cfg.CONF.authentication.auth_url)

    def _create(self):
        return self.kclient

    def is_not_found(self, ex):
        return isinstance(ex, exceptions.NotFound)

    def is_over_limit(self, ex):
        return isinstance(ex, exceptions.RequestEntityTooLarge)

    def is_conflict(self, ex):
        return isinstance(ex, exceptions.Conflict)
