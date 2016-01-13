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

from bilean.common import context
from bilean.common.i18n import _
from bilean.common.i18n import _LE
from bilean.notification import action as notify_action
from bilean.notification import converter

from oslo_log import log as logging
import oslo_messaging

LOG = logging.getLogger(__name__)

KEYSTONE_EVENTS = ['identity.project.created',
                   'identity.project.deleted']


class EventsNotificationEndpoint(object):
    def __init__(self):
        self.resource_converter = converter.setup_resources()
        self.cnxt = context.get_admin_context()
        super(EventsNotificationEndpoint, self).__init__()

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        """Convert message to Billing Event.

        :param ctxt: oslo_messaging context
        :param publisher_id: publisher of the notification
        :param event_type: type of notification
        :param payload: notification payload
        :param metadata: metadata about the notification
        """
        notification = dict(event_type=event_type,
                            payload=payload,
                            metadata=metadata)
        LOG.debug(_("Receive notification: %s") % notification)
        if event_type in KEYSTONE_EVENTS:
            return self.process_identity_notification(notification)
        return self.process_resource_notification(notification)

    def process_identity_notification(self, notification):
        """Convert notification to user."""
        user_id = notification['payload'].get('resource_info', None)
        if not user_id:
            LOG.error(_LE("Cannot retrieve user_id from notification: %s"),
                      notification)
            return oslo_messaging.NotificationResult.HANDLED
        action = self._get_action(notification['event_type'])
        if action:
            act = notify_action.UserAction(self.cnxt, action, user_id)
            LOG.info(_("Notify engine to %(action)s user: %(user)s") %
                     {'action': action, 'user': user_id})
            act.execute()

        return oslo_messaging.NotificationResult.HANDLED

    def process_resource_notification(self, notification):
        """Convert notification to resources."""
        resources = self.resource_converter.to_resources(notification)
        if not resources:
            LOG.info('Ignore notification because no matched resources '
                     'found from notification.')
            return oslo_messaging.NotificationResult.HANDLED

        action = self._get_action(notification['event_type'])
        if action:
            for resource in resources:
                act = notify_action.ResourceAction(
                    self.cnxt, action, resource)
                LOG.info(_("Notify engine to %(action)s resource: "
                           "%(resource)s") % {'action': action,
                                              'resource': resource})
                act.execute()

        return oslo_messaging.NotificationResult.HANDLED

    def _get_action(self, event_type):
        available_actions = ['create', 'delete', 'update']
        for action in available_actions:
            if action in event_type:
                return action
        LOG.info(_("Can not get action info in event_type: %s") % event_type)
        return None
