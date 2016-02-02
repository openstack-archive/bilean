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

from oslo_config import cfg
from oslo_log import log

from bilean.drivers import base
from bilean.drivers.openstack import sdk

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class KeystoneClient(base.DriverBase):
    '''Keystone V3 driver.'''

    def __init__(self, params=None):
        super(KeystoneClient, self).__init__(params)
        self.conn = sdk.create_connection(self.conn_params)

    @sdk.translate_exception
    def project_find(self, name_or_id, ignore_missing=True):
        '''Find a single project

        :param name_or_id: The name or ID of a project.
        :param bool ignore_missing: When set to ``False``
                    :class:`~openstack.exceptions.ResourceNotFound` will be
                    raised when the resource does not exist.
                    When set to ``True``, None will be returned when
                    attempting to find a nonexistent resource.
        :returns: One :class:`~openstack.identity.v3.project.Project` or None
        '''
        project = self.conn.identity.find_project(
            name_or_id, ignore_missing=ignore_missing)
        return project

    @sdk.translate_exception
    def project_list(self, **queries):
        '''Function to get project list.'''
        return self.conn.identity.projects(**queries)

    @classmethod
    def get_service_credentials(cls, **kwargs):
        '''Bilean service credential to use with Keystone.

        :param kwargs: An additional keyword argument list that can be used
                       for customizing the default settings.
        '''

        creds = {
            'auth_url': CONF.authentication.auth_url,
            'username': CONF.authentication.service_username,
            'password': CONF.authentication.service_password,
            'project_name': CONF.authentication.service_project_name,
            'user_domain_name': cfg.CONF.authentication.service_user_domain,
            'project_domain_name':
                cfg.CONF.authentication.service_project_domain,
        }
        creds.update(**kwargs)
        return creds
