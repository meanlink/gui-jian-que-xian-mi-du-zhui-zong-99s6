/** @typedef {{id:number,name:string,source:string,rows:number,checksum:string}} Dataset */
/** @typedef {{id:number,name:string,dataset_id:number,status:string,result:Object,approved:boolean}} AnalysisJob */
/** @typedef {{id:number,name:string,job_id:number,destination:string,next_run:number,enabled:boolean,authorization_id:?number,sealed:boolean,sealed_at:?number,sealed_reason:string}} ReportSchedule */
/** @typedef {{id:number,report_id:number,created_at:number,checksum:string,filename:string,destination:string,sealed:boolean,sealed_at:?number}} Delivery */
/** @typedef {{id:number,job_id:number,sequence:number,status:string,granted_by:string,granted_at:number,revoked_by:?string,revoked_at:?number,revoke_reason:?string,reports:Array,delivery_ids:Array<number>}} Authorization */
export {};
