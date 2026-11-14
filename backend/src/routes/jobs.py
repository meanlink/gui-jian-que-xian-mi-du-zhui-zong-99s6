from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Job, Report, Delivery
from src.schemas.job import JobInput, RevokeInput
from src.middlewares.auth import current_user, can_write, admin_only
from src.services import jobs
from src.services import authorizations as authz
from src.services.audit import record
from src.utils.serialization import job_dict, authorization_dict
router=APIRouter(prefix='/jobs')
@router.get('')
def listing(db=Depends(get_db),u=Depends(current_user)):
    return [job_dict(j) for j in db.scalars(select(Job).order_by(Job.id.desc()).limit(100))]
@router.post('',status_code=201)
def create(data:JobInput,db=Depends(get_db),u=Depends(can_write)):
    j=jobs.create(db,data,u); record(db,u.email,'job.create',{'id':j.id,'params':j.params})
    db.commit(); jobs.enqueue(j.id); return job_dict(j)
@router.get('/{id}')
def detail(id:int,db=Depends(get_db),u=Depends(current_user)):
    j=db.get(Job,id)
    if not j: raise HTTPException(404,'分析任务不存在')
    return job_dict(j)
@router.post('/{id}/approve')
def approve(id:int,db=Depends(get_db),u=Depends(admin_only)):
    j=db.get(Job,id)
    if not j: raise HTTPException(404,'分析任务不存在')
    if j.status!='completed':raise HTTPException(409,'仅已完成结果可以批准')
    active=authz.active_authorization(db,id)
    if active: raise HTTPException(409,'该分析已持有有效使用许可，无需重复批准')
    a=authz.grant(db,j,u.email)
    record(db,u.email,'job.approve',{'id':id,'authorization_id':a.id,'sequence':a.sequence})
    db.commit()
    return job_dict(j)
@router.post('/{id}/revoke')
def revoke(id:int,data:RevokeInput,db=Depends(get_db),u=Depends(admin_only)):
    j=db.get(Job,id)
    if not j: raise HTTPException(404,'分析任务不存在')
    reason=data.reason.strip()
    try:
        a,report_ids=authz.revoke(db,j,u.email,reason)
    except HTTPException:
        # 重试撤回时的补封动作必须落库，再向调用方返回 409
        db.commit()
        raise
    affected=[d_id for r_id in report_ids
              for d_id in db.scalars(select(Delivery.id).where(Delivery.report_id==r_id))]
    record(db,u.email,'job.revoke',{
        'id':id,'authorization_id':a.id,'reason':reason,
        'sealed_reports':report_ids,'sealed_deliveries':affected,
    })
    db.commit()
    return {'job':job_dict(j),'authorization':authorization_dict(a),
            'sealed_reports':report_ids,'sealed_deliveries':affected}
@router.get('/{id}/authorizations')
def authorization_history(id:int,db=Depends(get_db),u=Depends(current_user)):
    j=db.get(Job,id)
    if not j: raise HTTPException(404,'分析任务不存在')
    items=[]
    for a in authz.history(db,id):
        item=authorization_dict(a)
        reports=list(db.scalars(select(Report).where(Report.authorization_id==a.id)))
        item['reports']=[{'id':r.id,'name':r.name,'sealed':r.sealed,'enabled':r.enabled} for r in reports]
        delivery_ids=[d.id for r in reports for d in db.scalars(select(Delivery).where(Delivery.report_id==r.id))]
        item['delivery_ids']=delivery_ids
        items.append(item)
    return items
