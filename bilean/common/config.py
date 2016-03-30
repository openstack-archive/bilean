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

"""Routines for configuring Bilean."""
import logging as sys_logging
import os
import socket

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging

from bilean.common.i18n import _
from bilean.common import wsgi


LOG = logging.getLogger(__name__)
paste_deploy_group = cfg.OptGroup('paste_deploy')
paste_deploy_opts = [
    cfg.StrOpt('api_paste_config', default="api-paste.ini",
               help=_("The API paste config file to use."))]

service_opts = [
    cfg.IntOpt('periodic_interval',
               default=60,
               help=_('Seconds between running periodic tasks.')),
    cfg.StrOpt('region_name_for_services',
               help=_('Default region name used to get services endpoints.')),
    cfg.IntOpt('max_response_size',
               default=524288,
               help=_('Maximum raw byte size of data from web response.')),
    cfg.IntOpt('num_engine_workers',
               default=processutils.get_worker_count(),
               help=_('Number of heat-engine processes to fork and run.')),
]

engine_opts = [
    cfg.StrOpt('environment_dir',
               default='/etc/bilean/environments',
               help=_('The directory to search for environment files.')),
    cfg.IntOpt('default_action_timeout',
               default=3600,
               help=_('Timeout in seconds for actions.')),
    cfg.IntOpt('lock_retry_times',
               default=50,
               help=_('Number of times trying to grab a lock.')),
    cfg.IntOpt('lock_retry_interval',
               default=1,
               help=_('Number of seconds between lock retries.')),
]

rpc_opts = [
    cfg.StrOpt('host',
               default=socket.gethostname(),
               help=_('Name of the engine node. '
                      'This can be an opaque identifier. '
                      'It is not necessarily a hostname, FQDN, '
                      'or IP address.'))]

cloud_backend_opts = [
    cfg.StrOpt('cloud_backend',
               default='openstack',
               help=_('Default cloud backend to use.'))]

authentication_group = cfg.OptGroup('authentication')
authentication_opts = [
    cfg.StrOpt('auth_url', default='',
               help=_('Complete public identity V3 API endpoint.')),
    cfg.StrOpt('service_username', default='bilean',
               help=_('Bilean service user name')),
    cfg.StrOpt('service_password', default='',
               help=_('Password specified for the Bilean service user.')),
    cfg.StrOpt('service_project_name', default='service',
               help=_('Name of the service project.')),
    cfg.StrOpt('service_user_domain', default='Default',
               help=_('Name of the domain for the service user.')),
    cfg.StrOpt('service_project_domain', default='Default',
               help=_('Name of the domain for the service project.')),
]

client_http_log_debug_opts = [
    cfg.BoolOpt('http_log_debug',
                default=False,
                help=_("Allow client's debug log output."))]

revision_group = cfg.OptGroup('revision')
revision_opts = [
    cfg.StrOpt('bilean_api_revision', default='1.0',
               help=_('Bilean API revision.')),
    cfg.StrOpt('bilean_engine_revision', default='1.0',
               help=_('Bilean engine revision.'))]


def list_opts():
    yield None, rpc_opts
    yield None, engine_opts
    yield None, service_opts
    yield None, cloud_backend_opts
    yield paste_deploy_group.name, paste_deploy_opts
    yield authentication_group.name, authentication_opts
    yield revision_group.name, revision_opts


cfg.CONF.register_group(paste_deploy_group)
cfg.CONF.register_group(authentication_group)
cfg.CONF.register_group(revision_group)

for group, opts in list_opts():
    cfg.CONF.register_opts(opts, group=group)


def _get_deployment_config_file():
    """Retrieves the deployment_config_file config item.

    Item formatted as an absolute pathname.
    """
    config_path = cfg.CONF.find_file(
        cfg.CONF.paste_deploy['api_paste_config'])
    if config_path is None:
        return None

    return os.path.abspath(config_path)


def load_paste_app(app_name=None):
    """Builds and returns a WSGI app from a paste config file.

    We assume the last config file specified in the supplied ConfigOpts
    object is the paste config file.

    :param app_name: name of the application to load

    :raises RuntimeError when config file cannot be located or application
            cannot be loaded from config file
    """
    if app_name is None:
        app_name = cfg.CONF.prog

    conf_file = _get_deployment_config_file()
    if conf_file is None:
        raise RuntimeError(_("Unable to locate config file [%s]") %
                           cfg.CONF.paste_deploy['api_paste_config'])

    try:
        app = wsgi.paste_deploy_app(conf_file, app_name, cfg.CONF)

        # Log the options used when starting if we're in debug mode...
        if cfg.CONF.debug:
            cfg.CONF.log_opt_values(logging.getLogger(app_name),
                                    sys_logging.DEBUG)

        return app
    except (LookupError, ImportError) as e:
        raise RuntimeError(_("Unable to load %(app_name)s from "
                             "configuration file %(conf_file)s."
                             "\nGot: %(e)r") % {'app_name': app_name,
                                                'conf_file': conf_file,
                                                'e': e})
