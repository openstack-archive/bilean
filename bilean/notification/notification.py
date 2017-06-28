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

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_service import service

from bilean.common.i18n import _
from bilean.common import messaging as bilean_messaging
from bilean.engine import environment
from bilean.notification import endpoint

LOG = logging.getLogger(__name__)

listener_opts = [
    cfg.IntOpt('workers',
               default=1,
               min=1,
               help='Number of workers for notification service. A single '
               'notification agent is enabled by default.'),
    cfg.StrOpt('notifications_pool',
               default='bilean-listener',
               help='Use an oslo.messaging pool, which can be an alternative '
               'to multiple topics. ')
]

CONF = cfg.CONF
CONF.register_opts(listener_opts, group="listener")


class NotificationService(service.Service):

    def __init__(self, *args, **kwargs):
        super(NotificationService, self).__init__(*args, **kwargs)
        self.listeners = []
        self.topics_exchanges_set = self.topics_and_exchanges()

    def topics_and_exchanges(self):
        topics_exchanges = set()
        plugins = environment.global_env().get_plugins()
        for plugin in plugins:
            try:
                topic_exchanges = plugin.get_notification_topics_exchanges()
                for plugin_topic in topic_exchanges:
                    if isinstance(plugin_topic, basestring):
                        raise Exception(
                            _("Plugin %s should return a list of topic "
                              "exchange pairs") % plugin.__class__.__name__)
                    topics_exchanges.add(plugin_topic)
            except Exception as e:
                LOG.error("Failed to retrieve notification topic(s) "
                          "and exchanges from bilean plugin "
                          "%(ext)s: %(e)s",
                          {'ext': plugin.__name__, 'e': e})

        return topics_exchanges

    def start(self):
        super(NotificationService, self).start()
        transport = bilean_messaging.get_transport()
        targets = [
            oslo_messaging.Target(topic=tp, exchange=eg)
            for tp, eg in self.topics_exchanges_set
        ]
        endpoints = [endpoint.EventsNotificationEndpoint()]
        listener = oslo_messaging.get_notification_listener(
            transport,
            targets,
            endpoints,
            pool=CONF.listener.notifications_pool)

        listener.start()
        self.listeners.append(listener)

        # Add a dummy thread to have wait() working
        self.tg.add_timer(604800, lambda: None)

    def stop(self):
        map(lambda x: x.stop(), self.listeners)
        super(NotificationService, self).stop()
