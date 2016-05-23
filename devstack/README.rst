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
   settings. For example, typically, you will need to add the
   ``billing_notifications`` notification topic to each service's configuration.

4. Then run devstack normally.

  ::

    cd /opt/stack/devstack
    ./stack.sh
