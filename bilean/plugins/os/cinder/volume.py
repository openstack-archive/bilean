# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import six

from oslo_log import log as logging

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import schema
from bilean.drivers import base as driver_base
from bilean.plugins import base

LOG = logging.getLogger(__name__)


class VolumeRule(base.Rule):
    '''Rule for an OpenStack Cinder volume.'''

    KEYS = (
        PRICE_MAPPING, UNIT,
    ) = (
        'price_mapping', 'unit',
    )

    PM_KEYS = (
        START, END, PRICE,
    ) = (
        'start', 'end', 'price',
    )

    AVAILABLE_UNIT = (
        PER_HOUR, PER_SEC,
    ) = (
        'per_hour', 'per_sec',
    )

    properties_schema = {
        PRICE_MAPPING: schema.List(
            _('A list specifying the prices.'),
            schema=schema.Map(
                _('A map specifying the pricce of each volume capacity '
                  'interval.'),
                schema={
                    START: schema.Integer(
                        _('Start volume capacity.'),
                    ),
                    END: schema.Integer(
                        _('End volume capacity.'),
                    ),
                    PRICE: schema.Integer(
                        _('Price of this interval.'),
                    ),
                }
            ),
            required=True,
            updatable=True,
        ),
        UNIT: schema.String(
            _('Unit of price, per_hour or per_sec.'),
            default='per_hour',
        ),
    }

    def get_price(self, resource):
        '''Get the price of resource in seconds.

        If no exact price found, 0 will be returned.

        :param: resource: Resource object to find price.
        '''
        size = int(resource.properties.get('size'))
        if not size:
            raise exception.Error(msg='Size of volume should be provided to '
                                      'get price.')
        p_mapping = self.properties.get(self.PRICE_MAPPING)
        for pm in p_mapping:
            if size >= pm.get(self.START) and size <= pm.get(self.END):
                price = pm.get(self.PRICE)
        if self.PER_HOUR == self.properties.get(self.UNIT) and price > 0:
            price = price * 1.0 / 3600
        return price


class VolumeResource(base.Resource):
    '''Resource for an OpenStack Cinder volume.'''

    @classmethod
    def do_check(context, user):
        '''Communicate with other services and check user's resources.

        This would be a period job of user to check if there are any missing
        actions, and then make correction.
        '''
        # TODO(ldb)
        return NotImplemented

    def do_delete(self, context, timestamp=None, ignore_missing=True,
                  timeout=None):
        '''Delete resource from other services.'''

        # Delete resource from db and generate consumption
        self.delete(context, timestamp=timestamp)
        self.consumption.store(context)

        # Delete resource from cinder
        cinderclient = driver_base.BileanDriver().block_store()
        try:
            cinderclient.volume_delete(self.id, ignore_missing=ignore_missing)
        except Exception as ex:
            LOG.error('Error: %s', six.text_type(ex))
            return False

        return True


class VolumePlugin(base.Plugin):
    '''Plugin for Openstack Nova server.'''

    RuleClass = VolumeRule
    ResourceClass = VolumeResource
    notification_exchanges = ['openstack']
