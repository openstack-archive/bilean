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

from datetime import timedelta
import functools
import os
import random
import six
import uuid

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_service import service
from oslo_utils import timeutils

from bilean.common import context
from bilean.common import exception
from bilean.common.i18n import _
from bilean.common.i18n import _LI
from bilean.common.i18n import _LE
from bilean.common import messaging as rpc_messaging
from bilean.common import params as bilean_params
from bilean.common import schema
from bilean.db import api as db_api
from bilean.engine.bilean_task import BileanTask
from bilean.engine import clients as bilean_clients
from bilean.engine import environment
from bilean.engine import events as events_client
from bilean.engine import resources as resources_client
from bilean.engine import rules as rules_client
from bilean.engine import users as users_client
from bilean import notifier

LOG = logging.getLogger(__name__)


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        if ctx is not None and not isinstance(ctx, context.RequestContext):
            ctx = context.RequestContext.from_dict(ctx.to_dict())
        try:
            return func(self, ctx, *args, **kwargs)
        except exception.BileanException:
            raise oslo_messaging.rpc.dispatcher.ExpectedException()
    return wrapped


class EngineService(service.Service):
    """Manages the running instances from creation to destruction.

    All the methods in here are called from the RPC backend.  This is
    all done dynamically so if a call is made via RPC that does not
    have a corresponding method here, an exception will be thrown when
    it attempts to call into this class.  Arguments to these methods
    are also dynamically added and will be named as keyword arguments
    by the RPC caller.
    """

    RPC_API_VERSION = '1.1'

    def __init__(self, host, topic, manager=None, cnxt=None):
        super(EngineService, self).__init__()
        bilean_clients.initialise()
        self.host = host
        self.topic = topic

        # The following are initialized here, but assigned in start() which
        # happens after the fork when spawning multiple worker processes
        self.bilean_task = None
        self.engine_id = None
        self.target = None
        self._rpc_server = None
        self.notifier = notifier.Notifier()
        self.job_task_mapping = {'daily': '_daily_task',
                                 'notify': '_notify_task',
                                 'freeze': '_freeze_task'}
        if cnxt is None:
            cnxt = context.get_service_context()
        self.clients = cnxt.clients

    def start(self):
        self.engine_id = str(uuid.uuid4())
        target = oslo_messaging.Target(version=self.RPC_API_VERSION,
                                       server=cfg.CONF.host,
                                       topic=self.topic)
        self.target = target
        self._rpc_server = rpc_messaging.get_rpc_server(target, self)
        self._rpc_server.start()

        super(EngineService, self).start()

    def _stop_rpc_server(self):
        # Stop RPC connection to prevent new requests
        LOG.info(_LI("Stopping engine service..."))
        try:
            self._rpc_server.stop()
            self._rpc_server.wait()
            LOG.info(_LI('Engine service stopped successfully'))
        except Exception as ex:
            LOG.error(_LE('Failed to stop engine service: %s'),
                      six.text_type(ex))

    def stop(self):
        self._stop_rpc_server()

        # Wait for all active threads to be finished
        self.bilean_task.stop()
        super(EngineService, self).stop()

    def create_bilean_tasks(self):
        LOG.info("Starting  billing task  for all  users pid=%s" % os.getpid())
        if self.bilean_task is None:
            self.bilean_task = BileanTask()

        self._init_users()
        # Init billing job for engine
        admin_context = context.get_admin_context()
        jobs = db_api.job_get_by_engine_id(admin_context, self.engine_id)
        if jobs:
            for job in jobs:
                if self.bilean_task.is_exist(job.id):
                    continue
                job_type = job.job_type
                task = getattr(self, self.job_task_mapping[job_type])
                self.bilean_task.add_job(task,
                                         job.id,
                                         job_type=job_type,
                                         params=job.parameters)
        self.bilean_task.start()

    def _init_users(self):
        tenants = self.keystoneclient.tenants.list()
        tenant_ids = [t.id for t in tenants]
        admin_context = context.get_admin_context()
        users = self.list_users(admin_context)
        user_ids = [user['id'] for user in users]
        for tid in tenant_ids:
            if tid not in user_ids:
                user = self.create_user(
                    admin_context,
                    values={'id': tid,
                            'status': 'init',
                            'status_reason': 'Init status'})

    def _notify_task(self, user_id):
        msg = {'user': user_id, 'notification': 'The balance is almost use up'}
        self.notifier.info('billing.notify', msg)
        admin_context = context.get_admin_context()
        user = users_client.get_user(admin_context, user_id)
        if user['status'] != 'freeze' and user['rate'] > 0:
            user = users_client.do_bill(admin_context,
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
        user = users_client.get_user(admin_context, user_id)
        if user['status'] != 'freeze' and user['rate'] > 0:
            users_client.do_bill(admin_context,
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
        user = users_client.get_user(admin_context, user_id)
        if user['status'] != 'freeze' and user['rate'] > 0:
            users_client.do_bill(admin_context,
                                 user,
                                 update=True,
                                 bilean_controller=self)
        try:
            db_api.job_delete(
                admin_context, self._generate_job_id(user_id, 'freeze'))
        except exception.NotFound as e:
            LOG.warn(_("Failed in deleting job: %s") % six.text_type(e))

    @property
    def keystoneclient(self):
        return self.clients.client('keystone')

    @property
    def novaclient(self):
        return self.clients.client_plugin('nova')

    @property
    def cinderclient(self):
        return self.clients.client_plugin('cinder')

    @request_context
    def list_users(self, cnxt, detail=False):
        return users_client.list_users(cnxt)

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

    @request_context
    def create_user(self, cnxt, values):
        return users_client.create_user(cnxt, values)

    @request_context
    def show_user(self, cnxt, user_id):
        if cnxt.tenant_id != user_id and not cnxt.is_admin:
            raise exception.Forbidden("Only admin can do this.")
        user = users_client.get_user(cnxt, user_id)
        if user['rate'] > 0 and user['status'] != 'freeze':
            return users_client.do_bill(cnxt, user)
        return user

    @request_context
    def update_user(self, cnxt, user_id, values, user=None):
        """Update user info by given values."""
        # Do bill before updating user.
        if user is None:
            user = users_client.get_user(cnxt, user_id)
        if user['status'] != 'freeze' and user['rate'] > 0:
            user = users_client.do_bill(cnxt, user, update=True)

        action = values.get('action', 'update')
        if action.lower() == "recharge":
            recharge_value = values['balance']
            new_balance = recharge_value + user['balance']
            values.update(balance=new_balance)
            if user['status'] == 'init' and new_balance > 0:
                values.update(status='free',
                              status_reason='Recharge to free')
            elif user['status'] == 'freeze' and new_balance > 0:
                values.update(status='free',
                              status_reason='Recharge to free')
            if user['status'] == 'prefreeze':
                prior_notify_time = cfg.CONF.bilean_task.prior_notify_time
                notify_seconds = prior_notify_time * 60
                temp_use = notify_seconds * user['rate']
                if new_balance > temp_use:
                    values.update(status='inuse',
                                  status_reason='Recharge to inuse')
            events_client.generate_events(
                cnxt, user_id, 'recharge', recharge_value=recharge_value)

        user.update(values)

        # As user has been updated, the billing job for the user
        # should to be updated too.
        # values.update(self._update_user_job(cnxt, user))
        self._update_user_job(cnxt, user)
        # Update user
        return users_client.update_user(cnxt, user_id, values)

    @request_context
    def delete_user(self, cnxt, user_id):
        raise exception.NotImplement()

    @request_context
    def rule_create(self, cnxt, name, spec, metadata):
        type_name, version = schema.get_spec_version(spec)
        try:
            plugin = environment.global_env().get_rule(type_name)
        except exception.RuleTypeNotFound:
            msg = _("The specified rule type (%(type)s) is not supported."
                    ) % {"type": type_name}
            raise exception.BileanBadRequest(msg=msg)
        
        LOG.info(_LI("Creating rule type: %(type)s, name: %(name)s."),
                 {'type': type_name, 'name': name})
        rule = plugin(name, spec, metadata=metadata)
        try:
            rule.validate()
        except exception.InvalidSpec as ex:
            msg = six.text_type()
            LOG.error(_LE("Failed in creating rule: %s"), msg)
            raise exception.BileanBadRequest(msg=msg)

        rule.store(cnxt)
        LOG.info(_LI("Rule %(name)s is created: %(id)s."),
                 {'name': name, 'id': rule.id})
        return rule.to_dict()

    @request_context
    def rule_list(self, cnxt):
        return rules_client.list_rules(cnxt)

    @request_context
    def rule_show(self, cnxt, rule_id):
        return rules_client.get_rule(cnxt, rule_id)

    @request_context
    def rule_update(self, cnxt, rule_id, values):
        return rules.update_rule(cnxt, rule_id, values)

    @request_context
    def rule_delete(self, cnxt, rule_id):
        return rules_client.delete_rule(cnxt, rule_id)

    def _get_resource_rule(self, cnxt, resource):
        """Get the exact rule result for given resource."""

        resource_type = resource['resource_type']
        try:
            rules = rules_client.get_rule_by_filters(
                cnxt, resource_type=resource_type)
            return self._match_rule(rules, resource)
        except Exception as ex:
            LOG.warn(_("Failed in getting rule of resource: %s") %
                     six.text_type(ex))

    def _match_rule(self, rules, resource):
        res_size = resource['size']
        res_rule = {}
        for rule in rules:
            start = bilean_params.MIN_VALUE if rule.get('start') == '-1' \
                else rule.get('start')
            end = bilean_params.MAX_VALUE if rule.get('end') == '-1' \
                else rule.get('end')
            if res_size >= start and res_size <= end:
                if res_size.isdigit():
                    res_size = int(res_size)
                price = eval(rule.get('price'), {'n': res_size})
                res_rule["rate"] = price
                res_rule["rule_id"] = rule.get("id")
                return res_rule
        raise exception.NotFound(_('No exact rule found for resource: %s') %
                                 resource)

    @request_context
    def validate_creation(self, cnxt, resources):
        user_id = cnxt.tenant_id
        user = users_client.get_user(cnxt, user_id)
        ress = resources['resources']
        count = resources.get('count', 1)
        ratecount = 0
        for resource in ress:
            res_rule = self._get_resource_rule(cnxt, resource)
            ratecount += res_rule['rate']
        if count > 1:
            ratecount = ratecount * count
        # Pre 1 hour bill for resources
        pre_bill = ratecount * 1
        if pre_bill > user['balance']:
            return dict(validation=False)
        return dict(validation=True)

    @request_context
    def resource_create(self, cnxt, resources):
        """Create resource by given database

        Cause new resource would update user's rate, user update and billing
        would be done.

        """
        d_rate = 0
        for resource in resources:
            user_id = resource.get("user_id")
            if user_id is None:
                user_id = cnxt.tenant_id
                resource['user_id'] = user_id

            # Get the rule info and update resource resource
            res_rule = self._get_resource_rule(cnxt, resource)
            resource.update(res_rule)
            d_rate += res_rule['rate']

        self._change_user_rate(cnxt, user_id, d_rate)

        r_resources = []
        for resource in resources:
            r_resources.append(
                resources_client.resource_create(cnxt, resource))
        return r_resources

    def _change_user_rate(self, cnxt, user_id, df_rate):
        old_user = users_client.get_user(cnxt, user_id)

        # Update the rate of user
        old_rate = old_user.get('rate', 0)
        new_user_rate = old_rate + df_rate
        user_update_params = {"rate": new_user_rate}
        if old_rate == 0 and new_user_rate > 0:
            user_update_params['last_bill'] = timeutils.utcnow()
        if df_rate > 0 and old_user['status'] == 'free':
            user_update_params['status'] = 'inuse'
        elif df_rate < 0:
            if new_user_rate == 0 and old_user['balance'] > 0:
                user_update_params['status'] = 'free'
            elif old_user['status'] == 'prefreeze':
                prior_notify_time = cfg.CONF.bilean_task.prior_notify_time
                notify_seconds = prior_notify_time * 60
                temp_use = notify_seconds * new_user_rate
                if old_user['balance'] > temp_use:
                    user_update_params['status'] = 'inuse'
        user = self.update_user(cnxt, user_id, user_update_params, old_user)

        # As the rate of user has changed, the billing job for the user
        # should change too.
        self._update_user_job(cnxt, user)

    @request_context
    def resource_list(self, cnxt, **search_opts):
        return resources_client.resource_get_all(cnxt, **search_opts)

    @request_context
    def resource_get(self, cnxt, resource_id):
        return resources_client.resource_get(cnxt, resource_id)

    @request_context
    def resource_update(self, cnxt, resource):
        old_resource = db_api.resource_get_by_physical_resource_id(
            cnxt, resource['resource_ref'], resource['resource_type'])
        new_size = resource.get('size')
        new_status = resource.get('status')
        if new_size:
            res_rule = self._get_resource_rule(cnxt, resource)
            resource.update(res_rule)
            d_rate = resource["rate"] - old_resource["rate"]
        elif new_status in bilean_params.RESOURCE_STATUS and \
                new_status != old_resource['status']:
            if new_status == 'paused':
                d_rate = - resource["rate"]
            else:
                d_rate = resource["rate"]

        if d_rate:
            self._change_user_rate(cnxt, resource['user_id'], d_rate)
        return resources_client.resource_update_by_resource(cnxt, resource)

    @request_context
    def resource_delete(self, cnxt, resources):
        """Delele resources"""
        d_rate = 0
        for resource in resources:
            res = db_api.resource_get_by_physical_resource_id(
                cnxt, resource['resource_ref'], resource['resource_type'])
            d_rate += res['rate']
        d_rate = - d_rate
        self._change_user_rate(cnxt, res['user_id'], d_rate)
        try:
            for resource in resources:
                resources_client.resource_delete_by_physical_resource_id(
                    cnxt, resource['resource_ref'], resource['resource_type'])
        except Exception as ex:
            LOG.warn(_("Delete resource error %s"), ex)
            return

    def _delete_real_resource(self, resource):
        resource_client_mappings = {'instance': 'novaclient',
                                    'volume': 'cinderclient'}
        resource_type = resource['resource_type']
        c = getattr(self, resource_client_mappings[resource_type])
        LOG.info(_("Delete resource: %s") % resource['resource_ref'])
        c.delete(resource['resource_ref'])

    def do_freeze_action(self, cnxt, user_id):
        """Freeze user, delete all resource ralated to user"""
        resources = resources_client.resource_get_all(cnxt, user_id=user_id)
        for resource in resources:
            self._delete_real_resource(resource)

    @request_context
    def list_events(self, cnxt, **filters):
        return events_client.events_get_all_by_filters(cnxt, **filters)

    def _generate_job_id(self, user_id, job_type):
        """Generate job id by given user_id and job type"""
        return "%s-%s" % (job_type, user_id)
