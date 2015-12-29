#
# Copyright 2012, Red Hat, Inc.
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

"""
Client side of the bilean engine RPC API.
"""

from bilean.common import messaging
from bilean.common import params

from oslo_config import cfg


class EngineClient(object):
    '''Client side of the bilean engine rpc API.'''

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self):
        self._client = messaging.get_rpc_client(
            topic=params.ENGINE_TOPIC,
            server=cfg.CONF.host,
            version=self.BASE_RPC_API_VERSION)

    @staticmethod
    def make_msg(method, **kwargs):
        return method, kwargs

    def call(self, ctxt, msg, version=None):
        method, kwargs = msg
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client
        return client.call(ctxt, method, **kwargs)

    def cast(self, ctxt, msg, version=None):
        method, kwargs = msg
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client
        return client.cast(ctxt, method, **kwargs)

    def user_list(self, ctxt):
        return self.call(ctxt, self.make_msg('user_list'))

    def user_get(self, ctxt, user_id):
        return self.call(ctxt, self.make_msg('user_get',
                                             user_id=user_id))

    def user_create(self, ctxt, user_id, balance=0, credit=0,
                    status='init'):
        values = {'id': user_id,
                  'balance': balance,
                  'credit': credit,
                  'status': status}
        return self.call(ctxt, self.make_msg('user_create', values=values))

    def user_update(self, ctxt, user_id, values):
        return self.call(ctxt, self.make_msg('user_update',
                                             user_id=user_id,
                                             values=values))

    def user_delete(self, ctxt, user_id):
        return self.call(ctxt, self.make_msg('user_delete',
                                             user_id=user_id))

    def rule_list(self, ctxt):
        return self.call(ctxt, self.make_msg('rule_list'))

    def rule_get(self, ctxt, rule_id):
        return self.call(ctxt, self.make_msg('rule_get',
                                             rule_id=rule_id))

    def rule_create(self, ctxt, name, spec, metadata):
        return self.call(ctxt, self.make_msg('rule_create', name=name,
                                             spec=spec, metadata=metadata))

    def rule_update(self, ctxt, values):
        return self.call(ctxt, self.make_msg('rule_update',
                                             values=values))

    def rule_delete(self, ctxt, rule_id):
        return self.call(ctxt, self.make_msg('rule_delete',
                                             rule_id=rule_id))

    def resource_list(self, ctxt):
        return self.call(ctxt, self.make_msg('resource_list'))

    def resource_get(self, ctxt, resource_id):
        return self.call(ctxt, self.make_msg('resource_get',
                                             resource_id=resource_id))

    def resource_create(self, ctxt, resource):
        return self.call(ctxt, self.make_msg('resource_update',
                                             resource=resource))

    def resource_update(self, ctxt, resource):
        return self.call(ctxt, self.make_msg('resource_update',
                                             resource=resource))

    def resource_delete(self, ctxt, resource):
        return self.call(ctxt, self.make_msg('resource_delete',
                                             resource=resource))

    def event_list(self, ctxt, filters=None):
        return self.call(ctxt, self.make_msg('event_list', **filters))

    def validate_creation(self, cnxt, resources):
        return self.call(cnxt, self.make_msg('validate_creation',
                                             resources=resources))
