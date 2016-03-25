#!/usr/bin/env python
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
Bilean API Server.

An OpenStack ReST API to Bilean
"""

import eventlet
eventlet.monkey_patch(os=False)

import sys

from bilean.common import config
from bilean.common.i18n import _LI
from bilean.common import messaging
from bilean.common import wsgi
from bilean import version

from oslo_config import cfg
import oslo_i18n as i18n
from oslo_log import log as logging
from oslo_service import systemd
import six


i18n.enable_lazy()

LOG = logging.getLogger('bilean.api')


def main():
    try:
        logging.register_options(cfg.CONF)
        cfg.CONF(project='bilean', prog='bilean-api',
                 version=version.version_info.version_string())
        logging.setup(cfg.CONF, 'bilean-api')
        messaging.setup()

        app = config.load_paste_app()

        port = cfg.CONF.bilean_api.bind_port
        host = cfg.CONF.bilean_api.bind_host
        LOG.info(_LI('Starting Bilean ReST API on %(host)s:%(port)s'),
                 {'host': host, 'port': port})
        server = wsgi.Server('bilean-api', cfg.CONF.bilean_api)
        server.start(app, default_port=port)
        systemd.notify_once()
        server.wait()
    except RuntimeError as ex:
        sys.exit("ERROR: %s" % six.text_type(ex))
