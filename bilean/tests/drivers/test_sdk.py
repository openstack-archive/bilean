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
from openstack import connection
from oslo_serialization import jsonutils
from requests import exceptions as req_exc
import six

from bilean.common import exception as bilean_exc
from bilean.drivers.openstack import sdk
from bilean.tests.common import base


class OpenStackSDKTest(base.BileanTestCase):

    def setUp(self):
        super(OpenStackSDKTest, self).setUp()

    def test_parse_exception_http_exception_with_details(self):
        details = jsonutils.dumps({
            'error': {
                'code': 404,
                'message': 'Resource BAR is not found.'
            }
        })
        raw = sdk.exc.ResourceNotFound('A message', details=details,
                                       http_status=404)
        ex = self.assertRaises(bilean_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(500, ex.code)
        self.assertEqual('Resource BAR is not found.', six.text_type(ex))
        # key name is not 'error' case
        details = jsonutils.dumps({
            'forbidden': {
                'code': 403,
                'message': 'Quota exceeded for instances.'
            }
        })
        raw = sdk.exc.ResourceNotFound('A message', details=details,
                                       http_status=403)
        ex = self.assertRaises(bilean_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(403, ex.code)
        self.assertEqual('Quota exceeded for instances.', six.text_type(ex))

    def test_parse_exception_http_exception_no_details(self):
        details = "An error message"

        raw = sdk.exc.ResourceNotFound('A message.', details=details,
                                       http_status=404)
        ex = self.assertRaises(bilean_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(500, ex.code)
        self.assertEqual('A message.', six.text_type(ex))

    def test_parse_exception_http_exception_code_displaced(self):
        details = jsonutils.dumps({
            'code': 400,
            'error': {
                'message': 'Resource BAR is in error state.'
            }
        })

        raw = sdk.exc.HttpException(message='A message.', details=details,
                                    http_status=400)
        ex = self.assertRaises(bilean_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(400, ex.code)
        self.assertEqual('Resource BAR is in error state.', six.text_type(ex))

    def test_parse_exception_sdk_exception(self):
        raw = sdk.exc.InvalidResponse('INVALID')

        ex = self.assertRaises(bilean_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(500, ex.code)
        self.assertEqual('InvalidResponse', six.text_type(ex))

    def test_parse_exception_request_exception(self):
        raw = req_exc.HTTPError(401, 'ERROR')

        ex = self.assertRaises(bilean_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(401, ex.code)
        self.assertEqual('[Errno 401] ERROR', ex.message)

    def test_parse_exception_other_exceptions(self):
        raw = Exception('Unknown Error')

        ex = self.assertRaises(bilean_exc.InternalError,
                               sdk.parse_exception, raw)

        self.assertEqual(500, ex.code)
        self.assertEqual('Unknown Error', six.text_type(ex))

    def test_translate_exception_wrapper(self):

        test_func = mock.Mock()
        test_func.__name__ = 'test_func'

        res = sdk.translate_exception(test_func)
        self.assertEqual('function', res.__class__.__name__)

    def test_translate_exception_with_exception(self):

        @sdk.translate_exception
        def test_func(driver):
            raise(Exception('test exception'))

        error = bilean_exc.InternalError(code=500, message='BOOM')
        self.patchobject(sdk, 'parse_exception', side_effect=error)
        ex = self.assertRaises(bilean_exc.InternalError,
                               test_func, mock.Mock())

        self.assertEqual(500, ex.code)
        self.assertEqual('BOOM', ex.message)

    @mock.patch.object(connection, 'Connection')
    def test_create_connection_token(self, mock_conn):
        x_conn = mock.Mock()
        mock_conn.return_value = x_conn

        res = sdk.create_connection({'token': 'TOKEN', 'foo': 'bar'})

        self.assertEqual(x_conn, res)
        mock_conn.assert_called_once_with(user_agent=sdk.USER_AGENT,
                                          auth_plugin='token',
                                          token='TOKEN',
                                          foo='bar')

    @mock.patch.object(connection, 'Connection')
    def test_create_connection_password(self, mock_conn):
        x_conn = mock.Mock()
        mock_conn.return_value = x_conn

        res = sdk.create_connection({'user_id': '123', 'password': 'abc',
                                     'foo': 'bar'})

        self.assertEqual(x_conn, res)
        mock_conn.assert_called_once_with(user_agent=sdk.USER_AGENT,
                                          auth_plugin='password',
                                          user_id='123',
                                          password='abc',
                                          foo='bar')

    @mock.patch.object(connection, 'Connection')
    def test_create_connection_with_region(self, mock_conn):
        x_conn = mock.Mock()
        mock_conn.return_value = x_conn

        res = sdk.create_connection({'region_name': 'REGION_ONE'})

        self.assertEqual(x_conn, res)
        mock_conn.assert_called_once_with(user_agent=sdk.USER_AGENT,
                                          auth_plugin='password')

    @mock.patch.object(connection, 'Connection')
    @mock.patch.object(sdk, 'parse_exception')
    def test_create_connection_with_exception(self, mock_parse, mock_conn):
        ex_raw = Exception('Whatever')
        mock_conn.side_effect = ex_raw
        mock_parse.side_effect = bilean_exc.InternalError(code=123,
                                                          message='BOOM')

        ex = self.assertRaises(bilean_exc.InternalError,
                               sdk.create_connection)

        mock_conn.assert_called_once_with(user_agent=sdk.USER_AGENT,
                                          auth_plugin='password')
        mock_parse.assert_called_once_with(ex_raw)
        self.assertEqual(123, ex.code)
        self.assertEqual('BOOM', ex.message)
