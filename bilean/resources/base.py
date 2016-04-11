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
from bilean.engine import consumption as consumption_mod
from bilean.engine import environment

from oslo_utils import timeutils


class Resource(object):
    """A resource is an object that refers to a physical resource.

    The resource comes from other openstack component such as nova,
    cinder, neutron and so on, it can be an instance or volume or
    something else.
    """

    ALLOW_DELAY_TIME = 10

    def __new__(cls, id, user_id, res_type, properties, **kwargs):
        """Create a new resource of the appropriate class.

        :param id: The resource ID comes same as the real resource.
        :param user_id: The user ID the resource belongs to.
        :param properties: The properties of resource.
        :param dict kwargs: Other keyword arguments for the resource.
        """
        if cls != Resource:
            ResourceClass = cls
        else:
            ResourceClass = environment.global_env().get_resource(res_type)

        return super(Resource, cls).__new__(ResourceClass)

    def __init__(self, id, user_id, resource_type, properties, **kwargs):
        self.id = id
        self.user_id = user_id
        self.resource_type = resource_type
        self.properties = properties

        self.rule_id = kwargs.get('rule_id')
        self.rate = kwargs.get('rate', 0)
        self.last_bill = kwargs.get('last_bill')

        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.deleted_at = kwargs.get('deleted_at')

        # Properties pass to user to help settle account, not store to db
        self.delta_rate = 0
        self.delayed_cost = 0
        self.consumption = None

    def store(self, context):
        """Store the resource record into database table."""

        values = {
            'user_id': self.user_id,
            'resource_type': self.resource_type,
            'properties': self.properties,
            'rule_id': self.rule_id,
            'rate': self.rate,
            'last_bill': self.last_bill,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'deleted_at': self.deleted_at,
        }

        if self.created_at:
            self._update(context, values)
        else:
            values.update(id=self.id)
            self._create(context, values)

        return self.id

    def delete(self, context, soft_delete=True):
        '''Delete resource from db.'''
        self._delete(context, soft_delete=soft_delete)

    def _create(self, context, values):
        self.delta_rate = self.rate
        if self.delta_rate == 0:
            resource = db_api.resource_create(context, values)
            self.created_at = resource.created_at
            return

        now = timeutils.utcnow()
        self.last_bill = now
        create_time = self.properties.get('created_at')
        if create_time is not None:
            created_at = timeutils.parse_strtime(create_time)
            delayed_seconds = (now - created_at).total_seconds()
            # Engine handle resource creation is delayed because of something,
            # we suppose less than ALLOW_DELAY_TIME is acceptable.
            if delayed_seconds > self.ALLOW_DELAY_TIME:
                self.delayed_cost = self.delta_rate * delayed_seconds
                self.last_bill = created_at

        values.update(last_bill=self.last_bill)
        resource = db_api.resource_create(context, values)
        self.created_at = resource.created_at

    def _update(self, context, values):
        if self.delta_rate == 0:
            db_api.resource_update(context, self.id, values)
            return

        update_time = self.properties.get('updated_at')
        now = timeutils.utcnow()
        updated_at = now
        if update_time is not None:
            updated_at = timeutils.parse_strtime(update_time)
            delayed_seconds = (now - updated_at).total_seconds()
            # Engine handle resource update is delayed because of something,
            # we suppose less than ALLOW_DELAY_TIME is acceptable.
            if delayed_seconds > self.ALLOW_DELAY_TIME:
                self.delayed_cost = self.delta_rate * delayed_seconds

        # Generate consumption between lass bill and update time
        old_rate = self.rate - self.delta_rate
        cost = (updated_at - self.last_bill).total_seconds() * old_rate
        params = {'resource_id': self.id,
                  'resource_type': self.resource_type,
                  'start_time': self.last_bill,
                  'end_time': updated_at,
                  'rate': old_rate,
                  'cost': cost,
                  'metadata': {'cause': 'Resource update'}}
        self.consumption = consumption_mod.Consumption(self.user_id, **params)

        self.last_bill = updated_at
        values.update(last_bill=updated_at)
        db_api.resource_update(context, self.id, values)

    def _delete(self, context, soft_delete=True):
        self.delta_rate = - self.rate
        if self.delta_rate == 0:
            db_api.resource_delete(context, self.id, soft_delete=soft_delete)
            return

        delete_time = self.properties.get('deleted_at')
        now = timeutils.utcnow()
        deleted_at = now
        if delete_time is not None:
            deleted_at = timeutils.parse_strtime(delete_time)
            delayed_seconds = (now - deleted_at).total_seconds()
            # Engine handle resource deletion is delayed because of something,
            # we suppose less than ALLOW_DELAY_TIME is acceptable.
            if delayed_seconds > self.ALLOW_DELAY_TIME:
                self.delayed_cost = self.delta_rate * delayed_seconds

        # Generate consumption between lass bill and delete time
        cost = (deleted_at - self.last_bill).total_seconds() * self.rate
        params = {'resource_id': self.id,
                  'resource_type': self.resource_type,
                  'start_time': self.last_bill,
                  'end_time': deleted_at,
                  'rate': self.rate,
                  'cost': cost,
                  'metadata': {'cause': 'Resource deletion'}}
        self.consumption = consumption_mod.Consumption(self.user_id, **params)

        self.last_bill = deleted_at
        db_api.resource_delete(context, self.id, soft_delete=soft_delete)

    @classmethod
    def _from_db_record(cls, record):
        '''Construct a resource object from database record.

        :param record: a DB user object that contains all fields;
        '''
        kwargs = {
            'rule_id': record.rule_id,
            'rate': record.rate,
            'last_bill': record.last_bill,
            'created_at': record.created_at,
            'updated_at': record.updated_at,
            'deleted_at': record.deleted_at,
        }

        return cls(record.id, record.user_id, record.resource_type,
                   record.properties, **kwargs)

    @classmethod
    def load(cls, context, resource_id=None, resource=None,
             show_deleted=False, project_safe=True):
        '''Retrieve a resource from database.'''
        if context.is_admin:
            project_safe = False
        if resource is None:
            resource = db_api.resource_get(context, resource_id,
                                           show_deleted=show_deleted,
                                           project_safe=project_safe)
            if resource is None:
                raise exception.ResourceNotFound(resource=resource_id)

        return cls._from_db_record(resource)

    @classmethod
    def load_all(cls, context, user_id=None, show_deleted=False,
                 limit=None, marker=None, sort_keys=None, sort_dir=None,
                 filters=None, project_safe=True):
        '''Retrieve all users from database.'''

        records = db_api.resource_get_all(context, user_id=user_id,
                                          show_deleted=show_deleted,
                                          limit=limit, marker=marker,
                                          sort_keys=sort_keys,
                                          sort_dir=sort_dir,
                                          filters=filters,
                                          project_safe=project_safe)

        return [cls._from_db_record(record) for record in records]

    @classmethod
    def from_dict(cls, values):
        id = values.pop('id', None)
        user_id = values.pop('user_id', None)
        resource_type = values.pop('resource_type', None)
        properties = values.pop('properties', {})
        return cls(id, user_id, resource_type, properties, **values)

    def to_dict(self):
        resource_dict = {
            'id': self.id,
            'user_id': self.user_id,
            'resource_type': self.resource_type,
            'properties': self.properties,
            'rule_id': self.rule_id,
            'rate': self.rate,
            'last_bill': utils.format_time(self.last_bill),
            'created_at': utils.format_time(self.created_at),
            'updated_at': utils.format_time(self.updated_at),
            'deleted_at': utils.format_time(self.deleted_at),
        }
        return resource_dict

    @classmethod
    def do_check(cls, context, user):
        '''Communicate with other services and check user's resources.

        This would be a period job of user to check if there are any missing
        actions, and then make correction.
        '''

        return NotImplemented

    def do_delete(self, context, ignore_missing=True, timeout=None):
        '''Delete resource from other services.'''

        return NotImplemented
