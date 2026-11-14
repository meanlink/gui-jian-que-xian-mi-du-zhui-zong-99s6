import time, os, csv, io, hashlib, json
from fastapi import HTTPException
from src.models import Job, Report, Delivery
from src.config.settings import ARTIFACT_DIR
from src.services import authorizations as authz
def create(db, data):
    j=db.get(Job,data.job_id)
    if not j or j.status!='completed' or not j.approved:
        raise HTTPException(409,'请先选择已完成且获批准的分析结果')
    # 计划只能建立在当前有效授权之上；旧授权已撤回时必须重新批准取得新授权
    active=authz.active_authorization(db,j.id)
    if not active:
        raise HTTPException(409,'该分析没有有效的使用许可，请先由负责人重新批准')
    r=Report(name=data.name, job_id=j.id, authorization_id=active.id, destination=data.destination, interval_seconds=data.interval_seconds, next_run=time.time()+data.delay_seconds, enabled=True, sealed=False)
    db.add(r); db.flush()
    return r
def deliver(db, report):
    # 撤回以事务完成为界：封存计划不再生成任何新简报
    if report.sealed or not report.enabled:
        return None
    j=db.get(Job,report.job_id)
    active=authz.active_authorization(db,report.job_id) if j else None
    if not j or not j.approved or not active or active.id != report.authorization_id:
        # 授权已被撤回而计划尚未封存（并发窗口）：就地封存并拒绝发布
        report.enabled=False; report.sealed=True; report.sealed_at=time.time()
        report.sealed_reason=report.sealed_reason or '使用许可已撤回'
        return None
    out=io.StringIO()
    out.write('﻿')
    table=j.result.get('table',{})
    cols=table.get('columns',[])
    writer=csv.writer(out)
    def safe(v):
        if isinstance(v,(int,float)) and not isinstance(v,bool): return v
        text=str(v)
        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
    writer.writerow([safe(c['label']) for c in cols])
    for row in table.get('rows',[]): writer.writerow([safe(row.get(c['key'],'')) for c in cols])
    data=out.getvalue().encode('utf-8')
    delivery=Delivery(report_id=report.id, created_at=time.time(), checksum=hashlib.sha256(data).hexdigest(), filename='', destination=report.destination, sealed=False)
    db.add(delivery); db.flush()
    delivery.filename=f'report-{report.id}-delivery-{delivery.id}.csv'
    os.makedirs(ARTIFACT_DIR,exist_ok=True)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename),'wb') as f:f.write(data)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename+'.json'),'w') as f: json.dump({'job':j.name,'params':j.params,'result':j.result,'checksum':delivery.checksum},f,ensure_ascii=False,allow_nan=False)
    report.next_run=time.time()+report.interval_seconds
    return delivery
