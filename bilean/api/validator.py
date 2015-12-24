# Copyright 2011 Cloudscaling, Inc.
# All Rights Reserved.
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

import six

from bilean.common import exception
from bilean.common.i18n import _
from bilean.common import params

from oslo_log import log as logging
from oslo_utils import uuidutils


LOG = logging.getLogger(__name__)


def _validate_uuid_format(uid):
    return uuidutils.is_uuid_like(uid)


def is_valid_body(body, entity_name=None):
    if entity_name is not None:
        if not (body and entity_name in body):
            return False

    def is_dict(d):
        try:
            d.get(None)
            return True
        except AttributeError:
            return False

    return is_dict(body)


def validate(args, validator):
    """Validate values of args against validators in validator.

    :param args:      Dict of values to be validated.
    :param validator: A dict where the keys map to keys in args
                      and the values are validators.
                      Applies each validator to ``args[key]``
    :returns: True if validation succeeds. Otherwise False.

    A validator should be a callable which accepts 1 argument and which
    returns True if the argument passes validation. False otherwise.
    A validator should not raise an exception to indicate validity of the
    argument.

    Only validates keys which show up in both args and validator.

    """

    for key in validator:
        if key not in args:
            continue

        f = validator[key]
        assert callable(f)

        if not f(args[key]):
            LOG.debug("%(key)s with value %(value)s failed"
                      " validator %(name)s",
                      {'key': key, 'value': args[key], 'name': f.__name__})
            return False
    return True


def validate_string(value, name=None, min_length=0, max_length=None,
                    available_fields=None):
    """Check the length of specified string

    :param value: the value of the string
    :param name: the name of the string
    :param min_length: the min_length of the string
    :param max_length: the max_length of the string
    """
    if not isinstance(value, six.string_types):
        if name is None:
            msg = _("The input is not a string or unicode")
        else:
            msg = _("%s is not a string or unicode") % name
        raise exception.InvalidInput(message=msg)

    if name is None:
        name = value

    if available_fields:
        if value not in available_fields:
            msg = _("%(name)s must be in %(fields)s") % {
                'name': name, 'fields': available_fields}
            raise exception.InvalidInput(message=msg)

    if len(value) < min_length:
        msg = _("%(name)s has a minimum character requirement of "
                "%(min_length)s.") % {'name': name, 'min_length': min_length}
        raise exception.InvalidInput(message=msg)

    if max_length and len(value) > max_length:
        msg = _("%(name)s has more than %(max_length)s "
                "characters.") % {'name': name, 'max_length': max_length}
        raise exception.InvalidInput(message=msg)


def validate_resource(resource):
    """Make sure that resource is valid"""

    if not is_valid_body(resource):
        msg = _("%s is not a dict") % resource
        raise exception.InvalidInput(message=msg)
    if resource['resource_type']:
        validate_string(resource['resource_type'],
                        available_fields=params.RESOURCE_TYPES)
    else:
        msg = _('Expected resource_type field for resource')
        raise exception.InvalidInput(reason=msg)
    if resource['value']:
        validate_integer(resource['value'], 'resource_value', min_value=1)
    else:
        msg = _('Expected resource value field for resource')
        raise exception.InvalidInput(reason=msg)


def validate_integer(value, name, min_value=None, max_value=None):
    """Make sure that value is a valid integer, potentially within range."""

    try:
        value = int(str(value))
    except (ValueError, UnicodeEncodeError):
        msg = _('%(value_name)s must be an integer')
        raise exception.InvalidInput(reason=(
            msg % {'value_name': name}))

    if min_value is not None:
        if value < min_value:
            msg = _('%(value_name)s must be >= %(min_value)d')
            raise exception.InvalidInput(
                reason=(msg % {'value_name': name,
                               'min_value': min_value}))
    if max_value is not None:
        if value > max_value:
            msg = _('%(value_name)s must be <= %(max_value)d')
            raise exception.InvalidInput(
                reason=(
                    msg % {'value_name': name,
                           'max_value': max_value})
            )
    return value


def validate_float(value, name, min_value=None, max_value=None):
    """Make sure that value is a valid float, potentially within range."""

    try:
        value = float(str(value))
    except (ValueError, UnicodeEncodeError):
        msg = _('%(value_name)s must be an float')
        raise exception.InvalidInput(reason=(
            msg % {'value_name': name}))

    if min_value is not None:
        if value < min_value:
            msg = _('%(value_name)s must be >= %(min_value)d')
            raise exception.InvalidInput(
                reason=(msg % {'value_name': name,
                               'min_value': min_value}))
    if max_value is not None:
        if value > max_value:
            msg = _('%(value_name)s must be <= %(max_value)d')
            raise exception.InvalidInput(
                reason=(
                    msg % {'value_name': name,
                           'max_value': max_value}))
    return value


def is_none_string(val):
    """Check if a string represents a None value."""

    if not isinstance(val, six.string_types):
        return False

    return val.lower() == 'none'


def check_isinstance(obj, cls):
    """Checks that obj is of type cls, and lets PyLint infer types."""
    if isinstance(obj, cls):
        return obj
    raise Exception(_('Expected object of type: %s') % (str(cls)))
