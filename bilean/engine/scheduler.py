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

    def _notify_task(self, user_id):
        msg = {'user': user_id, 'notification': 'The balance is almost use up'}
        self.notifier.info('billing.notify', msg)
        admin_context = context.get_admin_context()
        user = user_mod.get_user(admin_context, user_id)
        if user['status'] != 'freeze' and user['rate'] > 0:
            user = user_mod.do_bill(admin_context,
                                        user,
                                        update=True,
                                        bilean_controller=self)
        try:
            db_api.job_delete(
                admin_context, self._generate_job_id(user_id, 'notify'))
        except exception.NotFound as e:
            LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))
        self._add_freeze_job(admin_context, user)

    def _daily_task(self, user_id):
        admin_context = context.get_admin_context()
        user = user_mod.get_user(admin_context, user_id)
        if user['status'] != 'freeze' and user['rate'] > 0:
            user_mod.do_bill(admin_context,
                                 user,
                                 update=True,
                                 bilean_controller=self)
        try:
            db_api.job_delete(
                admin_context, self._generate_job_id(user_id, 'daily'))
        except exception.NotFound as e:
            LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))

    def _freeze_task(self, user_id):
        admin_context = context.get_admin_context()
        user = user_mod.get_user(admin_context, user_id)
        if user['status'] != 'freeze' and user['rate'] > 0:
            user_mod.do_bill(admin_context,
                                 user,
                                 update=True,
                                 bilean_controller=self)
        try:
            db_api.job_delete(
                admin_context, self._generate_job_id(user_id, 'freeze'))
        except exception.NotFound as e:
            LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))

    def _add_notify_job(self, cnxt, user):
        if user['rate'] > 0:
            total_seconds = user['balance'] / user['rate'] * 3600.0
            prior_notify_time = cfg.CONF.bilean_task.prior_notify_time
            notify_seconds = total_seconds - prior_notify_time * 60
            notify_seconds = notify_seconds if notify_seconds > 0 else 0
            nf_time = timeutils.utcnow() + timedelta(seconds=notify_seconds)
            job_params = {'run_date': nf_time}
            job_id = self._generate_job_id(user['id'], 'notify')
            self.bilean_task.add_job(self._notify_task,
                                     job_id,
                                     job_type='notify',
                                     params=job_params)
            # Save job to database
            job = {'id': job_id,
                   'job_type': 'notify',
                   'engine_id': self.engine_id,
                   'parameters': {'run_date': nf_time}}
            db_api.job_create(cnxt, job)

    def _add_freeze_job(self, cnxt, user):
        if user['rate'] > 0:
            total_seconds = user['balance'] / user['rate'] * 3600.0
            run_time = timeutils.utcnow() + timedelta(seconds=total_seconds)
            job_params = {'run_date': run_time}
            job_id = self._generate_job_id(user['id'], 'freeze')
            self.bilean_task.add_job(self._freeze_task,
                                     job_id,
                                     job_type='freeze',
                                     params=job_params)
            # Save job to database
            job = {'id': job_id,
                   'job_type': 'freeze',
                   'engine_id': self.engine_id,
                   'parameters': {'run_date': run_time}}
            db_api.job_create(cnxt, job)

    def _add_daily_job(self, cnxt, user_id):
        job_id = self._generate_job_id(user_id, 'daily')
        params = {'hour': random.randint(0, 23),
                  'minute': random.randint(0, 59)}
        self.bilean_task.add_job(self._daily_task, job_id, params=params)
        # Save job to database
        job = {'id': job_id,
               'job_type': 'daily',
               'engine_id': self.engine_id,
               'parameters': params}
        db_api.job_create(cnxt, job)

    def _delete_all_job(self, cnxt, user_id):
        notify_job_id = self._generate_job_id(user_id, 'notify')
        freeze_job_id = self._generate_job_id(user_id, 'freeze')
        daily_job_id = self._generate_job_id(user_id, 'daily')
        for job_id in notify_job_id, freeze_job_id, daily_job_id:
            if self.bilean_task.is_exist(job_id):
                self.bilean_task.remove_job(job_id)
            try:
                db_api.job_delete(cnxt, job_id)
            except exception.NotFound as e:
                LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))

    def _update_notify_job(self, cnxt, user):
        notify_job_id = self._generate_job_id(user['id'], 'notify')
        freeze_job_id = self._generate_job_id(user['id'], 'freeze')
        for job_id in notify_job_id, freeze_job_id:
            if self.bilean_task.is_exist(job_id):
                self.bilean_task.remove_job(job_id)
        try:
            db_api.job_delete(cnxt, notify_job_id)
            db_api.job_delete(cnxt, freeze_job_id)
        except exception.NotFound as e:
            LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))
        self._add_notify_job(cnxt, user)

    def _update_freeze_job(self, cnxt, user):
        notify_job_id = self._generate_job_id(user['id'], 'notify')
        freeze_job_id = self._generate_job_id(user['id'], 'freeze')
        for job_id in notify_job_id, freeze_job_id:
            if self.bilean_task.is_exist(job_id):
                self.bilean_task.remove_job(job_id)
        try:
            db_api.job_delete(cnxt, notify_job_id)
            db_api.job_delete(cnxt, freeze_job_id)
        except exception.NotFound as e:
            LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))
        self._add_freeze_job(cnxt, user)

    def _update_user_job(self, cnxt, user):
        """Update user's billing job"""
        user_id = user["id"]
        no_job_status = ['init', 'free', 'freeze']
        if user['status'] in no_job_status:
            self._delete_all_job(cnxt, user_id)
        elif user['status'] == 'inuse':
            self._update_notify_job(cnxt, user)
            daily_job_id = self._generate_job_id(user_id, 'daily')
            if not self.bilean_task.is_exist(daily_job_id):
                self._add_daily_job(cnxt, user_id)
        elif user['status'] == 'prefreeze':
            self._update_freeze_job(cnxt, user)


def list_opts():
    yield bilean_task_group.name, bilean_task_opts
