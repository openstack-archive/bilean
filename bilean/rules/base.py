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

from oslo_log import log as logging
from oslo_utils import timeutils

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import schema
from bilean.common import utils
from bilean.db import api as db_api
from bilean.engine import environment

LOG = logging.getLogger(__name__)


class Rule(object):
    '''Base class for rules.'''

    KEYS = (
        TYPE, VERSION, PROPERTIES,
    ) = (
        'type', 'version', 'properties',
    )

    spec_schema = {
        TYPE: schema.String(
            _('Name of the rule type.'),
            required=True,
        ),
        VERSION: schema.String(
            _('Version number of the rule type.'),
            required=True,
        ),
        PROPERTIES: schema.Map(
            _('Properties for the rule.'),
            required=True,
        )
    }

    properties_schema = {}

    def __new__(cls, name, spec, **kwargs):
        """Create a new rule of the appropriate class.

        :param name: The name for the rule.
        :param spec: A dictionary containing the spec for the rule.
        :param kwargs: Keyword arguments for rule creation.
        :returns: An instance of a specific sub-class of Rule.
        """
        type_name, version = schema.get_spec_version(spec)

        if cls != Rule:
            RuleClass = cls
        else:
            RuleClass = environment.global_env().get_rule(type_name)

        return super(Rule, cls).__new__(RuleClass)

    def __init__(self, name, spec, **kwargs):
        """Initialize a rule instance.

        :param name: A string that specifies the name for the rule.
        :param spec: A dictionary containing the detailed rule spec.
        :param kwargs: Keyword arguments for initializing the rule.
        :returns: An instance of a specific sub-class of Rule.
        """

        type_name, version = schema.get_spec_version(spec)

        self.name = name
        self.spec = spec

        self.id = kwargs.get('id', None)
        self.type = kwargs.get('type', '%s-%s' % (type_name, version))

        self.metadata = kwargs.get('metadata', {})

        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)
        self.deleted_at = kwargs.get('deleted_at', None)

        self.spec_data = schema.Spec(self.spec_schema, self.spec)
        self.properties = schema.Spec(self.properties_schema,
                                      self.spec.get(self.PROPERTIES, {}))

    @classmethod
    def from_db_record(cls, record):
        '''Construct a rule object from database record.

        :param record: a DB Profle object that contains all required fields.
        '''
        kwargs = {
            'id': record.id,
            'type': record.type,
            'metadata': record.meta_data,
            'created_at': record.created_at,
            'updated_at': record.updated_at,
            'deleted_at': record.deleted_at,
        }

        return cls(record.name, record.spec, **kwargs)

    @classmethod
    def load(cls, context, rule_id=None, rule=None, show_deleted=False):
        '''Retrieve a rule object from database.'''
        if rule is None:
            rule = db_api.rule_get(context, rule_id,
                                   show_deleted=show_deleted)
            if rule is None:
                raise exception.RuleNotFound(rule=rule_id)

        return cls.from_db_record(rule)

    @classmethod
    def load_all(cls, context, show_deleted=False, limit=None,
                 marker=None, sort_keys=None, sort_dir=None,
                 filters=None):
        '''Retrieve all rules from database.'''

        records = db_api.rule_get_all(context, show_deleted=show_deleted,
                                      limit=limit, marker=marker,
                                      sort_keys=sort_keys, sort_dir=sort_dir,
                                      filters=filters)

        return [cls.from_db_record(record) for record in records]

    @classmethod
    def delete(cls, context, rule_id):
        db_api.rule_delete(context, rule_id)

    def store(self, context):
        '''Store the rule into database and return its ID.'''
        timestamp = timeutils.utcnow()

        values = {
            'name': self.name,
            'type': self.type,
            'spec': self.spec,
            'meta_data': self.metadata,
        }

        if self.id:
            self.updated_at = timestamp
            values['updated_at'] = timestamp
            db_api.rule_update(context, self.id, values)
        else:
            self.created_at = timestamp
            values['created_at'] = timestamp
            rule = db_api.rule_create(context, values)
            self.id = rule.id

        return self.id

    def validate(self):
        '''Validate the schema and the data provided.'''
        # general validation
        self.spec_data.validate()
        self.properties.validate()

    @classmethod
    def get_schema(cls):
        return dict((name, dict(schema))
                    for name, schema in cls.properties_schema.items())

    def get_price(self, resource):
        '''For subclass to override.'''

        return NotImplemented

    def do_delete(self, obj):
        '''For subclass to override.'''

        return NotImplemented

    def do_update(self, obj, new_rule, **params):
        '''For subclass to override.'''

        return NotImplemented

    def to_dict(self):
        rule_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'spec': self.spec,
            'metadata': self.metadata,
            'created_at': utils.format_time(self.created_at),
            'updated_at': utils.format_time(self.updated_at),
            'deleted_at': utils.format_time(self.deleted_at),
        }
        return rule_dict

    @classmethod
    def from_dict(cls, **kwargs):
        type_name = kwargs.pop('type')
        name = kwargs.pop('name')
        return cls(type_name, name, kwargs)
