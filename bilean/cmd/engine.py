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
Bilean Engine Server.
"""

import eventlet
eventlet.monkey_patch()

from bilean.common import consts
from bilean.common import messaging

from oslo_config import cfg
from oslo_i18n import _lazy
from oslo_log import log as logging
from oslo_service import service

_lazy.enable_lazy()

LOG = logging.getLogger('bilean.engine')


def main():
    logging.register_options(cfg.CONF)
    cfg.CONF(project='bilean', prog='bilean-engine')
    logging.setup(cfg.CONF, 'bilean-engine')
    logging.set_defaults()
    messaging.setup()

    from bilean.engine import service as engine

    srv = engine.EngineService(cfg.CONF.host, consts.ENGINE_TOPIC)
    launcher = service.launch(cfg.CONF, srv,
                              workers=cfg.CONF.num_engine_workers)
    launcher.wait()
