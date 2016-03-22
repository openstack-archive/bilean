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

from bilean.common.i18n import _
from bilean.db import api as db_api

CONF = cfg.CONF

CONF.import_opt('lock_retry_times', 'bilean.common.config')
CONF.import_opt('lock_retry_interval', 'bilean.common.config')

LOG = logging.getLogger(__name__)


def sleep(sleep_time):
    '''Interface for sleeping.'''

    eventlet.sleep(sleep_time)


def user_lock_acquire(user_id, engine_id):
    """Try to lock the specified user.

    :param user_id: ID of the user to be locked.
    :param engine_id: ID of the engine which wants to lock the user.
    :returns: True if lock is acquired, or False otherwise.
    """

    user_lock = db_api.user_lock_acquire(user_id, engine_id)
    if user_lock:
        return True

    retries = cfg.CONF.lock_retry_times
    retry_interval = cfg.CONF.lock_retry_interval

    while retries > 0:
        sleep(retry_interval)
        LOG.debug(_('Acquire lock for user %s again'), user_id)
        user_lock = db_api.user_lock_acquire(user_id, engine_id)
        if user_lock:
            return True
        retries = retries - 1

    return False


def user_lock_release(user_id, engine_id=None):
    """Release the lock on the specified user.

    :param user_id: ID of the user to be released.
    :param engine_id: ID of the engine which locked the user.
    """
    return db_api.user_lock_release(user_id, engine_id=engine_id)
