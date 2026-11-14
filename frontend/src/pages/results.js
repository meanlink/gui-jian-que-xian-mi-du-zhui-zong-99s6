import {jobs} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {chart} from '../components/common/chart.js';
import {table} from '../components/common/table.js';
import {status} from '../components/common/status.js';
import {esc,fmt,date,notify} from '../utils/dom.js';

function authBadge(authorized,everAuthorized){
 if(authorized)return '<span class="auth-badge is-active">使用许可有效</span>';
 return everAuthorized
   ? '<span class="auth-badge is-revoked">使用许可已撤回</span>'
   : '<span class="auth-badge">待负责人批准</span>';
}

function authorizationPanel(history){
 if(!history.length)return '';
 const rows=history.map(a=>{
   const affected=a.reports||[];
   const reportNames=affected.length
     ? affected.map(r=>'#'+r.id+' '+esc(r.name)+(r.sealed?'（已封存）':'')).join('；')
     : '无关联分发计划';
   const deliveryText=a.delivery_ids&&a.delivery_ids.length
     ? '受影响简报 #'+a.delivery_ids.join('、#')
     : '无受影响简报';
   if(a.status==='revoked'){
     return '<article class="auth-row revoked">'
       +'<div><span class="auth-seq">第 '+a.sequence+' 次授权 · 已撤回</span>'
       +'<p><strong>批准：</strong>'+esc(a.granted_by)+' · '+date(a.granted_at)+'</p>'
       +'<p><strong>撤回：</strong>'+esc(a.revoked_by||'')+' · '+date(a.revoked_at)+'</p>'
       +'<p class="revoke-reason"><strong>撤回原因：</strong>'+esc(a.revoke_reason||'')+'</p>'
       +'<p class="hint">'+reportNames+'；'+deliveryText+'（简报保留查证，禁止下载）</p></div></article>';
   }
   return '<article class="auth-row active">'
     +'<div><span class="auth-seq">第 '+a.sequence+' 次授权 · 有效</span>'
     +'<p><strong>批准：</strong>'+esc(a.granted_by)+' · '+date(a.granted_at)+'</p>'
     +'<p class="hint">'+reportNames+'；'+deliveryText+'</p></div></article>';
 }).join('');
 return '<section class="panel"><div class="section-title"><h2>授权与撤回追溯</h2><span>'+history.length+' 次授权记录</span></div><div class="auth-history">'+rows+'</div></section>';
}

export async function results(id){
 workspace.jobs=await jobs.list();
 const j=id?await jobs.get(id):(workspace.jobs.find(j=>j.id===workspace.selectedJob)||workspace.jobs[0]);
 if(j&&!workspace.jobs.some(x=>x.id===j.id))workspace.jobs.push(j);
 if(!j)return heading('04 / REVIEW','结果复核','尚无分析结果。')+'<div class="empty">先到分析工作台，选择批次并提交一次计算。<a href="#/workbench">前往工作台 ↗</a></div>';
 workspace.selectedJob=j.id;const r=j.result||{};
 const isAdmin=session.user.role==='admin';
 let history=[];
 if(j.status==='completed'){
   try{history=await jobs.authorizations(j.id);}catch(e){history=[];}
 }
 const everAuthorized=history.length>0;
 const actionSheet=(j.status==='completed'
   ? (j.approved
       ? '<button class="danger" id="revoke-job">撤回使用许可</button><form id="revoke-form" class="inline-form" hidden><label>撤回原因（必填，将随授权记录永久留存）<textarea name="reason" required minlength="2" maxlength="1000" rows="3" placeholder="例如：复核发现密度带口径错误，试验结论无效"></textarea></label><div class="form-actions"><button type="submit" class="danger">确认撤回并封存</button><button type="button" class="button" id="revoke-cancel">取消</button></div></form>'
       : (everAuthorized
           ? '<button class="primary" id="approve-job">重新批准（形成新授权）</button><p class="hint">重新批准产生新的授权序号；旧授权下的简报继续封存，原分发计划不可重启，需另建新计划。</p>'
           : '<button class="primary" id="approve-job">批准此业务结论</button><p class="hint">批准后形成使用授权，结果才可进入定时分发档案。</p>'))
   : '');
 return heading('04 / REVIEW','结果复核与业务解释',j.name,'<button class="button" id="refresh-results">刷新结果 ↻</button>')
  +'<div class="result-selector"><label>分析记录<select id="select-job">'+workspace.jobs.map(x=>'<option value="'+x.id+'" '+(x.id===j.id?'selected':'')+'>'+esc(x.name)+' · '+esc(x.status)+'</option>').join('')+'</select></label>'+status(j.status)+'<span>'+date(j.created_at)+'</span>'+(j.status==='completed'?authBadge(j.approved,everAuthorized):'')+'</div>'
  +(j.status==='completed'
    ? '<section class="result-lead"><p class="eyebrow">COMPUTED FINDING</p><h2>'+esc(r.summary)+'</h2><div class="metrics">'+(r.metrics||[]).map(m=>'<div><span>'+esc(m.label)+'</span><strong>'+esc(fmt(m.value))+'<small>'+esc(m.unit||'')+'</small></strong></div>').join('')+'</div></section>'
      +'<section class="panel">'+chart(r.chart)+'</section>'
      +'<div class="two-columns"><section class="panel"><div class="section-title"><h2>业务解释</h2><span>由计算结果生成</span></div><ol class="questions">'+(r.findings||[]).map(v=>'<li>'+esc(v)+'</li>').join('')+'</ol>'+(r.warnings||[]).map(v=>'<p class="warning">'+esc(v)+'</p>').join('')+'</section>'
      +'<section class="method-sheet compact"><p class="eyebrow">REPRODUCIBILITY</p><h3>计算口径与参数</h3><p>'+esc(r.method)+'</p><pre>'+esc(JSON.stringify(j.params,null,2))+'</pre>'+(isAdmin?actionSheet:'')+'<p class="hint">仅有效授权的结果可进入定时分发；撤回后相关计划停用、既有简报封存且不可下载。</p></section></div>'
      +'<section class="panel"><div class="section-title"><h2>结果明细</h2><span>'+(r.table?.rows?.length||0)+' 行</span></div>'+table(r.table?.columns||[],r.table?.rows||[])+'</section>'
      +authorizationPanel(history)
    : '<section class="panel empty">'+(j.status==='failed'?'计算失败：'+esc(j.error)+'。请返回工作台调整参数或数据。':'后台正在执行计算。点击刷新结果查看最新进展。')+'<a href="#/workbench">返回工作台 ↗</a></section>');
}

export function bindResults(refresh){
 document.querySelector('#refresh-results')?.addEventListener('click',refresh);
 document.querySelector('#select-job')?.addEventListener('change',e=>{workspace.selectedJob=Number(e.target.value);location.hash='#/results/'+e.target.value;});
 document.querySelector('#approve-job')?.addEventListener('click',async()=>{
   try{await jobs.approve(workspace.selectedJob);notify('使用授权已生效，可创建新的分发计划');await refresh();}
   catch(e){notify(e.message,true);}
 });
 const revokeBtn=document.querySelector('#revoke-job');
 const revokeForm=document.querySelector('#revoke-form');
 if(revokeBtn&&revokeForm){
   revokeBtn.addEventListener('click',()=>{revokeBtn.hidden=true;revokeForm.hidden=false;revokeForm.querySelector('textarea').focus();});
   document.querySelector('#revoke-cancel').addEventListener('click',()=>{revokeForm.hidden=true;revokeBtn.hidden=false;});
   revokeForm.addEventListener('submit',async e=>{
     e.preventDefault();
     const reason=new FormData(revokeForm).get('reason').trim();
     if(reason.length<2){notify('请填写撤回原因（至少 2 个字）',true);return;}
     const btn=revokeForm.querySelector('button[type=submit]');btn.disabled=true;
     try{
       const res=await jobs.revoke(workspace.selectedJob,reason);
       notify('使用许可已撤回；停用计划 '+res.sealed_reports.length+' 条，封存简报 '+res.sealed_deliveries.length+' 份');
       await refresh();
     }catch(e){notify(e.message,true);btn.disabled=false;}
   });
 }
}
