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

from oslo_log import log

from bilean.drivers import base
from bilean.drivers.openstack import sdk

LOG = log.getLogger(__name__)


class CinderClient(base.DriverBase):
    '''Cinder V2 driver.'''

    def __init__(self, params=None):
        super(CinderClient, self).__init__(params)
        self.conn = sdk.create_connection(self.conn_params)

    @sdk.translate_exception
    def volume_get(self, volume):
        '''Get a single volume.'''
        return self.conn.block_store.get_volume(volume)

    @sdk.translate_exception
    def volume_delete(self, volume, ignore_missing=True):
        '''Delete a volume.'''
        self.conn.block_store.delete_volume(volume,
                                            ignore_missing=ignore_missing)
