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

import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import schema
from bilean.common import utils
from bilean.db import api as db_api
from bilean.engine import consumption as consumption_mod
from bilean.engine import environment

wallclock = time.time
LOG = logging.getLogger(__name__)


resource_opts = [
    cfg.StrOpt('notifications_topic', default="notifications",
               help="The default messaging notifications topic"),
]

CONF = cfg.CONF
CONF.register_opts(resource_opts, group='resource_plugin')


class Plugin(object):
    '''Base class for plugins.'''

    RuleClass = None
    ResourceClass = None
    notification_exchanges = []

    @classmethod
    def get_notification_topics_exchanges(cls):
        """Returns a list of (topic,exchange), (topic,exchange)..)."""

        return [(CONF.resource_plugin.notifications_topic, exchange)
                for exchange in cls.notification_exchanges]


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
            PluginClass = environment.global_env().get_plugin(type_name)
            RuleClass = PluginClass.RuleClass

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

        self.id = kwargs.get('id')
        self.type = kwargs.get('type', '%s-%s' % (type_name, version))

        self.metadata = kwargs.get('metadata', {})

        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.deleted_at = kwargs.get('deleted_at')

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
    def load_all(cls, context, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, show_deleted=False):
        '''Retrieve all rules from database.'''

        records = db_api.rule_get_all(context, limit=limit,
                                      marker=marker,
                                      sort_keys=sort_keys,
                                      sort_dir=sort_dir,
                                      filters=filters,
                                      show_deleted=show_deleted)

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


class Resource(object):
    """A resource is an object that refers to a physical resource.

    The resource comes from other openstack component such as nova,
    cinder, neutron and so on, it can be an instance or volume or
    something else.
    """

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
            PluginClass = environment.global_env().get_plugin(res_type)
            ResourceClass = PluginClass.ResourceClass

        return super(Resource, cls).__new__(ResourceClass)

    def __init__(self, id, user_id, resource_type, properties, **kwargs):
        self.id = id
        self.user_id = user_id
        self.resource_type = resource_type
        self.properties = properties

        self.rule_id = kwargs.get('rule_id')
        self.rate = utils.make_decimal(kwargs.get('rate', 0))
        self.last_bill = utils.make_decimal(kwargs.get('last_bill', 0))

        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.deleted_at = kwargs.get('deleted_at')

        # Properties pass to user to help settle account, not store to db
        self.delta_rate = 0
        self.consumption = None

    def store(self, context):
        """Store the resource record into database table."""

        values = {
            'user_id': self.user_id,
            'resource_type': self.resource_type,
            'properties': self.properties,
            'rule_id': self.rule_id,
            'rate': utils.format_decimal(self.rate),
            'last_bill': utils.format_decimal(self.last_bill),
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

        self.last_bill = utils.make_decimal(wallclock())
        create_time = self.properties.get('created_at')
        if create_time is not None:
            sec = utils.format_time_to_seconds(create_time)
            self.last_bill = utils.make_decimal(sec)

        values.update(last_bill=utils.format_decimal(self.last_bill))
        resource = db_api.resource_create(context, values)
        self.created_at = resource.created_at

    def _update(self, context, values):
        if self.delta_rate == 0:
            db_api.resource_update(context, self.id, values)
            return

        update_time = self.properties.get('updated_at')
        updated_at = utils.make_decimal(wallclock())
        if update_time is not None:
            sec = utils.format_time_to_seconds(update_time)
            updated_at = utils.make_decimal(sec)

        # Generate consumption between lass bill and update time
        old_rate = self.rate - self.delta_rate
        cost = (updated_at - self.last_bill) * old_rate
        params = {'resource_id': self.id,
                  'resource_type': self.resource_type,
                  'start_time': self.last_bill,
                  'end_time': updated_at,
                  'rate': old_rate,
                  'cost': cost,
                  'metadata': {'cause': 'Resource update'}}
        self.consumption = consumption_mod.Consumption(self.user_id, **params)

        self.last_bill = updated_at
        values.update(last_bill=utils.format_decimal(updated_at))
        db_api.resource_update(context, self.id, values)

    def _delete(self, context, soft_delete=True):
        self.delta_rate = - self.rate
        if self.delta_rate == 0:
            db_api.resource_delete(context, self.id, soft_delete=soft_delete)
            return

        delete_time = self.properties.get('deleted_at')
        deleted_at = utils.make_decimal(wallclock())
        if delete_time is not None:
            sec = utils.format_time_to_seconds(delete_time)
            deleted_at = utils.make_decimal(sec)

        # Generate consumption between lass bill and delete time
        cost = (deleted_at - self.last_bill) * self.rate
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
            'rate': utils.dec2str(self.rate),
            'last_bill': utils.dec2str(self.last_bill),
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
