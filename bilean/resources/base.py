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
from bilean.engine import environment


class Resource(object):
    """A resource is an object that refers to a physical resource.

    The resource comes from other openstack component such as nova,
    cinder, neutron and so on, it can be an instance or volume or
    something else.
    """

    def __new__(cls, id, user_id, res_type, properties, **kwargs):
        """Create a new resource of the appropriate class."""
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
        self.d_rate = 0

        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.deleted_at = kwargs.get('deleted_at')

    def store(self, context):
        """Store the resource record into database table."""

        values = {
            'user_id': self.user_id,
            'resource_type': self.resource_type,
            'properties': self.properties,
            'rule_id': self.rule_id,
            'rate': self.rate,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'deleted_at': self.deleted_at,
        }

        if self.created_at:
            db_api.resource_update(context, self.id, values)
        else:
            values.update(id=self.id)
            resource = db_api.resource_create(context, values)
            self.created_at = resource.created_at

        return self.id

    def delete(self, context):
        '''Delete resource from db.'''
        db_api.resource_delete(context, self.id)

    @classmethod
    def _from_db_record(cls, record):
        '''Construct a resource object from database record.

        :param record: a DB user object that contains all fields;
        '''
        kwargs = {
            'rule_id': record.rule_id,
            'rate': record.rate,
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

    def to_dict(self):
        resource_dict = {
            'id': self.id,
            'user_id': self.user_id,
            'resource_type': self.resource_type,
            'properties': self.properties,
            'rule_id': self.rule_id,
            'rate': self.rate,
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
