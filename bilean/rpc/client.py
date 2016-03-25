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

from bilean.common import consts
from bilean.common import messaging

from oslo_config import cfg


class EngineClient(object):
    '''Client side of the bilean engine rpc API.'''

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self):
        self._client = messaging.get_rpc_client(
            topic=consts.ENGINE_TOPIC,
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

    # users
    def user_list(self, ctxt, show_deleted=False, limit=None,
                  marker=None, sort_keys=None, sort_dir=None,
                  filters=None):
        return self.call(ctxt,
                         self.make_msg('user_list',
                                       show_deleted=show_deleted,
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters))

    def user_get(self, ctxt, user_id):
        return self.call(ctxt, self.make_msg('user_get',
                                             user_id=user_id))

    def user_create(self, ctxt, user_id, balance=None, credit=None,
                    status=None):
        return self.call(ctxt, self.make_msg('user_create', user_id=user_id,
                                             balance=balance, credit=credit,
                                             status=status))

    def user_recharge(self, ctxt, user_id, value):
        return self.call(ctxt, self.make_msg('user_recharge',
                                             user_id=user_id,
                                             value=value))

    def user_delete(self, ctxt, user_id):
        return self.call(ctxt, self.make_msg('user_delete',
                                             user_id=user_id))

    def user_attach_policy(self, ctxt, user_id, policy_id):
        return self.call(ctxt, self.make_msg('user_attach_policy',
                                             user_id=user_id,
                                             policy_id=policy_id))

    # rules
    def rule_list(self, ctxt, limit=None, marker=None, sort_keys=None,
                  sort_dir=None, filters=None, show_deleted=False):
        return self.call(ctxt, self.make_msg('rule_list', limit=limit,
                                             marker=marker,
                                             sort_keys=sort_keys,
                                             sort_dir=sort_dir,
                                             filters=filters,
                                             show_deleted=show_deleted))

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

    # resources
    def resource_list(self, ctxt, user_id=None, limit=None, marker=None,
                      sort_keys=None, sort_dir=None, filters=None,
                      project_safe=True, show_deleted=False):
        return self.call(ctxt, self.make_msg('resource_list', user_id=user_id,
                                             limit=limit, marker=marker,
                                             sort_keys=sort_keys,
                                             sort_dir=sort_dir,
                                             filters=filters,
                                             project_safe=project_safe,
                                             show_deleted=show_deleted))

    def resource_get(self, ctxt, resource_id):
        return self.call(ctxt, self.make_msg('resource_get',
                                             resource_id=resource_id))

    def resource_create(self, ctxt, resource_id, user_id,
                        resource_type, properties):
        return self.call(ctxt, self.make_msg('resource_create',
                                             resource_id=resource_id,
                                             user_id=user_id,
                                             resource_type=resource_type,
                                             properties=properties))

    def resource_update(self, ctxt, resource):
        return self.call(ctxt, self.make_msg('resource_update',
                                             resource=resource))

    def resource_delete(self, ctxt, resource_id):
        return self.call(ctxt, self.make_msg('resource_delete',
                                             resource_id=resource_id))

    # events
    def event_list(self, ctxt, user_id=None, limit=None, marker=None,
                   sort_keys=None, sort_dir=None, filters=None,
                   start_time=None, end_time=None, project_safe=True,
                   show_deleted=False):
        return self.call(ctxt, self.make_msg('event_list', user_id=user_id,
                                             limit=limit, marker=marker,
                                             sort_keys=sort_keys,
                                             sort_dir=sort_dir,
                                             filters=filters,
                                             start_time=start_time,
                                             end_time=end_time,
                                             project_safe=project_safe,
                                             show_deleted=show_deleted))

    def validate_creation(self, cnxt, resources):
        return self.call(cnxt, self.make_msg('validate_creation',
                                             resources=resources))

    # policies
    def policy_list(self, ctxt, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, show_deleted=False):
        return self.call(ctxt, self.make_msg('policy_list', limit=limit,
                                             marker=marker,
                                             sort_keys=sort_keys,
                                             sort_dir=sort_dir,
                                             filters=filters,
                                             show_deleted=show_deleted))

    def policy_get(self, ctxt, policy_id):
        return self.call(ctxt, self.make_msg('policy_get',
                                             policy_id=policy_id))

    def policy_create(self, ctxt, name, rules=None, metadata=None):
        return self.call(ctxt, self.make_msg('policy_create',
                                             name=name,
                                             rule_ids=rules,
                                             metadata=metadata))

    def policy_update(self, ctxt, policy_id, name=None, metadata=None,
                      is_default=None):
        return self.call(ctxt, self.make_msg('policy_update',
                                             policy_id=policy_id,
                                             name=name,
                                             metadata=metadata,
                                             is_default=is_default))

    def policy_delete(self, ctxt, policy_id):
        return self.call(ctxt, self.make_msg('policy_delete',
                                             policy_id=policy_id))

    def policy_add_rules(self, ctxt, policy_id, rules):
        return self.call(ctxt, self.make_msg('policy_add_rules',
                                             policy_id=policy_id,
                                             rules=rules))

    def settle_account(self, ctxt, user_id, task=None):
        return self.call(ctxt, self.make_msg('settle_account',
                                             user_id=user_id,
                                             task=task))
