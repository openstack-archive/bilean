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
from bilean.rules import base as rule_base


class Policy(object):
    """Policy object contains all policy operations"""

    def __init__(self, name, **kwargs):
        self.name = name

        self.id = kwargs.get('id')
        self.is_default = kwargs.get('is_default', False)
        # rules schema like [{'id': 'xxx', 'type': 'os.nova.server'}]
        self.rules = kwargs.get('rules', [])
        self.metadata = kwargs.get('metadata')

        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.deleted_at = kwargs.get('deleted_at')

    def store(self, context):
        """Store the policy record into database table."""

        values = {
            'name': self.name,
            'rules': self.rules,
            'is_default': self.is_default,
            'meta_data': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'deleted_at': self.deleted_at,
        }

        if self.id:
            db_api.policy_update(context, self.id, values)
        else:
            policy = db_api.policy_create(context, values)
            self.id = policy.id

        return self.id

    @classmethod
    def _from_db_record(cls, record):
        '''Construct a policy object from database record.

        :param record: a DB policy object that contains all fields;
        '''
        kwargs = {
            'id': record.id,
            'rules': record.rules,
            'is_default': record.is_default,
            'metadata': record.meta_data,
            'created_at': record.created_at,
            'updated_at': record.updated_at,
            'deleted_at': record.deleted_at,
        }

        return cls(record.name, **kwargs)

    @classmethod
    def load(cls, context, policy_id=None, policy=None, show_deleted=False):
        '''Retrieve a policy from database.'''
        if policy is None:
            policy = db_api.policy_get(context, policy_id,
                                       show_deleted=show_deleted)
            if policy is None:
                raise exception.PolicyNotFound(policy=policy_id)

        return cls._from_db_record(policy)

    @classmethod
    def load_all(cls, context, limit=None, marker=None,
                 sort_keys=None, sort_dir=None,
                 filters=None, show_deleted=False):
        '''Retrieve all policies of from database.'''

        records = db_api.policy_get_all(context,
                                        limit=limit, marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir,
                                        filters=filters,
                                        show_deleted=show_deleted)

        return [cls._from_db_record(record) for record in records]

    def find_rule(self, context, rtype):
        '''Find the exact rule from self.rules by rtype'''

        for rule in self.rules:
            if rtype == rule['type'].split('-')[0]:
                return rule_base.Rule.load(context, rule_id=rule['id'])

        raise exception.RuleNotFound(rule_type=rtype)

    def to_dict(self):
        policy_dict = {
            'id': self.id,
            'name': self.name,
            'rules': self.rules,
            'is_default': self.is_default,
            'metadata': self.metadata,
            'created_at': utils.format_time(self.created_at),
            'updated_at': utils.format_time(self.updated_at),
            'deleted_at': utils.format_time(self.deleted_at),
        }
        return policy_dict

    def do_delete(self, context):
        db_api.policy_delete(context, self.id)
        return True
