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

import six
import socket

from oslo_log import log as logging
import oslo_messaging
from oslo_service import service

from bilean.common import consts
from bilean.common.i18n import _LE, _LI
from bilean.common import messaging as rpc_messaging
from bilean.engine import user as user_mod
from bilean.scheduler import cron_scheduler

LOG = logging.getLogger(__name__)


class SchedulerService(service.Service):

    def __init__(self, host, topic, manager=None, context=None):
        super(SchedulerService, self).__init__()
        self.host = host
        self.topic = topic

        self.scheduler_id = None
        self.scheduler = None
        self.target = None
        self._rpc_server = None

    def start(self):
        self.scheduler_id = socket.gethostname()

        self.scheduler = cron_scheduler.CronScheduler(
            scheduler_id=self.scheduler_id)
        LOG.info(_LI("Starting billing scheduler"))
        self.scheduler.init_scheduler()
        self.scheduler.start()

        LOG.info(_LI("Starting rpc server for bilean scheduler service"))
        self.target = oslo_messaging.Target(version=consts.RPC_API_VERSION,
                                            server=self.scheduler_id,
                                            topic=self.topic)
        self._rpc_server = rpc_messaging.get_rpc_server(self.target, self)
        self._rpc_server.start()

        super(SchedulerService, self).start()

    def _stop_rpc_server(self):
        # Stop RPC connection to prevent new requests
        LOG.info(_LI("Stopping scheduler service..."))
        try:
            self._rpc_server.stop()
            self._rpc_server.wait()
            LOG.info(_LI('Scheduler service stopped successfully'))
        except Exception as ex:
            LOG.error(_LE('Failed to stop scheduler service: %s'),
                      six.text_type(ex))

    def stop(self):
        self._stop_rpc_server()

        LOG.info(_LI("Stopping billing scheduler"))
        self.scheduler.stop()

        super(SchedulerService, self).stop()

    def update_jobs(self, ctxt, user):
        user_obj = user_mod.User.from_dict(user)
        self.scheduler.update_jobs(user_obj)

    def delete_jobs(self, ctxt, user):
        user_obj = user_mod.User.from_dict(user)
        self.scheduler.delete_jobs(user_obj)
