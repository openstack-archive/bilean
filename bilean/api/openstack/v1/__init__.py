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

import routes

from bilean.api.openstack.v1 import events
from bilean.api.openstack.v1 import resources
from bilean.api.openstack.v1 import rules
from bilean.api.openstack.v1 import users
from bilean.common import wsgi


class API(wsgi.Router):
    """WSGI router for Bilean v1 ReST API requests."""

    def __init__(self, conf, **local_conf):
        self.conf = conf
        mapper = routes.Mapper()

        # Users
        users_resource = users.create_resource(conf)
        users_path = "/{tenant_id}/users"
        with mapper.submapper(controller=users_resource,
                              path_prefix=users_path) as user_mapper:

            # User collection
            user_mapper.connect("users_index",
                                "",
                                action="index",
                                conditions={'method': 'GET'})

            # User detail
            user_mapper.connect("user_show",
                                "/{user_id}",
                                action="show",
                                conditions={'method': 'GET'})

            # Update user
            user_mapper.connect("user_update",
                                "/{user_id}",
                                action="update",
                                conditions={'method': 'PUT'})

        # Resources
        res_resource = resources.create_resource(conf)
        res_path = "/{tenant_id}/resources"
        with mapper.submapper(controller=res_resource,
                              path_prefix=res_path) as res_mapper:

            # Resource collection
            res_mapper.connect("resource_index",
                               "",
                               action="index",
                               conditions={'method': 'GET'})

            # Resource detail
            res_mapper.connect("resource_show",
                               "/{resource_id}",
                               action="show",
                               conditions={'method': 'GET'})

            # Validate creation
            res_mapper.connect("validate_creation",
                               "",
                               action="validate_creation",
                               conditions={'method': 'POST'})

        # Rules
        rule_resource = rules.create_resource(conf)
        rule_path = "/{tenant_id}/rules"
        with mapper.submapper(controller=rule_resource,
                              path_prefix=rule_path) as rule_mapper:

            # Rule collection
            rule_mapper.connect("rules_index",
                                "",
                                action="index",
                                conditions={'method': 'GET'})

            # Rule detail
            rule_mapper.connect("rule_show",
                                "/{rule_id}",
                                action="show",
                                conditions={'method': 'GET'})

            # Create rule
            rule_mapper.connect("rule_create",
                                "",
                                action="create",
                                conditions={'method': 'POST'})

            # Update rule
            rule_mapper.connect("rule_update",
                                "/{rule_id}",
                                action="update",
                                conditions={'method': 'PUT'})

            # Delete rule
            rule_mapper.connect("rule_delete",
                                "/{rule_id}",
                                action="delete",
                                conditions={'method': 'DELETE'})

        # Events
        event_resource = events.create_resource(conf)
        event_path = "/{tenant_id}/events"
        with mapper.submapper(controller=event_resource,
                              path_prefix=event_path) as event_mapper:

            # Event collection
            event_mapper.connect("events_index",
                                 "",
                                 action="index",
                                 conditions={'method': 'GET'})

        super(API, self).__init__(mapper)
