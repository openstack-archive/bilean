===========================
Enabling Bilean in DevStack
===========================

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

   For example, to enable nova service, edit `/etc/nova/nova.conf` and add
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
