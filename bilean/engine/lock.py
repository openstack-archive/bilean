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

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
import time

from bilean.common.i18n import _
from bilean.db import api as db_api

CONF = cfg.CONF

CONF.import_opt('lock_retry_times', 'bilean.common.config')
CONF.import_opt('lock_retry_interval', 'bilean.common.config')

LOG = logging.getLogger(__name__)


def is_engine_dead(ctx, engine_id, period_time=None):
    # if engine didn't report its status for peirod_time, will consider it
    # as a dead engine.
    if period_time is None:
        period_time = 2 * CONF.periodic_interval
    engine = db_api.service_get(ctx, engine_id)
    if not engine:
        return True
    if (timeutils.utcnow() - engine.updated_at).total_seconds() > period_time:
        return True
    return False


def sleep(sleep_time):
    '''Interface for sleeping.'''

    eventlet.sleep(sleep_time)


def user_lock_acquire(context, user_id, action_id, engine=None,
                      forced=False):
    """Try to lock the specified user.

    :param context: the context used for DB operations;
    :param user_id: ID of the user to be locked.
    :param action_id: ID of the action that attempts to lock the user.
    :param engine: ID of the engine that attempts to lock the user.
    :param forced: set to True to cancel current action that owns the lock,
                   if any.
    :returns: True if lock is acquired, or False otherwise.
    """

    owner = db_api.user_lock_acquire(user_id, action_id)
    if action_id == owner:
        return True

    retries = cfg.CONF.lock_retry_times
    retry_interval = cfg.CONF.lock_retry_interval

    while retries > 0:
        sleep(retry_interval)
        LOG.debug(_('Acquire lock for user %s again'), user_id)
        owner = db_api.user_lock_acquire(user_id, action_id)
        if action_id == owner:
            return True
        retries = retries - 1

    if forced:
        owner = db_api.user_lock_steal(user_id, action_id)
        return action_id == owner

    action = db_api.action_get(context, owner)
    if (action and action.owner and action.owner != engine and
            is_engine_dead(context, action.owner)):
        LOG.info('The user %(u)s is locked by dead action %(a)s, '
                 'try to steal the lock.',
                 {'u': user_id, 'a': owner})
        reason = _('Engine died when executing this action.')
        db_api.action_mark_failed(context, action.id, time.time(),
                                  reason=reason)
        db_api.user_lock_steal(user_id, action_id)
        return True

    LOG.error('User is already locked by action %(old)s, '
              'action %(new)s failed grabbing the lock',
              {'old': owner, 'new': action_id})

    return False


def user_lock_release(user_id, action_id):
    """Release the lock on the specified user.

    :param user_id: ID of the user to be released.
    :param action_id: ID of the action which locked the user.
    """
    return db_api.user_lock_release(user_id, action_id)
