import time
from fastapi import HTTPException
from sqlalchemy import select
from src.models import Job, Authorization, Report, Delivery

def active_authorization(db, job_id):
    return db.scalar(
        select(Authorization)
        .where(Authorization.job_id == job_id, Authorization.status == 'active')
        .order_by(Authorization.sequence.desc())
    )

def grant(db, job, actor):
    """批准即发放一份新的授权（新授权序号递增），并同步任务的派生批准标记。"""
    seq = db.scalar(
        select(Authorization.sequence)
        .where(Authorization.job_id == job.id)
        .order_by(Authorization.sequence.desc()).limit(1)
    )
    auth = Authorization(
        job_id=job.id,
        sequence=(seq or 0) + 1,
        status='active',
        granted_by=actor,
        granted_at=time.time(),
    )
    db.add(auth)
    db.flush()
    job.approved = True
    return auth

def _seal_reports_and_deliveries(db, auth_id, reason):
    """撤回封存：停用计划、既有简报全部封存；幂等，可在重试时安全重复执行。"""
    now = time.time()
    reports = list(db.scalars(select(Report).where(Report.authorization_id == auth_id)))
    report_ids = [r.id for r in reports]
    for r in reports:
        r.enabled = False
        r.sealed = True
        if not r.sealed_at:
            r.sealed_at = now
        r.sealed_reason = reason
    if report_ids:
        for d in db.scalars(select(Delivery).where(Delivery.report_id.in_(report_ids))):
            if not d.sealed:
                d.sealed = True
                d.sealed_at = now
    return report_ids

def revoke(db, job, actor, reason):
    """撤回当前有效授权。以本事务完成为界：其后发起的下载、分发一律拒绝。"""
    reason = (reason or '').strip()
    if not reason:
        raise HTTPException(422, '撤回必须注明原因')
    if len(reason) > 1000:
        raise HTTPException(422, '撤回原因不能超过 1000 字')
    auth = active_authorization(db, job.id)
    if not auth:
        # 中断恢复后重试：授权已撤回，仍再扫一遍确保所有受影响简报封存
        sealed = _seal_orphaned(db, job.id)
        raise HTTPException(409, '该分析当前没有有效的使用许可，无需再次撤回', headers={'X-Sealed-Reports': ','.join(map(str, sealed))})
    auth.status = 'revoked'
    auth.revoked_by = actor
    auth.revoked_at = time.time()
    auth.revoke_reason = reason
    report_ids = _seal_reports_and_deliveries(db, auth.id, reason)
    job.approved = False
    return auth, report_ids

def _seal_orphaned(db, job_id):
    """兜底：把任务下已封存授权关联但仍漏封的计划/简报补封（worker 恢复也会调用）。"""
    now = time.time()
    revoked_ids = list(db.scalars(
        select(Authorization.id).where(Authorization.job_id == job_id, Authorization.status == 'revoked')
    ))
    if not revoked_ids:
        return []
    report_ids = []
    for r in db.scalars(select(Report).where(Report.authorization_id.in_(revoked_ids))):
        r.enabled = False
        r.sealed = True
        r.sealed_at = r.sealed_at or now
        report_ids.append(r.id)
    if report_ids:
        for d in db.scalars(select(Delivery).where(Delivery.report_id.in_(report_ids))):
            if not d.sealed:
                d.sealed = True
                d.sealed_at = now
    return report_ids

def reconcile(db):
    """进程恢复时全量对账：凡挂在已撤回授权下的计划与简报，一律确保封存。"""
    revoked = list(db.scalars(select(Authorization).where(Authorization.status == 'revoked')))
    auth_ids = [a.id for a in revoked]
    if not auth_ids:
        return 0
    now = time.time()
    reports = list(db.scalars(select(Report).where(Report.authorization_id.in_(auth_ids))))
    report_ids = [r.id for r in reports]
    for r in reports:
        r.enabled = False
        r.sealed = True
        r.sealed_at = r.sealed_at or now
    sealed = 0
    if report_ids:
        for d in db.scalars(select(Delivery).where(Delivery.report_id.in_(report_ids))):
            if not d.sealed:
                d.sealed = True
                d.sealed_at = now
                sealed += 1
    return sealed

def history(db, job_id):
    return list(db.scalars(
        select(Authorization)
        .where(Authorization.job_id == job_id)
        .order_by(Authorization.sequence.asc())
    ))
