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

import mock
from oslo_utils import encodeutils
import six

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import schema
from bilean.db import api as db_api
from bilean.engine import environment
from bilean.rules import base as rule_base
from bilean.tests.common import base
from bilean.tests.common import utils


class DummyRule(rule_base.Rule):
    VERSION = '1.0'

    properties_schema = {
        'key1': schema.String(
            'First key',
            default='value1'
        ),
        'key2': schema.Integer(
            'Second key',
            required=True,
        ),
    }

    def __init__(self, name, spec, **kwargs):
        super(DummyRule, self).__init__(name, spec, **kwargs)


class TestRuleBase(base.BileanTestCase):

    def setUp(self):
        super(TestRuleBase, self).setUp()

        self.context = utils.dummy_context()
        environment.global_env().register_rule('bilean.rule.dummy', DummyRule)
        self.spec = {
            'type': 'bilean.rule.dummy',
            'version': '1.0',
            'properties': {
                'key1': 'value1',
                'key2': 2,
            }
        }

    def _create_rule(self, rule_name, rule_id=None):
        rule = rule_base.Rule(rule_name, self.spec)
        if rule_id:
            rule.id = rule_id

        return rule

    def _create_db_rule(self, **kwargs):
        values = {
            'name': 'test-rule',
            'type': 'bilean.rule.dummy-1.0',
            'spec': self.spec,
            'metadata': {}
        }

        values.update(kwargs)
        return db_api.rule_create(self.context, values)

    def test_init(self):
        name = utils.random_name()
        rule = self._create_rule(name)

        self.assertIsNone(rule.id)
        self.assertEqual(name, rule.name)
        self.assertEqual('bilean.rule.dummy-1.0', rule.type)
        self.assertEqual(self.spec, rule.spec)
        self.assertEqual({}, rule.metadata)
        self.assertIsNone(rule.created_at)
        self.assertIsNone(rule.updated_at)
        self.assertIsNone(rule.deleted_at)

        spec_data = rule.spec_data
        self.assertEqual('bilean.rule.dummy', spec_data['type'])
        self.assertEqual('1.0', spec_data['version'])
        self.assertEqual({'key1': 'value1', 'key2': 2},
                         spec_data['properties'])
        self.assertEqual({'key1': 'value1', 'key2': 2}, rule.properties)

    def test_rule_type_not_found(self):
        bad_spec = {
            'type': 'bad-type',
            'version': '1.0',
            'properties': '',
        }

        self.assertRaises(exception.RuleTypeNotFound,
                          rule_base.Rule,
                          'test-rule', bad_spec)
