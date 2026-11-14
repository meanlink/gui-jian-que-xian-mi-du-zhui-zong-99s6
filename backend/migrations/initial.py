import time
from sqlalchemy import inspect, text
from src.config.database import engine, Session, Base
from src import models

# 旧库升级时新增的列：表 -> [(列名, 列类型 DDL)]
_ADDED_COLUMNS = {
    'reports': [
        ('authorization_id', 'INTEGER'),
        ('sealed', 'BOOLEAN'),
        ('sealed_at', 'FLOAT'),
        ('sealed_reason', 'VARCHAR(1000)'),
    ],
    'deliveries': [
        ('sealed', 'BOOLEAN'),
        ('sealed_at', 'FLOAT'),
    ],
}

def _add_missing_columns():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {col['name'] for col in inspector.get_columns(table)}
            for name, ddl_type in columns:
                if name not in present:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl_type}'))

def _backfill():
    """旧库中已批准的任务没有授权记录：按 job 补一份 active 授权并把计划挂接过去。"""
    with Session() as db:
        rows = db.execute(text(
            "SELECT j.id, j.created_at FROM jobs j "
            "WHERE j.approved IS TRUE AND NOT EXISTS ("
            "SELECT 1 FROM authorizations a WHERE a.job_id = j.id)"
        )).fetchall()
        for job_id, created_at in rows:
            seq = db.execute(text(
                'SELECT COALESCE(MAX(sequence), 0) + 1 FROM authorizations WHERE job_id = :jid'
            ), {'jid': job_id}).scalar_one()
            db.execute(text(
                'INSERT INTO authorizations (job_id, sequence, status, reason, granted_by, granted_at) '
                "VALUES (:jid, :seq, 'active', '', 'legacy-migration', :at)"
            ), {'jid': job_id, 'seq': seq, 'at': created_at or time.time()})
        db.commit()
        for job_id, _ in rows:
            auth = db.execute(text(
                'SELECT id FROM authorizations WHERE job_id = :jid ORDER BY sequence DESC LIMIT 1'
            ), {'jid': job_id}).scalar_one()
            db.execute(text(
                'UPDATE reports SET authorization_id = :aid, sealed = COALESCE(sealed, 0) '
                'WHERE job_id = :jid AND authorization_id IS NULL'
            ), {'aid': auth, 'jid': job_id})
        db.execute(text('UPDATE reports SET sealed = 0 WHERE sealed IS NULL'))
        db.execute(text('UPDATE deliveries SET sealed = 0 WHERE sealed IS NULL'))
        db.commit()

def migrate():
    Base.metadata.create_all(engine)
    _add_missing_columns()
    _backfill()

if __name__ == '__main__':
    migrate()
