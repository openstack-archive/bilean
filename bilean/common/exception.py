#
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

'''
Bilean exception subclasses.
'''

import sys

from oslo_log import log as logging
import six

from bilean.common.i18n import _
from bilean.common.i18n import _LE

_FATAL_EXCEPTION_FORMAT_ERRORS = False
LOG = logging.getLogger(__name__)


class BileanException(Exception):
    '''Base Bilean Exception.

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.
    '''

    message = _("An unknown exception occurred.")

    def __init__(self, **kwargs):
        self.kwargs = kwargs

        try:
            self.message = self.msg_fmt % kwargs
        except KeyError:
            # exc_info = sys.exc_info()
            # if kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            LOG.exception(_LE('Exception in string format operation'))
            for name, value in six.iteritems(kwargs):
                LOG.error("%s: %s" % (name, value))  # noqa

            if _FATAL_EXCEPTION_FORMAT_ERRORS:
                raise
                # raise exc_info[0], exc_info[1], exc_info[2]

    def __str__(self):
        return six.text_type(self.message)

    def __unicode__(self):
        return six.text_type(self.message)

    def __deepcopy__(self, memo):
        return self.__class__(**self.kwargs)


class SIGHUPInterrupt(BileanException):
    msg_fmt = _("System SIGHUP signal received.")


class NotAuthenticated(BileanException):
    msg_fmt = _("You are not authenticated.")


class Forbidden(BileanException):
    msg_fmt = _("You are not authorized to complete this action.")


class BileanBadRequest(BileanException):
    msg_fmt = _("The request is malformed: %(msg)s")


class MultipleChoices(BileanException):
    msg_fmt = _("Multiple results found matching the query criteria %(arg)s. "
                "Please be more specific.")


class InvalidParameter(BileanException):
    msg_fmt = _("Invalid value '%(value)s' specified for '%(name)s'")


class RuleTypeNotFound(BileanException):
    msg_fmt = _("Rule type (%(rule_type)s) is not found.")


class RuleTypeNotMatch(BileanException):
    msg_fmt = _("%(message)s")


class RuleNotFound(BileanException):
    msg_fmt = _("The rule (%(rule)s) could not be found.")


class RuleNotSpecified(BileanException):
    msg_fmt = _("Rule not specified.")


class RuleOperationFailed(BileanException):
    msg_fmt = _("%(message)s")


class RuleOperationTimeout(BileanException):
    msg_fmt = _("%(message)s")


class PolicyNotFound(BileanException):
    msg_fmt = _("The policy (%(policy)s) could not be found.")


class UserNotFound(BileanException):
    msg_fmt = _("The user (%(user)s) could not be found.")


class InvalidSchemaError(BileanException):
    msg_fmt = _("%(message)s")


class SpecValidationFailed(BileanException):
    msg_fmt = _("%(message)s")


class FeatureNotSupported(BileanException):
    msg_fmt = _("%(feature)s is not supported.")


class Error(BileanException):
    msg_fmt = "%(message)s"

    def __init__(self, msg):
        super(Error, self).__init__(message=msg)


class ResourceInUse(BileanException):
    msg_fmt = _("The %(resource_type)s (%(resource_id)s) is still in use.")


class InvalidContentType(BileanException):
    msg_fmt = _("Invalid content type %(content_type)s")


class RequestLimitExceeded(BileanException):
    msg_fmt = _('Request limit exceeded: %(message)s')


class EventNotFound(BileanException):
    msg_fmt = _("The event (%(event)s) could not be found.")


class InvalidResource(BileanException):
    msg_fmt = _("%(msg)")


class InternalError(BileanException):
    '''A base class for internal exceptions in bilean.

    The internal exception classes which inherit from :class:`InternalError`
    class should be translated to a user facing exception type if need to be
    made user visible.
    '''
    msg_fmt = _('ERROR %(code)s happens for %(message)s.')
    message = _('Internal error happens')

    def __init__(self, **kwargs):
        super(InternalError, self).__init__(**kwargs)
        if 'code' in kwargs.keys():
            self.code = kwargs.get('code', 500)
            self.message = kwargs.get('message')


class ResourceBusyError(InternalError):
    msg_fmt = _("The %(resource_type)s (%(resource_id)s) is busy now.")


class TrustNotFound(InternalError):
    # Internal exception, not to be exposed to end user.
    msg_fmt = _("The trust for trustor (%(trustor)s) could not be found.")


class ResourceDeletionFailure(InternalError):
    # Used when deleting resources from other services
    msg_fmt = _("Failed in deleting %(resource)s.")


class ResourceNotFound(InternalError):
    msg_fmt = _("The resource (%(resource)s) could not be found.")


class ResourceStatusError(InternalError):
    msg_fmt = _("The resource %(resource_id)s is in error status "
                "- '%(status)s' due to '%(reason)s'.")


class InvalidPlugin(InternalError):
    msg_fmt = _("%(message)s")


class InvalidSpec(InternalError):
    msg_fmt = _("%(message)s")


class HTTPExceptionDisguise(Exception):
    """Disguises HTTP exceptions.

    The purpose is to let them be handled by the webob fault application
    in the wsgi pipeline.
    """

    def __init__(self, exception):
        self.exc = exception
        self.tb = sys.exc_info()[2]
