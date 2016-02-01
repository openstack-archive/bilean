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
from bilean.db import api as db_api
from bilean.engine import user as user_mod
from bilean import notifier

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

scheduler_group = cfg.OptGroup('scheduler')
cfg.CONF.register_group(scheduler_group)
cfg.CONF.register_opts(scheduler_opts, group=scheduler_group)

LOG = logging.getLogger(__name__)


class BileanScheduler(object):
    """Billing scheduler based on apscheduler"""

    job_types = (
        NOTIFY, DAILY, FREEZE,
    ) = (
        'notify', 'daily', 'freeze',
    )
    trigger_types = (DATE, CRON) = ('date', 'cron')

    def __init__(self, **kwargs):
        super(BileanScheduler, self).__init__()
        self._scheduler = BackgroundScheduler()
        self.notifier = notifier.Notifier()
        self.engine_id = kwargs.get('engine_id', None)
        self.context = kwargs.get('context', None)
        if not self.context:
            self.context = bilean_context.get_admin_context()
        if cfg.CONF.scheduler.store_ap_job:
            self._scheduler.add_jobstore(cfg.CONF.scheduler.backend,
                                         url=cfg.CONF.scheduler.connection)

    def init_scheduler(self):
        """Init all jobs related to the engine from db."""
        jobs = db_api.job_get_all(self.context, engine_id=self.engine_id)
        if not jobs:
            LOG.info(_LI("No job related to engine '%s'."), self.engine_id)
            return
        for job in jobs:
            if self.is_exist(job.id):
                continue
            task_name = "_%s_task" % (job.job_type)
            task = getattr(self, task_name)
            LOG.info(_LI("Add job '%(job_id)s' to engine '%(engine_id)s'."),
                     {'job_id': job.id, 'engine_id': self.engine_id})
            tg_type = self.CRON if job.job_type == self.DAILY else self.DAILY
            self.add_job(task, job.id, trigger_type=tg_type,
                         params=job.parameters)

    def add_job(self, task, job_id, trigger_type='date', **kwargs):
        """Add a job to scheduler by given data.

        :param str|unicode user_id: used as job_id
        :param datetime alarm_time: when to first run the job

        """
        mg_time = cfg.CONF.scheduler.misfire_grace_time
        job_time_zone = cfg.CONF.scheduler.time_zone
        user_id = job_id.split('-')[1]
        if trigger_type == 'date':
            run_date = kwargs.get('run_date')
            if run_date is None:
                msg = "Param run_date cannot be None for trigger type 'date'."
                raise exception.InvalidInput(reason=msg)
            self._scheduler.add_job(task, 'date',
                                    timezone=job_time_zone,
                                    run_date=run_date,
                                    args=[user_id],
                                    id=job_id,
                                    misfire_grace_time=mg_time)
            return

        # Add a cron type job
        hour = kwargs.get('hour', None)
        minute = kwargs.get('minute', None)
        if not hour or not minute:
            hour, minute = self._generate_timer()
        self._scheduler.add_job(task, 'cron',
                                timezone=job_time_zone,
                                hour=hour,
                                minute=minute,
                                args=[user_id],
                                id=job_id,
                                misfire_grace_time=mg_time)

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

    def _notify_task(self, user_id):
        user = user_mod.User.load(self.context, user_id=user_id)
        msg = {'user': user.id, 'notification': 'The balance is almost use up'}
        self.notifier.info('billing.notify', msg)
        if user.status != user.FREEZE and user.rate > 0:
            user.do_bill(self.context)
        try:
            db_api.job_delete(
                self.context, self._generate_job_id(user.id, 'notify'))
        except exception.NotFound as e:
            LOG.warning(_("Failed in deleting job: %s") % six.text_type(e))
        self._add_freeze_job(user)

    def _daily_task(self, user_id):
        user = user_mod.User.load(self.context, user_id=user_id)
        if user.status != user.FREEZE and user.rate > 0:
            user.do_bill(self.context)
        try:
            db_api.job_delete(
                self.context, self._generate_job_id(user.id, 'daily'))
        except exception.NotFound as e:
            LOG.warning(_("Failed in deleting job: %s") % six.text_type(e))

    def _freeze_task(self, user_id):
        user = user_mod.User.load(self.context, user_id=user_id)
        if user.status != user.FREEZE and user.rate > 0:
            user.do_bill(self.context)
        try:
            db_api.job_delete(
                self.context, self._generate_job_id(user.id, 'freeze'))
        except exception.NotFound as e:
            LOG.warning(_("Failed in deleting job: %s") % six.text_type(e))

    def _add_notify_job(self, user):
        if not user.rate:
            return False
        total_seconds = user['balance'] / user['rate']
        prior_notify_time = cfg.CONF.scheduler.prior_notify_time * 3600
        notify_seconds = total_seconds - prior_notify_time
        notify_seconds = notify_seconds if notify_seconds > 0 else 0
        run_date = timeutils.utcnow() + timedelta(seconds=notify_seconds)
        job_params = {'run_date': run_date}
        job_id = self._generate_job_id(user['id'], self.NOTIFY)
        self.add_job(self._notify_task, job_id, params=job_params)
        # Save job to database
        job = {'id': job_id,
               'job_type': self.NOTIFY,
               'engine_id': self.engine_id,
               'parameters': {'run_date': run_date}}
        db_api.job_create(self.context, job)

    def _add_freeze_job(self, user):
        if not user.rate:
            return False
        total_seconds = user.balance / user.rate
        run_date = timeutils.utcnow() + timedelta(seconds=total_seconds)
        job_params = {'run_date': run_date}
        job_id = self._generate_job_id(user.id, self.FREEZE)
        self.add_job(self._freeze_task, job_id, params=job_params)
        # Save job to database
        job = {'id': job_id,
               'job_type': self.FREEZE,
               'engine_id': self.engine_id,
               'parameters': {'run_date': run_date}}
        db_api.job_create(self.context, job)
        return True

    def _add_daily_job(self, user):
        job_id = self._generate_job_id(user.id, self.DAILY)
        params = {'hour': random.randint(0, 23),
                  'minute': random.randint(0, 59)}
        self.add_job(self._daily_task, job_id, trigger_type='cron',
                     params=params)
        # Save job to database
        job = {'id': job_id,
               'job_type': self.DAILY,
               'engine_id': self.engine_id,
               'parameters': params}
        db_api.job_create(self.context, job)
        return True

    def _delete_all_job(self, user):
        for job_type in self.job_types:
            job_id = self._generate_job_id(user.id, job_type)
            if self.is_exist(job_id):
                self.remove_job(job_id)
            try:
                db_api.job_delete(self.context, job_id)
            except exception.NotFound as e:
                LOG.warning(_("Failed in deleting job: %s") % six.text_type(e))

    def update_user_job(self, user):
        """Update user's billing job"""
        if user.status not in [user.ACTIVE, user.WARNING]:
            self._delete_all_job(user.id)
            return

        for job_type in self.NOTIFY, self.FREEZE:
            job_id = self._generate_job_id(user.id, job_type)
            if self.is_exist(job_id):
                self.remove_job(job_id)
            try:
                db_api.job_delete(self.context, job_id)
            except exception.NotFound as e:
                LOG.warning(_("Failed in deleting job: %s") % six.text_type(e))

        daily_job_id = self._generate_job_id(user.id, self.DAILY)
        if not self.is_exist(daily_job_id):
            self._add_daily_job(user)

        if user.status == user.ACTIVE:
            self._add_notify_job(user)
        else:
            self._add_freeze_job(user)

    def _generate_timer(self):
        """Generate a random timer include hour and minute."""
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        return hour, minute

    def _generate_job_id(self, user_id, job_type):
        """Generate job id by given user_id and job type"""
        return "%s-%s" % (job_type, user_id)


def list_opts():
    yield scheduler_group.name, scheduler_opts
