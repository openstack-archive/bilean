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
Utilities module.
'''

import datetime
import decimal
import random
import six
import string

from cryptography.fernet import Fernet
import requests
from requests import exceptions
from six.moves import urllib

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import encodeutils
from oslo_utils import strutils
from oslo_utils import timeutils

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common.i18n import _LI

cfg.CONF.import_opt('max_response_size', 'bilean.common.config')
LOG = logging.getLogger(__name__)


class URLFetchError(exception.Error, IOError):
    pass


def parse_int_param(name, value, allow_zero=True, allow_negative=False,
                    lower_limit=None, upper_limit=None):
    if value is None:
        return None

    if value in ('0', 0):
        if allow_zero:
            return int(value)
        raise exception.InvalidParameter(name=name, value=value)

    try:
        result = int(value)
    except (TypeError, ValueError):
        raise exception.InvalidParameter(name=name, value=value)
    else:
        if any([(allow_negative is False and result < 0),
                (lower_limit and result < lower_limit),
                (upper_limit and result > upper_limit)]):
            raise exception.InvalidParameter(name=name, value=value)

    return result


def parse_bool_param(name, value):
    if str(value).lower() not in ('true', 'false'):
        raise exception.InvalidParameter(name=name, value=str(value))

    return strutils.bool_from_string(value, strict=True)


def url_fetch(url, allowed_schemes=('http', 'https')):
    '''Get the data at the specified URL.

    The URL must use the http: or https: schemes.
    The file: scheme is also supported if you override
    the allowed_schemes argument.
    Raise an IOError if getting the data fails.
    '''
    LOG.info(_LI('Fetching data from %s'), url)

    components = urllib.parse.urlparse(url)

    if components.scheme not in allowed_schemes:
        raise URLFetchError(_('Invalid URL scheme %s') % components.scheme)

    if components.scheme == 'file':
        try:
            return urllib.request.urlopen(url).read()
        except urllib.error.URLError as uex:
            raise URLFetchError(_('Failed to retrieve data: %s') % uex)

    try:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()

        # We cannot use resp.text here because it would download the entire
        # file, and a large enough file would bring down the engine.  The
        # 'Content-Length' header could be faked, so it's necessary to
        # download the content in chunks to until max_response_size is reached.
        # The chunk_size we use needs to balance CPU-intensive string
        # concatenation with accuracy (eg. it's possible to fetch 1000 bytes
        # greater than max_response_size with a chunk_size of 1000).
        reader = resp.iter_content(chunk_size=1000)
        result = ""
        for chunk in reader:
            result += chunk
            if len(result) > cfg.CONF.max_response_size:
                raise URLFetchError("Data exceeds maximum allowed size (%s"
                                    " bytes)" % cfg.CONF.max_response_size)
        return result

    except exceptions.RequestException as ex:
        raise URLFetchError(_('Failed to retrieve data: %s') % ex)


def encrypt(msg):
    '''Encrypt message with random key.

    :param msg: message to be encrypted
    :returns: encrypted msg and key to decrypt
    '''
    password = Fernet.generate_key()
    f = Fernet(password)
    key = f.encrypt(encodeutils.safe_encode(msg))
    return encodeutils.safe_decode(password), encodeutils.safe_decode(key)


def decrypt(msg, key):
    '''Decrypt message using provided key.

    :param msg: encrypted message
    :param key: key used to decrypt
    :returns: decrypted message string
    '''
    f = Fernet(encodeutils.safe_encode(msg))
    msg = f.decrypt(encodeutils.safe_encode(key))

    return encodeutils.safe_decode(msg)


def random_name(length=8):
    if length <= 0:
        return ''

    lead = random.choice(string.ascii_letters)
    tail = ''.join(random.choice(string.ascii_letters + string.digits)
                   for i in range(length - 1))
    return lead + tail


def format_time(value):
    """Cut microsecond and format to isoformat string."""
    if isinstance(value, datetime.datetime):
        value = value.replace(microsecond=0)
        value = value.isoformat()
    return value


def format_time_to_seconds(t):
    """Format datetime to seconds from 1970-01-01 00:00:00 UTC."""
    epoch = datetime.datetime.utcfromtimestamp(0)
    if isinstance(t, datetime.datetime):
        return (t - epoch).total_seconds()
    if isinstance(t, six.string_types):
        try:
            dt = timeutils.parse_strtime(t)
        except ValueError:
            dt = timeutils.normalize_time(timeutils.parse_isotime(t))
        return (dt - epoch).total_seconds()
    return t


def make_decimal(value):
    """Format float to decimal."""
    if isinstance(value, decimal.Decimal):
        return value
    if isinstance(value, float):
        return decimal.Decimal.from_float(value)
    return decimal.Decimal(str(value))


def format_decimal(value, num=8):
    """Format decimal and keep num decimals."""
    if not isinstance(value, decimal.Decimal):
        value = make_decimal(value)
    dec = "0.%s" % ('0' * num)
    return value.quantize(decimal.Decimal(dec))


def dec2str(value):
    """Decimal to str and keep 2 decimals."""
    if not isinstance(value, decimal.Decimal):
        value = make_decimal(value)
    return str(value.quantize(decimal.Decimal('0.00')))
