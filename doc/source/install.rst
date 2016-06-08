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

There are in general two ways to isntall Bilean service: install via DevStack
or install manually.

Install via DevStack
~~~~~~~~~~~~~~~~~~~~

This is the recommended way to install the Bilean service. Please refer to
following detailed instructions.

1. Download DevStack.

  ::

    git clone https://git.openstack.org/openstack-dev/devstack
    cd devstack

2. Add this repo as an external repository.

  ::

    cat > /opt/stack/devstack/local.conf << END
    [[local|localrc]]
    enable_plugin bilean https://github.com/openstack/bilean master
    END

3. Add Plugin Configuration Hooks.

   Bilean service is driven using a plugin mechanism for integrating to other
   services. Each integrated service may require additional configuration
   settings. Typically, you will need to set the notifications driver in each
   service's configuration.

   For example, to enable nova service, edit `/etc/nova/nvoa.conf` and add
   following configuration::

       [oslo_messaging_notifications]
       driver = messaging

   Or add following configurations to post config section in `local.conf` to
   make devstack automaticlly configure the settings above::

       [[post-config|$NOVA_CONF]]
       [oslo_messaging_notifications]
       driver = messaging

4. Then run devstack normally.

  ::

    cd /opt/stack/devstack
    ./stack.sh

Manual Installation
~~~~~~~~~~~~~~~~~~~

Install Bilean Server
---------------------

1. Get Bilean source code from Github.

  ::

    $ cd /opt/stack
    $ git clone https://github.com/lvdongbing/bilean.git

2. Install Bilean with required packages.

  ::

    $ cd /opt/stack/bilean
    $ sudo pip install -e .

3. Register Bilean service with keystone.

   This can be done using the :command:`setup-service` script under the
   :file:`tools` folder::

    $ source ~/devstack/openrc admin
    $ cd /opt/stack/bilean/tools
    $ ./setup-service <HOST IP> <SERVICE_PASSWORD>

4. Generate configuration file for the Bilean service.

  ::

    $ cd /opt/stack/bilean
    $ tox -e genconfig
    $ sudo mkdir /etc/bilean
    $ sudo cp etc/bilean/api-paste.ini /etc/bilean
    $ sudo cp etc/bilean/policy.json /etc/bilean
    $ sudo cp etc/bilean/resource_definitions.yaml /etc/bilean
    $ sudo cp etc/bilean/bilean.conf.sample /etc/bilean/bilean.conf

5. Modify configuration file. 

   Edit file :file:`/etc/bilean/bilean.conf` according to your system settings.
   The most common options to be customized include::

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

6. Create Bilean Database

   Create Bilean database using the :command:`bilean-db-recreate` script under
   the :file:`tools` subdirectory::

    $ cd /opt/stack/bilean/tools
    $ ./bilean-db-recreate <DB PASSWORD>

7. Start bilean services.

   You may need four consoles for the services each::

    $ bilean-engine --config-file /etc/bilean/bilean.conf
    $ bilean-api --config-file /etc/bilean/bilean.conf
    $ bilean-scheduler --config-file /etc/bilean/bilean.conf
    $ bilean-notification --config-file /etc/bilean/bilean.conf

Install Bilean Client
---------------------

1. Get Bilean client code from OpenStack git repository.

  ::

    $ cd /opt/stack
    $ git clone https://git.openstack.org/openstack/python-bileanclient.git

2. Install Bilean client.

  ::
  
    $ cd python-bileanclient
    $ sudo pip install -e .

Verify Installation
-------------------

To check whether Bilean server and Bilean client have been installed
successfully, run command ``bilean user-list`` in a console. The installation
is successful if the command output looks similar to the following.

::

  $ bilean user-list
  +----------------------------------+--------------------+---------+--------+------+--------+
  | id                               | name               | balance | credit | rate | status |
  +----------------------------------+--------------------+---------+--------+------+--------+
  | 675f42b2dd3a456c9890350403bce8cf | admin              | 0.0     | 0      | 0.0  | INIT   |
  | 927fef3da8194718a9179f4775f5f5ce | service            | 0.0     | 0      | 0.0  | INIT   |
  | c688c64711a64d06b90c2b3c5d513dde | demo               | 0.0     | 0      | 0.0  | INIT   |
  | e0504e51bd0d4e8886d06bb3cc3e6e80 | alt_demo           | 0.0     | 0      | 0.0  | INIT   |
  | e9950cf337be47e68a21c9b20b291142 | invisible_to_admin | 0.0     | 0      | 0.0  | INIT   |
  +----------------------------------+--------------------+---------+--------+------+--------+

