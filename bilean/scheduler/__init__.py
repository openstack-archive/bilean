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

from bilean.common import consts
from bilean.common import messaging

from oslo_context import context as oslo_context
import oslo_messaging


supported_actions = (
    UPDATE_JOBS, DELETE_JOBS,
) = (
    'update_jobs', 'delete_jobs',
)


def notify(method, scheduler_id=None, **kwargs):
    '''Send notification to scheduler

    :param method: remote method to call
    :param scheduler_id: specify scheduler to notify; None implies broadcast
    '''
    if scheduler_id:
        # Notify specific scheduler identified by scheduler_id
        client = messaging.get_rpc_client(
            topic=consts.SCHEDULER_TOPIC,
            server=scheduler_id,
            version=consts.RPC_API_VERSION)
    else:
        # Broadcast to all schedulers
        client = messaging.get_rpc_client(
            topic=consts.SCHEDULER_TOPIC,
            version=consts.RPC_API_VERSION)
    try:
        client.call(oslo_context.get_current(), method, **kwargs)
        return True
    except oslo_messaging.MessagingTimeout:
        return False
