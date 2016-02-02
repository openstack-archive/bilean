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

from bilean.api.middleware.context import ContextMiddleware
from bilean.api.middleware.fault import FaultWrapper
from bilean.api.middleware.ssl import SSLMiddleware
from bilean.api.middleware.version_negotiation import VersionNegotiationFilter
from bilean.api.openstack import versions


def version_negotiation_filter(app, conf, **local_conf):
    return VersionNegotiationFilter(versions.Controller, app,
                                    conf, **local_conf)


def faultwrap_filter(app, conf, **local_conf):
    return FaultWrapper(app)


def sslmiddleware_filter(app, conf, **local_conf):
    return SSLMiddleware(app)


def contextmiddleware_filter(app, conf, **local_conf):
    return ContextMiddleware(app)
