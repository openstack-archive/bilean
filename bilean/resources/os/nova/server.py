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

from bilean.common.i18n import _LE
from bilean.db import api as db_api
from bilean.drivers import base as driver_base
from bilean.resources import base

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class ServerResource(base.Resource):
    '''Resource for an OpenStack Nova server.'''

    @classmethod
    def do_check(context, user):
        '''Communicate with other services and check user's resources.

        This would be a period job of user to check if there are any missing
        actions, and then make correction.
        '''
        # TODO(ldb)
        return NotImplemented

    def do_delete(self, context, ignore_missing=True, timeout=None):
        '''Delete resource from other services.'''

        # Delete resource from db
        db_api.resource_delete(context, self.id)

        #Delete resource from nova
        novaclient = driver_base.BileanDriver().compute()
        try:
            novaclient.server_delete(self.id, ignore_missing=ignore_missing)
            novaclient.wait_for_server_delete(self.id, timeout=timeout)
        except Exception as ex:
            LOG.error(_LE('Error: %s'), six.text_type(ex))
            return False

        return True
