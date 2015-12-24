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

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine

    job = sqlalchemy.Table(
        'job', meta,
        sqlalchemy.Column('id', sqlalchemy.String(50),
                          primary_key=True, nullable=False),
        sqlalchemy.Column('engine_id', sqlalchemy.String(36),
                          nullable=False),
        sqlalchemy.Column('job_type', sqlalchemy.String(10),
                          nullable=False),
        sqlalchemy.Column('parameters', types.Dict()),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    try:
        job.create()
    except Exception:
        LOG.error("Table |%s| not created!", repr(job))
        raise


def downgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    job = sqlalchemy.Table('job', meta, autoload=True)
    try:
        job.drop()
    except Exception:
        LOG.error("Job table not dropped")
        raise
