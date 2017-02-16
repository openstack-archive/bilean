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

from bilean.common import exception
from bilean.common import utils
from bilean.db import api as db_api


class Consumption(object):
    """Class reference to consumption record."""

    def __init__(self, user_id, **kwargs):
        self.id = kwargs.get('id')
        self.user_id = user_id

        self.resource_id = kwargs.get('resource_id')
        self.resource_type = kwargs.get('resource_type')

        self.start_time = utils.make_decimal(kwargs.get('start_time', 0))
        self.end_time = utils.make_decimal(kwargs.get('end_time', 0))
        self.rate = utils.make_decimal(kwargs.get('rate', 0))
        self.cost = utils.make_decimal(kwargs.get('cost', 0))
        self.metadata = kwargs.get('metadata')

    @classmethod
    def from_db_record(cls, record):
        '''Construct a consumption object from a database record.'''

        kwargs = {
            'id': record.id,
            'resource_id': record.resource_id,
            'resource_type': record.resource_type,
            'start_time': record.start_time,
            'end_time': record.end_time,
            'rate': record.rate,
            'cost': record.cost,
            'metadata': record.meta_data,
        }
        return cls(record.user_id, **kwargs)

    @classmethod
    def load(cls, context, db_consumption=None, consumption_id=None,
             project_safe=True):
        '''Retrieve a consumption record from database.'''
        if db_consumption is not None:
            return cls.from_db_record(db_consumption)

        record = db_api.consumption_get(context, consumption_id,
                                        project_safe=project_safe)
        if record is None:
            raise exception.ConsumptionNotFound(consumption=consumption_id)

        return cls.from_db_record(record)

    @classmethod
    def load_all(cls, context, user_id=None, limit=None, marker=None,
                 sort_keys=None, sort_dir=None, filters=None,
                 project_safe=True):
        '''Retrieve all consumptions from database.'''

        records = db_api.consumption_get_all(context,
                                             user_id=user_id,
                                             limit=limit,
                                             marker=marker,
                                             filters=filters,
                                             sort_keys=sort_keys,
                                             sort_dir=sort_dir,
                                             project_safe=project_safe)

        for record in records:
            yield cls.from_db_record(record)

    def store(self, context):
        '''Store the consumption into database and return its ID.'''
        values = {
            'user_id': self.user_id,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'start_time': utils.format_decimal(self.start_time),
            'end_time': utils.format_decimal(self.end_time),
            'rate': utils.format_decimal(self.rate),
            'cost': utils.format_decimal(self.cost),
            'meta_data': self.metadata,
        }

        consumption = db_api.consumption_create(context, values)
        self.id = consumption.id

        return self.id

    def delete(self, context):
        '''Delete consumption from database.'''
        db_api.consumption_delete(context, self.id)

    def to_dict(self):
        consumption = {
            'id': self.id,
            'user_id': self.user_id,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'start_time': utils.dec2str(self.start_time),
            'end_time': utils.dec2str(self.end_time),
            'rate': utils.dec2str(self.rate),
            'cost': utils.dec2str(self.cost),
            'metadata': self.metadata,
        }
        return consumption
