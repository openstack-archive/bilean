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

from bilean.api.openstack.v1 import util
from bilean.common import consts
from bilean.common import serializers
from bilean.common import wsgi
from bilean.rpc import client as rpc_client


def format_event(req, res, keys=None):
    keys = keys or []
    include_key = lambda k: k in keys if keys else True

    def transform(key, value):
        if not include_key(key):
            return
        else:
            yield (key, value)

    return dict(itertools.chain.from_iterable(
        transform(k, v) for k, v in res.items()))


class EventController(object):
    """WSGI controller for Events in Bilean v1 API

    Implements the API actions
    """
    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'events'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    @util.policy_enforce
    def index(self, req, tenant_id):
        """Lists summary information for all users"""
        filter_fields = {
            'user_id': 'string',
            'resource_type': 'string',
            'action': 'string',
            'start': 'timestamp',
            'end': 'timestamp',
        }
        filter_params = util.get_allowed_params(req.params, filter_fields)
        if 'aggregate' in req.params:
            aggregate = req.params.get('aggregate')
            if aggregate in ['sum', 'avg']:
                filter_params['aggregate'] = aggregate
                events = self.rpc_client.list_events(
                    req.context, filters=filter_params)
                event_statistics = self._init_event_statistics()
                for e in events:
                    if e[0] in event_statistics:
                        event_statistics[e[0]] = e[1]
                return dict(events=event_statistics)

        events = self.rpc_client.list_events(
            req.context, filters=filter_params)
        return dict(events=events)

    def _init_event_statistics(self):
        event_statistics = {}
        for resource in consts.RESOURCE_TYPES:
            event_statistics[resource] = 0
        return event_statistics


def create_resource(options):
    """User resource  factory method."""
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = serializers.JSONResponseSerializer()
    return wsgi.Resource(EventController(options), deserializer, serializer)
