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

import sqlalchemy

from bilean.db.sqlalchemy import types


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine

    user = sqlalchemy.Table(
        'user', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('policy_id',
                          sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('policy.id'),
                          nullable=True),
        sqlalchemy.Column('balance', sqlalchemy.Float),
        sqlalchemy.Column('rate', sqlalchemy.Float),
        sqlalchemy.Column('credit', sqlalchemy.Integer),
        sqlalchemy.Column('last_bill', sqlalchemy.DateTime),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.Text),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_at', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    rule = sqlalchemy.Table(
        'rule', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('type', sqlalchemy.String(255)),
        sqlalchemy.Column('spec', types.Dict),
        sqlalchemy.Column('meta_data', types.Dict),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_at', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    policy = sqlalchemy.Table(
        'policy', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(255)),
        sqlalchemy.Column('rules', types.List),
        sqlalchemy.Column('is_default', sqlalchemy.Boolean),
        sqlalchemy.Column('meta_data', types.Dict),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_at', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    resource = sqlalchemy.Table(
        'resource', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36), primary_key=True,
                          nullable=False),
        sqlalchemy.Column('user_id',
                          sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('user.id'),
                          nullable=False),
        sqlalchemy.Column('rule_id', sqlalchemy.String(36), nullable=False),
        sqlalchemy.Column('resource_type', sqlalchemy.String(36),
                          nullable=False),
        sqlalchemy.Column('last_bill', sqlalchemy.DateTime),
        sqlalchemy.Column('properties', types.Dict),
        sqlalchemy.Column('rate', sqlalchemy.Float, nullable=False),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime),
        sqlalchemy.Column('deleted_at', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    event = sqlalchemy.Table(
        'event', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('timestamp', sqlalchemy.DateTime),
        sqlalchemy.Column('obj_id', sqlalchemy.String(36)),
        sqlalchemy.Column('obj_type', sqlalchemy.String(36)),
        sqlalchemy.Column('obj_name', sqlalchemy.String(255)),
        sqlalchemy.Column('action', sqlalchemy.String(36)),
        sqlalchemy.Column('user_id', sqlalchemy.String(36)),
        sqlalchemy.Column('level', sqlalchemy.Integer),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.Text),
        sqlalchemy.Column('meta_data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    consumption = sqlalchemy.Table(
        'consumption', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('user_id', sqlalchemy.String(36)),
        sqlalchemy.Column('resource_id', sqlalchemy.String(36)),
        sqlalchemy.Column('resource_type', sqlalchemy.String(255)),
        sqlalchemy.Column('start_time', sqlalchemy.DateTime),
        sqlalchemy.Column('end_time', sqlalchemy.DateTime),
        sqlalchemy.Column('rate', sqlalchemy.Float),
        sqlalchemy.Column('cost', sqlalchemy.Float),
        sqlalchemy.Column('meta_data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    recharge = sqlalchemy.Table(
        'recharge', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('user_id', sqlalchemy.String(36)),
        sqlalchemy.Column('type', sqlalchemy.String(255)),
        sqlalchemy.Column('timestamp', sqlalchemy.DateTime),
        sqlalchemy.Column('value', sqlalchemy.Float),
        sqlalchemy.Column('meta_data', types.Dict),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    action = sqlalchemy.Table(
        'action', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(63)),
        sqlalchemy.Column('context', types.Dict),
        sqlalchemy.Column('target', sqlalchemy.String(36)),
        sqlalchemy.Column('action', sqlalchemy.String(255)),
        sqlalchemy.Column('cause', sqlalchemy.String(255)),
        sqlalchemy.Column('owner', sqlalchemy.String(36)),
        sqlalchemy.Column('start_time', sqlalchemy.Float(precision='24,8')),
        sqlalchemy.Column('end_time', sqlalchemy.Float(precision='24,8')),
        sqlalchemy.Column('timeout', sqlalchemy.Integer),
        sqlalchemy.Column('inputs', types.Dict),
        sqlalchemy.Column('outputs', types.Dict),
        sqlalchemy.Column('data', types.Dict),
        sqlalchemy.Column('status', sqlalchemy.String(255)),
        sqlalchemy.Column('status_reason', sqlalchemy.Text),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    dependency = sqlalchemy.Table(
        'dependency', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('depended',
                          sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('action.id'),
                          nullable=False),
        sqlalchemy.Column('dependent',
                          sqlalchemy.String(36),
                          sqlalchemy.ForeignKey('action.id'),
                          nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    user_lock = sqlalchemy.Table(
        'user_lock', meta,
        sqlalchemy.Column('user_id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('action_id', sqlalchemy.String(36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    service = sqlalchemy.Table(
        'service', meta,
        sqlalchemy.Column('id', sqlalchemy.String(36),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('host', sqlalchemy.String(255)),
        sqlalchemy.Column('binary', sqlalchemy.String(255)),
        sqlalchemy.Column('topic', sqlalchemy.String(255)),
        sqlalchemy.Column('disabled', sqlalchemy.Boolean),
        sqlalchemy.Column('disabled_reason', sqlalchemy.String(255)),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    tables = (
        policy,
        user,
        rule,
        resource,
        event,
        consumption,
        recharge,
        action,
        dependency,
        user_lock,
        service,
    )

    for index, table in enumerate(tables):
        try:
            table.create()
        except Exception:
            # If an error occurs, drop all tables created so far to return
            # to the previously existing state.
            meta.drop_all(tables=tables[:index])
            raise


def downgrade(migrate_engine):
    raise NotImplementedError('Database downgrade not supported - '
                              'would drop all tables')
