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

import collections
import json
import six

from novaclient import client as nc
from novaclient import exceptions
from novaclient import shell as novashell

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common.i18n import _LW
from bilean.engine.clients import client_plugin

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class NovaClientPlugin(client_plugin.ClientPlugin):

    deferred_server_statuses = ['BUILD',
                                'HARD_REBOOT',
                                'PASSWORD',
                                'REBOOT',
                                'RESCUE',
                                'RESIZE',
                                'REVERT_RESIZE',
                                'SHUTOFF',
                                'SUSPENDED',
                                'VERIFY_RESIZE']

    exceptions_module = exceptions

    def _create(self):
        computeshell = novashell.OpenStackComputeShell()
        extensions = computeshell._discover_extensions("1.1")

        endpoint_type = self._get_client_option('nova', 'endpoint_type')
        args = {
            'project_id': self.context.tenant,
            'auth_url': self.context.auth_url,
            'service_type': 'compute',
            'username': None,
            'api_key': None,
            'extensions': extensions,
            'endpoint_type': endpoint_type,
            'http_log_debug': self._get_client_option('nova',
                                                      'http_log_debug'),
            'cacert': self._get_client_option('nova', 'ca_file'),
            'insecure': self._get_client_option('nova', 'insecure')
        }

        client = nc.Client(1.1, **args)

        management_url = self.url_for(service_type='compute',
                                      endpoint_type=endpoint_type)
        client.client.auth_token = self.auth_token
        client.client.management_url = management_url

        return client

    def is_not_found(self, ex):
        return isinstance(ex, exceptions.NotFound)

    def is_over_limit(self, ex):
        return isinstance(ex, exceptions.OverLimit)

    def is_bad_request(self, ex):
        return isinstance(ex, exceptions.BadRequest)

    def is_conflict(self, ex):
        return isinstance(ex, exceptions.Conflict)

    def is_unprocessable_entity(self, ex):
        http_status = (getattr(ex, 'http_status', None) or
                       getattr(ex, 'code', None))
        return (isinstance(ex, exceptions.ClientException) and
                http_status == 422)

    def refresh_server(self, server):
        '''Refresh server's attributes.

        Log warnings for non-critical API errors.
        '''
        try:
            server.get()
        except exceptions.OverLimit as exc:
            LOG.warn(_LW("Server %(name)s (%(id)s) received an OverLimit "
                         "response during server.get(): %(exception)s"),
                     {'name': server.name,
                      'id': server.id,
                      'exception': exc})
        except exceptions.ClientException as exc:
            if ((getattr(exc, 'http_status', getattr(exc, 'code', None)) in
                 (500, 503))):
                LOG.warn(_LW('Server "%(name)s" (%(id)s) received the '
                             'following exception during server.get(): '
                             '%(exception)s'),
                         {'name': server.name,
                          'id': server.id,
                          'exception': exc})
            else:
                raise

    def get_ip(self, server, net_type, ip_version):
        """Return the server's IP of the given type and version."""
        if net_type in server.addresses:
            for ip in server.addresses[net_type]:
                if ip['version'] == ip_version:
                    return ip['addr']

    def get_status(self, server):
        '''Return the server's status.

        :param server: server object
        :returns: status as a string
        '''
        # Some clouds append extra (STATUS) strings to the status, strip it
        return server.status.split('(')[0]

    def get_flavor_id(self, flavor):
        '''Get the id for the specified flavor name.

        If the specified value is flavor id, just return it.

        :param flavor: the name of the flavor to find
        :returns: the id of :flavor:
        :raises: exception.FlavorMissing
        '''
        flavor_id = None
        flavor_list = self.client().flavors.list()
        for o in flavor_list:
            if o.name == flavor:
                flavor_id = o.id
                break
            if o.id == flavor:
                flavor_id = o.id
                break
        if flavor_id is None:
            raise exception.FlavorMissing(flavor_id=flavor)
        return flavor_id

    def get_keypair(self, key_name):
        '''Get the public key specified by :key_name:

        :param key_name: the name of the key to look for
        :returns: the keypair (name, public_key) for :key_name:
        :raises: exception.UserKeyPairMissing
        '''
        try:
            return self.client().keypairs.get(key_name)
        except exceptions.NotFound:
            raise exception.UserKeyPairMissing(key_name=key_name)

    def delete_server(self, server):
        '''Deletes a server and waits for it to disappear from Nova.'''
        if not server:
            return
        try:
            server.delete()
        except Exception as exc:
            self.ignore_not_found(exc)
            return

        while True:
            yield

            try:
                self.refresh_server(server)
            except Exception as exc:
                self.ignore_not_found(exc)
                break
            else:
                # Some clouds append extra (STATUS) strings to the status
                short_server_status = server.status.split('(')[0]
                if short_server_status in ("DELETED", "SOFT_DELETED"):
                    break
                if short_server_status == "ERROR":
                    fault = getattr(server, 'fault', {})
                    message = fault.get('message', 'Unknown')
                    code = fault.get('code')
                    errmsg = (_("Server %(name)s delete failed: (%(code)s) "
                                "%(message)s"))
                    raise exception.Error(errmsg % {"name": server.name,
                                                    "code": code,
                                                    "message": message})

    def delete(self, server_id):
        '''Delete a server by given server id'''
        self.client().servers.delete(server_id)

    def resize(self, server, flavor, flavor_id):
        """Resize the server and then call check_resize task to verify."""
        server.resize(flavor_id)
        yield self.check_resize(server, flavor, flavor_id)

    def rename(self, server, name):
        """Update the name for a server."""
        server.update(name)

    def check_resize(self, server, flavor, flavor_id):
        """Verify that a resizing server is properly resized.

        If that's the case, confirm the resize, if not raise an error.
        """
        self.refresh_server(server)
        while server.status == 'RESIZE':
            yield
            self.refresh_server(server)
        if server.status == 'VERIFY_RESIZE':
            server.confirm_resize()
        else:
            raise exception.Error(
                _("Resizing to '%(flavor)s' failed, status '%(status)s'") %
                dict(flavor=flavor, status=server.status))

    def rebuild(self, server, image_id, preserve_ephemeral=False):
        """Rebuild the server and call check_rebuild to verify."""
        server.rebuild(image_id, preserve_ephemeral=preserve_ephemeral)
        yield self.check_rebuild(server, image_id)

    def check_rebuild(self, server, image_id):
        """Verify that a rebuilding server is rebuilt.

        Raise error if it ends up in an ERROR state.
        """
        self.refresh_server(server)
        while server.status == 'REBUILD':
            yield
            self.refresh_server(server)
        if server.status == 'ERROR':
            raise exception.Error(
                _("Rebuilding server failed, status '%s'") % server.status)

    def meta_serialize(self, metadata):
        """Serialize non-string metadata values before sending them to Nova."""
        if not isinstance(metadata, collections.Mapping):
            raise exception.StackValidationFailed(message=_(
                "nova server metadata needs to be a Map."))

        return dict((key, (value if isinstance(value,
                                               six.string_types)
                           else json.dumps(value))
                     ) for (key, value) in metadata.items())

    def meta_update(self, server, metadata):
        """Delete/Add the metadata in nova as needed."""
        metadata = self.meta_serialize(metadata)
        current_md = server.metadata
        to_del = [key for key in current_md.keys() if key not in metadata]
        client = self.client()
        if len(to_del) > 0:
            client.servers.delete_meta(server, to_del)

        client.servers.set_meta(server, metadata)

    def server_to_ipaddress(self, server):
        '''Return the server's IP address, fetching it from Nova.'''
        try:
            server = self.client().servers.get(server)
        except exceptions.NotFound as ex:
            LOG.warn(_LW('Instance (%(server)s) not found: %(ex)s'),
                     {'server': server, 'ex': ex})
        else:
            for n in server.networks:
                if len(server.networks[n]) > 0:
                    return server.networks[n][0]

    def get_server(self, server):
        try:
            return self.client().servers.get(server)
        except exceptions.NotFound as ex:
            LOG.warn(_LW('Server (%(server)s) not found: %(ex)s'),
                     {'server': server, 'ex': ex})
            raise exception.ServerNotFound(server=server)

    def absolute_limits(self):
        """Return the absolute limits as a dictionary."""
        limits = self.client().limits.get()
        return dict([(limit.name, limit.value)
                    for limit in list(limits.absolute)])
