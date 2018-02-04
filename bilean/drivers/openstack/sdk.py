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

'''
SDK Client
'''
import functools
from oslo_log import log as logging
import six

from openstack import connection
from openstack import exceptions as sdk_exc
from oslo_serialization import jsonutils
from requests import exceptions as req_exc

from bilean.common import exception as bilean_exc
from bilean import version

APP_NAME = 'bilean'
exc = sdk_exc
LOG = logging.getLogger(__name__)


def parse_exception(ex):
    '''Parse exception code and yield useful information.'''
    code = 500

    if isinstance(ex, sdk_exc.HttpException):
        # some exceptions don't contain status_code
        if ex.http_status is not None:
            code = ex.http_status
        message = ex.message
        data = {}
        try:
            data = jsonutils.loads(ex.details)
        except Exception:
            # Some exceptions don't have details record or
            # are not in JSON format
            pass

        # try dig more into the exception record
        # usually 'data' has two types of format :
        # type1: {"forbidden": {"message": "error message", "code": 403}
        # type2: {"code": 404, "error": { "message": "not found"}}
        if data:
            code = data.get('code', code)
            message = data.get('message', message)
            error = data.get('error')
            if error:
                code = data.get('code', code)
                message = data['error'].get('message', message)
            else:
                for value in data.values():
                    code = value.get('code', code)
                    message = value.get('message', message)

    elif isinstance(ex, sdk_exc.SDKException):
        # Besides HttpException there are some other exceptions like
        # ResourceTimeout can be raised from SDK, handle them here.
        message = ex.message
    elif isinstance(ex, req_exc.RequestException):
        # Exceptions that are not captured by SDK
        code = ex.errno
        message = six.text_type(ex)
    elif isinstance(ex, Exception):
        message = six.text_type(ex)

    raise bilean_exc.InternalError(code=code, message=message)


def translate_exception(func):
    """Decorator for exception translation."""

    @functools.wraps(func)
    def invoke_with_catch(driver, *args, **kwargs):
        try:
            return func(driver, *args, **kwargs)
        except Exception as ex:
            LOG.exception(ex)
            raise parse_exception(ex)

    return invoke_with_catch


def create_connection(params=None):
    if params is None:
        params = {}

    if params.get('token'):
        auth_type = 'token'
    else:
        auth_type = 'password'

    try:
        conn = connection.Connection(
            app_name=APP_NAME,
            app_version=version.version_info.version_string(),
            identity_api_version='3', auth_type=auth_type, **params)
    except Exception as ex:
        raise parse_exception(ex)

    return conn
