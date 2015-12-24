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

from apscheduler.schedulers.background import BackgroundScheduler
import random

from bilean.common import exception
from bilean.common.i18n import _

from oslo_config import cfg
from oslo_log import log as logging

bilean_task_opts = [
    cfg.StrOpt('time_zone',
               default='utc',
               help=_('The time zone of job, default is utc')),
    cfg.IntOpt('prior_notify_time',
               default=3,
               help=_("The days notify user before user's balance is used up, "
                      "default is 3 days.")),
    cfg.IntOpt('misfire_grace_time',
               default=3600,
               help=_('Seconds after the designated run time that the job is '
                      'still allowed to be run.')),
    cfg.BoolOpt('store_ap_job',
                default=False,
                help=_('Allow bilean to store apscheduler job.')),
    cfg.StrOpt('backend',
               default='sqlalchemy',
               help='The backend to use for db'),
    cfg.StrOpt('connection',
               help='The SQLAlchemy connection string used to connect to the '
                    'database')
    ]

bilean_task_group = cfg.OptGroup('bilean_task')
cfg.CONF.register_group(bilean_task_group)
cfg.CONF.register_opts(bilean_task_opts, group=bilean_task_group)

LOG = logging.getLogger(__name__)


class BileanTask(object):

    _scheduler = None

    def __init__(self):
        super(BileanTask, self).__init__()
        self._scheduler = BackgroundScheduler()
        if cfg.CONF.bilean_task.store_ap_job:
            self._scheduler.add_jobstore(cfg.CONF.bilean_task.backend,
                                         url=cfg.CONF.bilean_task.connection)
        self.job_trigger_mappings = {'notify': 'date',
                                     'daily': 'cron',
                                     'freeze': 'date'}

    def add_job(self, task, job_id, job_type='daily', params=None):
        """Add a job to scheduler by given data.

        :param str|unicode user_id: used as job_id
        :param datetime alarm_time: when to first run the job

        """
        mg_time = cfg.CONF.bilean_task.misfire_grace_time
        job_time_zone = cfg.CONF.bilean_task.time_zone
        user_id = job_id.split('-')[1]
        trigger_type = self.job_trigger_mappings[job_type]
        if trigger_type == 'date':
            run_date = params.get('run_date')
            if run_date is None:
                msg = "Param run_date cannot be None for trigger type 'date'."
                raise exception.InvalidInput(reason=msg)
            self._scheduler.add_job(task, 'date',
                                    timezone=job_time_zone,
                                    run_date=run_date,
                                    args=[user_id],
                                    id=job_id,
                                    misfire_grace_time=mg_time)
        else:
            if params is None:
                hour, minute = self._generate_timer()
            else:
                hour = params.get('hour', None)
                minute = params.get('minute', None)
                if hour is None or minute is None:
                    msg = "Param hour or minute  cannot be None."
                    raise exception.InvalidInput(reason=msg)
            self._scheduler.add_job(task, 'cron',
                                    timezone=job_time_zone,
                                    hour=hour,
                                    minute=minute,
                                    args=[user_id],
                                    id=job_id,
                                    misfire_grace_time=mg_time)
        return job_id

    def modify_job(self, job_id, **changes):
        """Modifies the properties of a single job.

        Modifications are passed to this method as extra keyword arguments.

        :param str|unicode job_id: the identifier of the job
        """

        self._scheduler.modify_job(job_id, **changes)

    def remove_job(self, job_id):
        """Removes a job, preventing it from being run any more.

        :param str|unicode job_id: the identifier of the job
        """

        self._scheduler.remove_job(job_id)

    def start(self):
        LOG.info(_('Starting Billing scheduler'))
        self._scheduler.start()

    def stop(self):
        LOG.info(_('Stopping Billing scheduler'))
        self._scheduler.shutdown()

    def is_exist(self, job_id):
        """Returns if the Job exists that matches the given ``job_id``.

        :param str|unicode job_id: the identifier of the job
        :return: True|False
        """

        job = self._scheduler.get_job(job_id)
        return job is not None

    def _generate_timer(self):
        """Generate a random timer include hour and minute."""
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        return (hour, minute)


def list_opts():
    yield bilean_task_group.name, bilean_task_opts
