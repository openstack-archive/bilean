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

.. _guide-overview:

========
Overview
========

The mission for Bilean project is to provide a generic billing service for
an OpenStack cloud, it implements trigger-type billing based on other
OpenStack services' notification.

Components
~~~~~~~~~~

The developers are focusing on creating an OpenStack style project using
OpenStack design tenets, implemented in Python. We have started with a close
interaction with Heat project.

bilean
------

The :program:`bilean` tool is A CLI communicates with the :program:`bilean-api`
to manage rules, policies, users, resources, jobs and events. End developers
could also use the Bilean REST API directly.

bilean-api
----------

The :program:`bilean-api` component provides an OpenStack-native REST API that
processes API requests by sending them to the :program:`bilean-engine` over RPC.

bilean-notification
-------------------

The :program:`bilean-notification` component monitors the message bus for data
provided by other OpenStack components such as Nova, then converts notifications
into billing resources and sends to :program:`bilean-engine` over AMQP.

bilean-engine
-------------

The :program:`bilean-engine` does the main billing work, operates all users,
rules, policies, resources, jobs and events.


Installation
~~~~~~~~~~~~

You will need to make sure you have a suitable environment for deploying
Bilean. Please refer to :ref:`Installation <guide-install>` for detailed
instructions on setting up an environment to use the Bilean service.
