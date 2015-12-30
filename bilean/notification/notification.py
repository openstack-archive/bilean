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

from oslo_log import log as logging
import oslo_messaging
from oslo_service import service

from bilean.common import consts
from bilean.common.i18n import _
from bilean.common import messaging as bilean_messaging
from bilean.notification import endpoint

LOG = logging.getLogger(__name__)


class NotificationService(service.Service):

    def __init__(self, *args, **kwargs):
        super(NotificationService, self).__init__(*args, **kwargs)
        self.targets, self.listeners = [], []
        self.transport = None
        self.group_id = None
        self.endpoints = [endpoint.EventsNotificationEndpoint()]

    def start(self):
        super(NotificationService, self).start()
        self.transport = bilean_messaging.get_transport()
        self.targets.append(
            oslo_messaging.Target(topic=consts.NOTIFICATION_TOPICS))
        listener = bilean_messaging.get_notification_listener(
            self.transport, self.targets, self.endpoints)

        LOG.info(_("Starting listener on topic: %s"),
                 consts.NOTIFICATION_TOPICS)
        listener.start()
        self.listeners.append(listener)

        # Add a dummy thread to have wait() working
        self.tg.add_timer(604800, lambda: None)

    def stop(self):
        map(lambda x: x.stop(), self.listeners)
        super(NotificationService, self).stop()
