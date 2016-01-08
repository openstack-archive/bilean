..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

.. _guide-install:

============
Installation
============

1. Get Bilean source code from Github

::

  $ cd /opt/stack
  $ git clone https://github.com/lvdongbing/bilean.git

2. Install Bilean with required packages

::

  $ cd /opt/stack/bilean
  $ sudo pip install -e .

3. Register Bilean service with keystone.

   This can be done using the :command:`setup-service` script under the
   :file:`tools` folder.

::

  $ source ~/devstack/openrc admin
  $ cd /opt/stack/bilean/tools
  $ ./setup-service <HOST IP> <SERVICE_PASSWORD>

4. Generate configuration file for the Bilean service.

::

  $ cd /opt/stack/bilean
  $ tools/gen-config
  $ sudo mkdir /etc/bilean
  $ sudo cp etc/bilean/api-paste.ini /etc/bilean
  $ sudo cp etc/bilean/policy.json /etc/bilean
  $ sudo cp etc/bilean/resource_definitions.yaml /etc/bilean
  $ sudo cp etc/bilean/bilean.conf.sample /etc/bilean/bilean.conf

Edit file :file:`/etc/bilean/bilean.conf` according to your system settings.
The most common options to be customized include:

::

  [database]
  connection = mysql://root:<DB PASSWORD>@127.0.0.1/bilean?charset=utf8

  [keystone_authtoken]
  auth_uri = http://<HOST>:5000/v3
  auth_version = 3
  cafile = /opt/stack/data/ca-bundle.pem
  identity_uri = http://<HOST>:35357
  admin_user = bilean
  admin_password = <BILEAN PASSWORD>
  admin_tenant_name = service

  [authentication]
  auth_url = http://<HOST>:5000/v3
  service_username = bilean
  service_password = <BILEAN PASSWORD>
  service_project_name = service

  [oslo_messaging_rabbit]
  rabbit_userid = <RABBIT USER ID>
  rabbit_hosts = <HOST>
  rabbit_password = <RABBIT PASSWORD>

5. Create Bilean Database

 Create Bilean database using the :command:`bilean-db-recreate` script under
 the :file:`tools` subdirectory.

::

  $ cd /opt/stack/bilean/tools
  $ ./bilean-db-recreate <DB PASSWORD>

6. Start bilean engine and api service.

 You may need two consoles for the services each.

::

  $ bilean-engine --config-file /etc/bilean/bilean.conf
  $ bilean-api --config-file /etc/bilean/bilean.conf
