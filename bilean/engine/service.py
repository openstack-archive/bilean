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
from bilean.engine import event as event_mod
from bilean.engine import policy as policy_mod
from bilean.engine import resource as resource_mod
from bilean.engine import rule as rule_mod
from bilean.engine import user as user_mod
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
        LOG.info("Starting billing task for all users pid=%s" % os.getpid())
        if self.bilean_task is None:
            self.bilean_task = BileanTask()

        #self._init_users()
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
        return user_mod.list_users(cnxt)

    @request_context
    def create_user(self, cnxt, values):
        return user_mod.create_user(cnxt, values)

    @request_context
    def show_user(self, cnxt, user_id):
        if cnxt.tenant_id != user_id and not cnxt.is_admin:
            raise exception.Forbidden("Only admin can do this.")
        user = user_mod.get_user(cnxt, user_id)
        if user['rate'] > 0 and user['status'] != 'freeze':
            return user_mod.do_bill(cnxt, user)
        return user

    @request_context
    def user_recharge(self, cnxt, user_id, value):
        """Do recharge for specify user."""
        user = user_mod.User.load(cnxt, user_id=user_id)
        user.do_recharge(cnxt, value)
        # As user has been updated, the billing job for the user
        # should to be updated too.
        self._update_user_job(cnxt, user)
        return user.to_dict()

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
        return rule_mod.list_rules(cnxt)

    @request_context
    def rule_show(self, cnxt, rule_id):
        return rule_mod.get_rule(cnxt, rule_id)

    @request_context
    def rule_update(self, cnxt, rule_id, values):
        return rules.update_rule(cnxt, rule_id, values)

    @request_context
    def rule_delete(self, cnxt, rule_id):
        return rule_mod.delete_rule(cnxt, rule_id)

    @request_context
    def validate_creation(self, cnxt, resources):
        """Validate resources creation.

        If user's balance is not enough for resources to keep 1 hour,
        will fail to validate.
        """
        user = user_mod.User.load(cnxt, user_id=cnxt.tenant_id)
        policy = policy_mod.Policy.load(cnxt, policy_id=user.policy_id)
        count = resources.get('count', 1)
        total_rate = 0
        for resource in resources['resources']:
            rule = policy.find_rule(cnxt, resource['resource_type']) 
            res = resource_mod.Resource('FAKE_ID', user.id,
                                        resource['resource_type'],
                                        resource['properties'])
            total_rate += rule.get_price(res)
        if count > 1:
            total_rate = total_rate * count
        # Pre 1 hour bill for resources
        pre_bill = ratecount * 3600
        if pre_bill > user.balance:
            return dict(validation=False)
        return dict(validation=True)

    @request_context
    def resource_create(self, cnxt, id, user_id, resource_type,
                        properties, **kwargs):
        """Create resource by given database

        Cause new resource would update user's rate, user update and billing
        would be done.

        """
        resource = resource_mod.Resource(id, user_id, resource_type,
                                         properties)
        # Find the exact rule of resource
        user = user_mod.load(cnxt, user_id=user_id)
        user_policy = policy_mod.Policy.load(cnxt, policy_id=user.policy_id)
        rule = user_policy.find_rule(cnxt, resource_type)

        # Update resource with rule_id and rate
        resource.rule_id = rule.id
        resource.rate = rule.get_price(resource)
        resource.store(cnxt)

        # Update user with resource
        user.update_with_resource(cnxt, resource)
        
        # As the rate of user has changed, the billing job for the user
        # should change too.
        self._update_user_job(cnxt, user)

        return resource.to_dict()

    @request_context
    def resource_list(self, cnxt, **search_opts):
        return resource_mod.resource_get_all(cnxt, **search_opts)

    @request_context
    def resource_get(self, cnxt, resource_id):
        return resource_mod.resource_get(cnxt, resource_id)

    @request_context
    def resource_update(self, cnxt, resource):
        """Do resource update."""
        res = resource_mod.Resource.load(cnxt, resource_id=resource['id'])
        old_rate = res.rate
        res.properties = resource['properties']
        rule = rule_mod.Rule.load(cnxt, rule_id=res.rule_id)
        res.rate = rule.get_price(res)
        res.store(cnxt)
        res.d_rate = res.rate - old_rate
        self.update_with_resource(cnxt, res, action='update')
        self._update_user_job(cnxt, user)

    @request_context
    def resource_delete(self, cnxt, resource):
        """Do resource delete"""
        res = resource_mod.Resource.load(cnxt, resource_id=resource['id'])
        user = user_mod.User.load(cnxt, user_id=resource['user_id']
        user.update_with_resource(cnxt, res, action='delete')
        self._update_user_job(cnxt, user)
        try:
            res.do_delete(cnxt)
        except Exception as ex:
            LOG.warn(_("Delete resource error %s"), ex)
            return

    @request_context
    def list_events(self, cnxt, **filters):
        return event_mod.events_get_all_by_filters(cnxt, **filters)

    def _generate_job_id(self, user_id, job_type):
        """Generate job id by given user_id and job type"""
        return "%s-%s" % (job_type, user_id)
