# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg

from bilean.drivers import base
from bilean.drivers.openstack import sdk


class NovaClient(base.DriverBase):
    '''Nova V2 driver.'''

    def __init__(self, params=None):
        super(NovaClient, self).__init__(params)
        self.conn = sdk.create_connection(self.conn_params)

    @sdk.translate_exception
    def flavor_find(self, name_or_id, ignore_missing=False):
        return self.conn.compute.find_flavor(name_or_id, ignore_missing)

    @sdk.translate_exception
    def flavor_list(self, details=True, **query):
        return self.conn.compute.flavors(details, **query)

    @sdk.translate_exception
    def image_find(self, name_or_id, ignore_missing=False):
        return self.conn.compute.find_image(name_or_id, ignore_missing)

    @sdk.translate_exception
    def image_list(self, details=True, **query):
        return self.conn.compute.images(details, **query)

    @sdk.translate_exception
    def image_delete(self, value, ignore_missing=True):
        return self.conn.compute.delete_image(value, ignore_missing)

    @sdk.translate_exception
    def server_get(self, value):
        return self.conn.compute.get_server(value)

    @sdk.translate_exception
    def server_list(self, details=True, **query):
        return self.conn.compute.servers(details, **query)

    @sdk.translate_exception
    def server_update(self, value, **attrs):
        return self.conn.compute.update_server(value, **attrs)

    @sdk.translate_exception
    def server_delete(self, value, ignore_missing=True):
        return self.conn.compute.delete_server(value, ignore_missing)

    @sdk.translate_exception
    def wait_for_server_delete(self, value, timeout=None):
        '''Wait for server deleting complete'''
        if timeout is None:
            timeout = cfg.CONF.default_action_timeout

        server_obj = self.conn.compute.find_server(value, True)
        if server_obj:
            self.conn.compute.wait_for_delete(server_obj, wait=timeout)

        return
