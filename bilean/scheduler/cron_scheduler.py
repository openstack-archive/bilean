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

from bilean.common import context as bilean_context
from bilean.common import exception
from bilean.common.i18n import _
from bilean.common.i18n import _LI
from bilean.common import utils
from bilean.db import api as db_api
from bilean.engine import user as user_mod
from bilean.rpc import client as rpc_client

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
import random
import six

scheduler_opts = [
    cfg.StrOpt('time_zone',
               default='utc',
               help=_('The time zone of job, default is utc')),
    cfg.IntOpt('prior_notify_time',
               default=3,
               help=_('Time in hours before notify user when the balance of '
                      'user is almost used up.')),
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

scheduler_group = cfg.OptGroup('scheduler')
cfg.CONF.register_group(scheduler_group)
cfg.CONF.register_opts(scheduler_opts, group=scheduler_group)

LOG = logging.getLogger(__name__)


class CronScheduler(object):
    """Cron scheduler based on apscheduler"""

    job_types = (
        NOTIFY, DAILY, FREEZE,
    ) = (
        'notify', 'daily', 'freeze',
    )
    trigger_types = (DATE, CRON) = ('date', 'cron')

    def __init__(self, **kwargs):
        super(CronScheduler, self).__init__()
        self._scheduler = BackgroundScheduler()
        self.scheduler_id = kwargs.get('scheduler_id')
        self.rpc_client = rpc_client.EngineClient()
        if cfg.CONF.scheduler.store_ap_job:
            self._scheduler.add_jobstore(cfg.CONF.scheduler.backend,
                                         url=cfg.CONF.scheduler.connection)

    def start(self):
        LOG.info(_('Starting Cron scheduler'))
        self._scheduler.start()

    def stop(self):
        LOG.info(_('Stopping Cron scheduler'))
        self._scheduler.shutdown()

    def init_scheduler(self):
        """Init all jobs related to the engine from db."""
        admin_context = bilean_context.get_admin_context()
        jobs = [] or db_api.job_get_all(admin_context,
                                        scheduler_id=self.scheduler_id)
        for job in jobs:
            if self._is_exist(job.id):
                continue
            LOG.info(_LI("Add job '%(job_id)s' to scheduler '%(id)s'."),
                     {'job_id': job.id, 'id': self.scheduler_id})
            self._add_job(job.id, job.job_type, **job.parameters)

        LOG.info(_LI("Initialise users from keystone."))
        users = user_mod.User.init_users(admin_context)

        # Init daily job for all users
        if users:
            for user in users:
                job_id = self._generate_job_id(user.id, self.DAILY)
                if self._is_exist(job_id):
                    continue
                self._add_daily_job(user)

    def _add_job(self, job_id, task_type, **kwargs):
        """Add a job to scheduler by given data.

        :param str|unicode user_id: used as job_id
        :param datetime alarm_time: when to first run the job

        """
        mg_time = cfg.CONF.scheduler.misfire_grace_time
        job_time_zone = cfg.CONF.scheduler.time_zone
        user_id = job_id.split('-')[1]
        trigger_type = self.CRON if task_type == self.DAILY else self.DATE

        if trigger_type == self.DATE:
            run_date = kwargs.get('run_date')
            if run_date is None:
                msg = "Param run_date cannot be None for trigger type 'date'."
                raise exception.InvalidInput(reason=msg)
            self._scheduler.add_job(self._task, 'date',
                                    timezone=job_time_zone,
                                    run_date=run_date,
                                    args=[user_id, task_type],
                                    id=job_id,
                                    misfire_grace_time=mg_time)
            return

        # Add a cron type job
        hour = kwargs.get('hour')
        minute = kwargs.get('minute')
        if not hour or not minute:
            hour, minute = self._generate_timer()
        self._scheduler.add_job(self._task, 'cron',
                                timezone=job_time_zone,
                                hour=hour,
                                minute=minute,
                                args=[user_id, task_type],
                                id=job_id,
                                misfire_grace_time=mg_time)

    def _remove_job(self, job_id):
        """Removes a job, preventing it from being run any more.

        :param str|unicode job_id: the identifier of the job
        """

        self._scheduler.remove_job(job_id)

    def _is_exist(self, job_id):
        """Returns if the Job exists that matches the given ``job_id``.

        :param str|unicode job_id: the identifier of the job
        :return: True|False
        """

        job = self._scheduler.get_job(job_id)
        return job is not None

    def _task(self, user_id, task_type):
        admin_context = bilean_context.get_admin_context()
        self.rpc_client.settle_account(
            admin_context, user_id, task=task_type)
        if task_type != self.DAILY:
            try:
                db_api.job_delete(
                    admin_context, self._generate_job_id(user_id, task_type))
            except exception.NotFound as e:
                LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))

    def _add_notify_job(self, user):
        if user.rate == 0:
            return False
        total_seconds = user.balance / user.rate
        prior_notify_time = cfg.CONF.scheduler.prior_notify_time * 3600
        notify_seconds = total_seconds - prior_notify_time
        notify_seconds = notify_seconds if notify_seconds > 0 else 0
        run_date = timeutils.utcnow() + timedelta(seconds=notify_seconds)
        job_params = {'run_date': run_date}
        job_id = self._generate_job_id(user.id, self.NOTIFY)
        self._add_job(job_id, self.NOTIFY, **job_params)
        # Save job to database
        job = {'id': job_id,
               'job_type': self.NOTIFY,
               'scheduler_id': self.scheduler_id,
               'parameters': {'run_date': utils.format_time(run_date)}}
        admin_context = bilean_context.get_admin_context()
        db_api.job_create(admin_context, job)

    def _add_freeze_job(self, user):
        if user.rate == 0:
            return False
        total_seconds = user.balance / user.rate
        LOG.info(_LI("###########Fuck user: %s"), user.to_dict())
        run_date = timeutils.utcnow() + timedelta(seconds=total_seconds)
        job_params = {'run_date': run_date}
        job_id = self._generate_job_id(user.id, self.FREEZE)
        self._add_job(job_id, self.FREEZE, **job_params)
        # Save job to database
        job = {'id': job_id,
               'job_type': self.FREEZE,
               'scheduler_id': self.scheduler_id,
               'parameters': {'run_date': utils.format_time(run_date)}}
        admin_context = bilean_context.get_admin_context()
        db_api.job_create(admin_context, job)
        return True

    def _add_daily_job(self, user):
        job_id = self._generate_job_id(user.id, self.DAILY)
        job_params = {'hour': random.randint(0, 23),
                      'minute': random.randint(0, 59)}
        self._add_job(job_id, self.DAILY, **job_params)
        return True

    def _generate_timer(self):
        """Generate a random timer include hour and minute."""
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        return hour, minute

    def _generate_job_id(self, user_id, job_type):
        """Generate job id by given user_id and job type"""
        return "%s-%s" % (job_type, user_id)

    def update_jobs(self, user):
        """Update user's billing job"""
        # Delete all jobs except daily job
        admin_context = bilean_context.get_admin_context()
        for job_type in self.NOTIFY, self.FREEZE:
            job_id = self._generate_job_id(user.id, job_type)
            try:
                if self._is_exist(job_id):
                    self._remove_job(job_id)
                    db_api.job_delete(admin_context, job_id)
            except Exception as e:
                LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))

        if user.status == user.ACTIVE:
            self._add_notify_job(user)
        elif user.status == user.WARNING:
            self._add_freeze_job(user)

    def delete_jobs(self, user):
        """Delete all jobs related the specific user."""
        admin_context = bilean_context.get_admin_context()
        for job_type in self.job_types:
            job_id = self._generate_job_id(user.id, job_type)
            try:
                if self._is_exist(job_id):
                    self._remove_job(job_id)
                    db_api.job_delete(admin_context, job_id)
            except Exception as e:
                LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))


def list_opts():
    yield scheduler_group.name, scheduler_opts
