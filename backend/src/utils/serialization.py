import hashlib, json
def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def dataset_dict(d):
    return {'id':d.id, 'name':d.name, 'source':d.source, 'rows':len(d.records), 'checksum':d.checksum, 'created_at':d.created_at}
def job_dict(j):
    return {k:getattr(j,k) for k in ['id','name','dataset_id','params','status','result','error','approved','created_at','finished_at']}
def authorization_dict(a):
    return {k:getattr(a,k) for k in ['id','job_id','sequence','status','reason','granted_by','granted_at','revoked_by','revoked_at','revoke_reason']}
def report_dict(r):
    data={k:getattr(r,k) for k in ['id','name','job_id','destination','interval_seconds','next_run','enabled','authorization_id','sealed','sealed_at','sealed_reason']}
    return data
def delivery_dict(d):
    data={k:getattr(d,k) for k in ['id','report_id','created_at','checksum','filename','destination','sealed','sealed_at']}
    return data
