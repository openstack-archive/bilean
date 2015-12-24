#!/bin/bash
HOST_IP="192.168.142.14"
REGION="RegionOne"
BILEAN_USER="bileanUser"
BILEAN_PASS="bileanPass"

mysql -u root -p123123 -e "DROP DATABASE IF EXISTS bilean;"
mysql -u root -p123123 -e "CREATE DATABASE bilean;"
mysql -u root -p123123 -e "GRANT ALL PRIVILEGES ON bilean.* TO '$BILEAN_USER'@'%' IDENTIFIED BY '$BILEAN_PASS';"
bilean-manage db_sync
keystone service-create --name bilean --type billing --description "Openstack Billing Service"
service_id=`keystone service-list|grep billing |awk '{print $2}'`

keystone endpoint-create --region $REGION --service $service_id --publicurl http://$HOST_IP:8770/v1/$\(tenant_id\)s --adminurl http://$HOST_IP:8770/v1/$\(tenant_id\)s --internalurl http://$HOST_IP:8770/v1/$\(tenant_id\)s

keystone user-create --name $BILEAN_USER --pass $BILEAN_PASS --email bilean@domain.com

keystone user-role-add --user=$BILEAN_USER --tenant=service --role=admin
