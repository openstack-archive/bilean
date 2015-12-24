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

import functools
import six

from webob import exc

from oslo_utils import timeutils


def policy_enforce(handler):
    """Decorator that enforces policies.

    Checks the path matches the request context and enforce policy defined in
    policy.json.

    This is a handler method decorator.
    """
    @functools.wraps(handler)
    def handle_bilean_method(controller, req, tenant_id, **kwargs):
        if req.context.tenant_id != tenant_id:
            raise exc.HTTPForbidden()
        allowed = req.context.policy.enforce(context=req.context,
                                             action=handler.__name__,
                                             scope=controller.REQUEST_SCOPE)
        if not allowed:
            raise exc.HTTPForbidden()
        return handler(controller, req, **kwargs)

    return handle_bilean_method


def get_allowed_params(params, whitelist):
    """Extract from ``params`` all entries listed in ``whitelist``.

    The returning dict will contain an entry for a key if, and only if,
    there's an entry in ``whitelist`` for that key and at least one entry in
    ``params``. If ``params`` contains multiple entries for the same key, it
    will yield an array of values: ``{key: [v1, v2,...]}``

    :param params: a NestedMultiDict from webob.Request.params
    :param whitelist: an array of strings to whitelist

    :returns: a dict with {key: value} pairs
    """
    allowed_params = {}

    for key, key_type in six.iteritems(whitelist):
        value = params.get(key)
        if value:
            if key_type == 'timestamp':
                value = timeutils.parse_isotime(value)
                value = value.replace(tzinfo=None)
            allowed_params[key] = value

    return allowed_params
