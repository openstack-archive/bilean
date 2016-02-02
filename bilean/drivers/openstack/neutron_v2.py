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

from bilean.drivers import base
from bilean.drivers.openstack import sdk


class NeutronClient(base.DriverBase):
    '''Neutron V2 driver.'''

    def __init__(self, params=None):
        super(NeutronClient, self).__init__(params)
        self.conn = sdk.create_connection(self.conn_params)

    @sdk.translate_exception
    def network_get(self, name_or_id):
        network = self.conn.network.find_network(name_or_id)
        return network

    @sdk.translate_exception
    def network_delete(self, network, ignore_missing=True):
        self.conn.network.delete_network(
            network, ignore_missing=ignore_missing)
        return

    @sdk.translate_exception
    def subnet_get(self, name_or_id):
        subnet = self.conn.network.find_subnet(name_or_id)
        return subnet

    @sdk.translate_exception
    def subnet_delete(self, subnet, ignore_missing=True):
        self.conn.network.delete_subnet(
            subnet, ignore_missing=ignore_missing)
        return

    @sdk.translate_exception
    def loadbalancer_get(self, name_or_id):
        lb = self.conn.network.find_load_balancer(name_or_id)
        return lb

    @sdk.translate_exception
    def loadbalancer_list(self):
        lbs = [lb for lb in self.conn.network.load_balancers()]
        return lbs

    @sdk.translate_exception
    def loadbalancer_delete(self, lb_id, ignore_missing=True):
        self.conn.network.delete_load_balancer(
            lb_id, ignore_missing=ignore_missing)
        return

    @sdk.translate_exception
    def listener_get(self, name_or_id):
        listener = self.conn.network.find_listener(name_or_id)
        return listener

    @sdk.translate_exception
    def listener_list(self):
        listeners = [i for i in self.conn.network.listeners()]
        return listeners

    @sdk.translate_exception
    def listener_delete(self, listener_id, ignore_missing=True):
        self.conn.network.delete_listener(listener_id,
                                          ignore_missing=ignore_missing)
        return

    @sdk.translate_exception
    def pool_get(self, name_or_id):
        pool = self.conn.network.find_pool(name_or_id)
        return pool

    @sdk.translate_exception
    def pool_list(self):
        pools = [p for p in self.conn.network.pools()]
        return pools

    @sdk.translate_exception
    def pool_delete(self, pool_id, ignore_missing=True):
        self.conn.network.delete_pool(pool_id,
                                      ignore_missing=ignore_missing)
        return

    @sdk.translate_exception
    def pool_member_get(self, pool_id, name_or_id):
        member = self.conn.network.find_pool_member(name_or_id,
                                                    pool_id)
        return member

    @sdk.translate_exception
    def pool_member_list(self, pool_id):
        members = [m for m in self.conn.network.pool_members(pool_id)]
        return members

    @sdk.translate_exception
    def pool_member_delete(self, pool_id, member_id, ignore_missing=True):
        self.conn.network.delete_pool_member(
            member_id, pool_id, ignore_missing=ignore_missing)
        return

    @sdk.translate_exception
    def healthmonitor_get(self, name_or_id):
        hm = self.conn.network.find_health_monitor(name_or_id)
        return hm

    @sdk.translate_exception
    def healthmonitor_list(self):
        hms = [hm for hm in self.conn.network.health_monitors()]
        return hms

    @sdk.translate_exception
    def healthmonitor_delete(self, hm_id, ignore_missing=True):
        self.conn.network.delete_health_monitor(
            hm_id, ignore_missing=ignore_missing)
        return
