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

import base64
import copy

from oslo_log import log as logging
from oslo_utils import encodeutils
import six

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import schema
from bilean.common import utils
from bilean.rules import base

LOG = logging.getLogger(__name__)


class ServerRule(base.Rule):
    '''Rule for an OpenStack Nova server.'''

    KEYS = (
        PRICE_MAPPING, UNIT,
    ) = (
        'price_mapping', 'unit',
    )

    PM_KEYS = (
        FLAVOR, PRICE,
    ) = (
        'flavor', 'price',
    )

    AVAILABLE_UNIT = (
        PER_HOUR, PER_SEC,
    ) = (
        'per_hour', 'per_sec',
    )

    properties_schema = {
        PRICE_MAPPING: schema.List(
            _('A list specifying the price of each flavor'),
            schema=schema.Map(
                _('A map specifying the pricce of a flavor.'),
                schema={
                    FLAVOR: schema.String(
                        _('Flavor id to set price.'),
                    ),
                    PRICE: schema.Integer(
                        _('Price of this flavor.'),
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

        If no exact price found, it shows that rule of the server's flavor
        has not been set, will return 0 as the price notify admin to set 
        it.

        :param: resource: Resource object to find price.
        '''
        flavor = resource.properties.get('flavor', None)
        if not flavor:
            raise exception.Error(msg='Flavor should be provided to get '
                                      'the price of server.')
        p_mapping = self.properties.get(self.PRICE_MAPPING)
        price = 0
        for pm in p_mapping:
            if flavor == pm.get(self.FLAVOR):
                price = pm.get(self.PRICE)
        if self.PER_HOUR == self.properties.get(self.UNIT) and price > 0:
            price = price * 1.0 / 3600
        return price
