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
import six

from bilean.common import exception
from bilean.common import schema
from bilean.common import utils as common_utils
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

    def test_load(self):
        rule = self._create_db_rule()
        result = rule_base.Rule.load(self.context, rule.id)

        self.assertEqual(rule.id, result.id)
        self.assertEqual(rule.name, result.name)
        self.assertEqual(rule.type, result.type)
        self.assertEqual(rule.spec, result.spec)
        self.assertEqual(rule.meta_data, result.metadata)
        self.assertEqual({'key1': 'value1', 'key2': 2}, result.properties)

        self.assertEqual(rule.created_at, result.created_at)
        self.assertEqual(rule.updated_at, result.updated_at)

    def test_load_not_found(self):
        ex = self.assertRaises(exception.RuleNotFound,
                               rule_base.Rule.load,
                               self.context, 'fake-rule', None)
        self.assertEqual('The rule (fake-rule) could not be found.',
                         six.text_type(ex))

        ex = self.assertRaises(exception.RuleNotFound,
                               rule_base.Rule.load,
                               self.context, None, None)
        self.assertEqual('The rule (None) could not be found.',
                         six.text_type(ex))

    def test_load_all(self):
        result = rule_base.Rule.load_all(self.context)
        self.assertEqual([], list(result))

        rule1 = self._create_db_rule(name='rule-1', id='ID1')
        rule2 = self._create_db_rule(name='rule-2', id='ID2')

        result = rule_base.Rule.load_all(self.context)
        rules = list(result)
        self.assertEqual(2, len(rules))
        self.assertEqual(rule1.id, rules[0].id)
        self.assertEqual(rule2.id, rules[1].id)

    @mock.patch.object(db_api, 'rule_get_all')
    def test_load_all_with_params(self, mock_get_all):
        mock_get_all.return_value = []

        res = list(rule_base.Rule.load_all(self.context))
        self.assertEqual([], res)
        mock_get_all.assert_called_once_with(self.context, limit=None,
                                             marker=None, sort_keys=None,
                                             sort_dir=None, filters=None,
                                             show_deleted=False)
        mock_get_all.reset_mock()

        res = list(rule_base.Rule.load_all(self.context, limit=1,
                                           marker='MARKER',
                                           sort_keys=['K1'],
                                           sort_dir='asc',
                                           filters={'name': 'fake-name'}))
        self.assertEqual([], res)
        mock_get_all.assert_called_once_with(self.context, limit=1,
                                             marker='MARKER',
                                             sort_keys=['K1'],
                                             sort_dir='asc',
                                             filters={'name': 'fake-name'},
                                             show_deleted=False)

    def test_delete(self):
        rule = self._create_db_rule()
        rule_id = rule.id

        res = rule_base.Rule.delete(self.context, rule_id)
        self.assertIsNone(res)
        self.assertRaises(exception.RuleNotFound,
                          rule_base.Rule.load,
                          self.context, rule_id, None)

    def test_delete_not_found(self):
        result = rule_base.Rule.delete(self.context, 'fake-rule')
        self.assertIsNone(result)

    def test_store_for_create(self):
        rule = self._create_rule('test-rule')
        self.assertIsNone(rule.id)

        rule_id = rule.store(self.context)
        self.assertIsNotNone(rule_id)
        self.assertEqual(rule_id, rule.id)

        result = db_api.rule_get(self.context, rule_id)

        self.assertIsNotNone(result)
        self.assertEqual('test-rule', result.name)
        self.assertEqual(rule_id, result.id)
        self.assertEqual(rule.type, result.type)
        self.assertEqual(rule.spec, result.spec)
        self.assertEqual(rule.metadata, result.meta_data)

        self.assertIsNotNone(result.created_at)
        self.assertIsNone(result.updated_at)

    def test_store_for_update(self):
        rule = self._create_rule('test-rule')
        self.assertIsNone(rule.id)
        rule_id = rule.store(self.context)
        self.assertIsNotNone(rule_id)
        self.assertEqual(rule_id, rule.id)

        rule.name = 'test-rule-1'
        rule.metadata = {'key': 'value'}

        new_id = rule.store(self.context)
        self.assertEqual(rule_id, new_id)

        result = db_api.rule_get(self.context, rule_id)
        self.assertIsNotNone(result)
        self.assertEqual('test-rule-1', result.name)
        self.assertEqual({'key': 'value'}, result.meta_data)
        self.assertIsNotNone(rule.created_at)
        self.assertIsNotNone(rule.updated_at)

    def test_to_dict(self):
        rule = self._create_rule('test-rule')
        rule_id = rule.store(self.context)
        self.assertIsNotNone(rule_id)
        expected = {
            'id': rule_id,
            'name': rule.name,
            'type': rule.type,
            'spec': rule.spec,
            'metadata': rule.metadata,
            'created_at': common_utils.format_time(rule.created_at),
            'updated_at': None,
            'deleted_at': None,
        }

        result = rule_base.Rule.load(self.context, rule_id=rule.id)
        self.assertEqual(expected, result.to_dict())

    def test_get_schema(self):
        expected = {
            'key1': {
                'default': 'value1',
                'description': 'First key',
                'readonly': False,
                'required': False,
                'type': 'String'
            },
            'key2': {
                'description': 'Second key',
                'readonly': False,
                'required': True,
                'type': 'Integer'
            },
        }
        res = DummyRule.get_schema()
        self.assertEqual(expected, res)
