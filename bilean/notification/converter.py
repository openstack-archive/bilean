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

import fnmatch
import jsonpath_rw
import os
import six
import yaml

from bilean.common.i18n import _
from bilean.common.i18n import _LI
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

resource_definition_opts = [
    cfg.StrOpt('definitions_cfg_file',
               default="resource_definitions.yaml",
               help="Configuration file for resource definitions."
               ),
    cfg.BoolOpt('drop_unmatched_notifications',
                default=True,
                help='Drop notifications if no resource definition matches. '
                '(Otherwise, we convert them with just the default traits)'),

]

resource_group = cfg.OptGroup('resource_definition')
cfg.CONF.register_group(resource_group)
cfg.CONF.register_opts(resource_definition_opts, group=resource_group)

LOG = logging.getLogger(__name__)


def get_config_file():
    config_file = cfg.CONF.resource_definition.definitions_cfg_file
    if not os.path.exists(config_file):
        config_file = cfg.CONF.find_file(config_file)
    return config_file


def setup_resources():
    """Setup the resource definitions from yaml config file."""
    config_file = get_config_file()
    if config_file is not None:
        LOG.debug(_("Resource Definitions configuration file: %s") %
                  config_file)

        with open(config_file) as cf:
            config = cf.read()

        try:
            resources_config = yaml.safe_load(config)
        except yaml.YAMLError as err:
            if hasattr(err, 'problem_mark'):
                mark = err.problem_mark
                errmg = (_("Invalid YAML syntax in Resource Definitions "
                           "file %(file)s at line: %(line)s, column: "
                           "%(column)s.") % dict(file=config_file,
                                                 line=mark.line + 1,
                                                 column=mark.column + 1))
            else:
                errmg = (_("YAML error reading Resource Definitions file "
                           "%(file)s") % dict(file=config_file))
            LOG.error(errmg)
            raise

    else:
        LOG.debug(_("No Resource Definitions configuration file found!"
                  " Using default config."))
        resources_config = []

    LOG.info(_LI("Resource Definitions: %s"), resources_config)

    allow_drop = cfg.CONF.resource_definition.drop_unmatched_notifications
    return NotificationResourcesConverter(resources_config,
                                          add_catchall=not allow_drop)


class NotificationResourcesConverter(object):
    """Notification Resource Converter."""

    def __init__(self, resources_config, add_catchall=True):
        self.definitions = [
            EventDefinition(event_def)
            for event_def in reversed(resources_config)]
        if add_catchall and not any(d.is_catchall for d in self.definitions):
            event_def = dict(event_type='*', resources={})
            self.definitions.append(EventDefinition(event_def))

    def to_resources(self, notification_body):
        event_type = notification_body['event_type']
        edef = None
        for d in self.definitions:
            if d.match_type(event_type):
                edef = d
                break

        if edef is None:
            msg = (_('Dropping Notification %(type)s')
                   % dict(type=event_type))
            if cfg.CONF.resource_definition.drop_unmatched_notifications:
                LOG.debug(msg)
            else:
                # If drop_unmatched_notifications is False, this should
                # never happen. (mdragon)
                LOG.error(msg)
            return None

        return edef.to_resources(notification_body)


class EventDefinition(object):

    def __init__(self, definition_cfg):
        self._included_types = []
        self._excluded_types = []
        self.cfg = definition_cfg

        try:
            event_type = definition_cfg['event_type']
            self.resources = [ResourceDefinition(resource_def)
                              for resource_def in definition_cfg['resources']]
        except KeyError as err:
            raise EventDefinitionException(
                _("Required field %s not specified") % err.args[0], self.cfg)

        if isinstance(event_type, six.string_types):
            event_type = [event_type]

        for t in event_type:
            if t.startswith('!'):
                self._excluded_types.append(t[1:])
            else:
                self._included_types.append(t)

        if self._excluded_types and not self._included_types:
            self._included_types.append('*')

    def included_type(self, event_type):
        for t in self._included_types:
            if fnmatch.fnmatch(event_type, t):
                return True
        return False

    def excluded_type(self, event_type):
        for t in self._excluded_types:
            if fnmatch.fnmatch(event_type, t):
                return True
        return False

    def match_type(self, event_type):
        return (self.included_type(event_type) and
                not self.excluded_type(event_type))

    @property
    def is_catchall(self):
        return '*' in self._included_types and not self._excluded_types

    def to_resources(self, notification_body):
        resources = []
        for resource in self.resources:
            resources.append(resource.to_resource(notification_body))
        return resources


class ResourceDefinition(object):

    DEFAULT_TRAITS = dict(
        user_id=dict(type='string', fields='payload.tenant_id'),
    )

    def __init__(self, definition_cfg):
        self.traits = dict()

        try:
            self.resource_type = definition_cfg['resource_type']
            traits = definition_cfg['traits']
        except KeyError as err:
            raise EventDefinitionException(
                _("Required field %s not specified") % err.args[0], self.cfg)

        for trait_name in self.DEFAULT_TRAITS:
            self.traits[trait_name] = TraitDefinition(
                trait_name,
                self.DEFAULT_TRAITS[trait_name])
        for trait_name in traits:
            self.traits[trait_name] = TraitDefinition(
                trait_name,
                traits[trait_name])

    def to_resource(self, notification_body):
        traits = (self.traits[t].to_trait(notification_body)
                  for t in self.traits)
        # Only accept non-None value traits ...
        traits = [trait for trait in traits if trait is not None]
        resource = {"resource_type": self.resource_type}
        for trait in traits:
            resource.update(trait)
        if 'created_at' not in resource:
            resource['created_at'] = timeutils.utcnow()
        return resource


class TraitDefinition(object):

    def __init__(self, name, trait_cfg):
        self.cfg = trait_cfg
        self.name = name

        type_name = trait_cfg.get('type', 'string')

        if 'fields' not in trait_cfg:
            raise EventDefinitionException(
                _("Required field in trait definition not specified: "
                  "'%s'") % 'fields',
                self.cfg)

        fields = trait_cfg['fields']
        if not isinstance(fields, six.string_types):
            # NOTE(mdragon): if not a string, we assume a list.
            if len(fields) == 1:
                fields = fields[0]
            else:
                fields = '|'.join('(%s)' % path for path in fields)
        try:
            self.fields = jsonpath_rw.parse(fields)
        except Exception as e:
            raise EventDefinitionException(
                _("Parse error in JSONPath specification "
                  "'%(jsonpath)s' for %(trait)s: %(err)s")
                % dict(jsonpath=fields, trait=name, err=e), self.cfg)
        self.trait_type = type_name
        if self.trait_type is None:
            raise EventDefinitionException(
                _("Invalid trait type '%(type)s' for trait %(trait)s")
                % dict(type=type_name, trait=name), self.cfg)

    def to_trait(self, notification_body):
        values = [match for match in self.fields.find(notification_body)
                  if match.value is not None]

        value = values[0].value if values else None

        if value is None:
            return None

        if self.trait_type != 'string' and value == '':
            return None

        if self.trait_type is "int":
            value = int(value)
        elif self.trait_type is "float":
            value = float(value)
        elif self.trait_type is "string":
            value = str(value)
        return {self.name: value}


class EventDefinitionException(Exception):
    def __init__(self, message, definition_cfg):
        super(EventDefinitionException, self).__init__(message)
        self.definition_cfg = definition_cfg

    def __str__(self):
        return '%s %s: %s' % (self.__class__.__name__,
                              self.definition_cfg, self.message)


def list_opts():
    yield resource_group.name, resource_definition_opts
