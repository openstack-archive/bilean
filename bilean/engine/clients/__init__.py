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

import weakref

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils
import six
from stevedore import enabled

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common.i18n import _LW

LOG = logging.getLogger(__name__)


_default_backend = "bilean.engine.clients.OpenStackClients"

cloud_opts = [
    cfg.StrOpt('client_backend',
               default=_default_backend,
               help="Fully qualified class name to use as a client backend.")
]
cfg.CONF.register_opts(cloud_opts)


class OpenStackClients(object):
    """Convenience class to create and cache client instances."""

    def __init__(self, context):
        self._context = weakref.ref(context)
        self._clients = {}
        self._client_plugins = {}

    @property
    def context(self):
        ctxt = self._context()
        assert ctxt is not None, "Need a reference to the context"
        return ctxt

    def invalidate_plugins(self):
        """Used to force plugins to clear any cached client."""
        for name in self._client_plugins:
            self._client_plugins[name].invalidate()

    def client_plugin(self, name):
        global _mgr
        if name in self._client_plugins:
            return self._client_plugins[name]
        if _mgr and name in _mgr.names():
            client_plugin = _mgr[name].plugin(self.context)
            self._client_plugins[name] = client_plugin
            return client_plugin

    def client(self, name):
        client_plugin = self.client_plugin(name)
        if client_plugin:
            return client_plugin.client()

        if name in self._clients:
            return self._clients[name]
        # call the local method _<name>() if a real client plugin
        # doesn't exist
        method_name = '_%s' % name
        if callable(getattr(self, method_name, None)):
            client = getattr(self, method_name)()
            self._clients[name] = client
            return client
        LOG.warning(_LW('Requested client "%s" not found'), name)

    @property
    def auth_token(self):
        # Always use the auth_token from the keystone() client, as
        # this may be refreshed if the context contains credentials
        # which allow reissuing of a new token before the context
        # auth_token expiry (e.g trust_id or username/password)
        return self.client('keystone').auth_token


class ClientBackend(object):
    """Class for delaying choosing the backend client module.

    Delay choosing the backend client module until the client's class needs
    to be initialized.
    """
    def __new__(cls, context):
        if cfg.CONF.client_backend == _default_backend:
            return OpenStackClients(context)
        else:
            try:
                return importutils.import_object(cfg.CONF.cloud_backend,
                                                 context)
            except (ImportError, RuntimeError, cfg.NoSuchOptError) as err:
                msg = _('Invalid cloud_backend setting in bilean.conf '
                        'detected - %s') % six.text_type(err)
                LOG.error(msg)
                raise exception.Invalid(reason=msg)


Clients = ClientBackend


_mgr = None


def has_client(name):
    return _mgr and name in _mgr.names()


def initialise():
    global _mgr
    if _mgr:
        return

    def client_is_available(client_plugin):
        if not hasattr(client_plugin.plugin, 'is_available'):
            # if the client does not have a is_available() class method, then
            # we assume it wants to be always available
            return True
        # let the client plugin decide if it wants to register or not
        return client_plugin.plugin.is_available()

    _mgr = enabled.EnabledExtensionManager(
        namespace='bilean.clients',
        check_func=client_is_available,
        invoke_on_load=False)


def list_opts():
    yield None, cloud_opts
