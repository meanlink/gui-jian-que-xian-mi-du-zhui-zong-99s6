import {jobs,reports} from '../api/entities.js';
import {download} from '../api/client.js';
import {workspace} from '../stores/workspace.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {esc,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';

function scheduleArticle(r){
 if(r.sealed){
   return '<article class="sealed">'
     +'<div><strong>'+esc(r.name)+'</strong><span class="seal-tag">已封存 · 许可撤回</span>'
     +'<p>'+esc(r.destination)+'</p>'
     +(r.sealed_reason?'<small>撤回原因：'+esc(r.sealed_reason)+'</small>':'<small>依据的使用许可已撤回</small>')
     +'<small>封存时间 '+date(r.sealed_at)+'</small></div>'
     +'<button class="button small" disabled title="许可撤回后原计划不可重启">不可重启</button></article>';
 }
 return '<article><div><strong>'+esc(r.name)+'</strong><p>'+esc(r.destination)+'</p><small>下次 '+date(r.next_run)+' · 周期 '+r.interval_seconds+' 秒</small></div>'
   +'<button class="button small" data-toggle="'+r.id+'" '+(session.user.role!=='admin'?'disabled':'')+'>'+(r.enabled?'暂停':'启用')+'</button></article>';
}

function deliveryRow(d){
 const controls=d.sealed
   ? '<span class="seal-tag">已封存</span><button class="text-button" disabled title="许可撤回后仅保留查证记录，禁止下载">下载已禁用</button>'
   : '<button class="text-button" data-download="'+d.id+'" data-format="csv">CSV ↓</button><button class="text-button" data-download="'+d.id+'" data-format="json">JSON ↓</button>';
 return '<div class="delivery'+(d.sealed?' sealed':'')+'"><div><strong>'+esc(d.filename)+'</strong>'
   +(d.sealed?'<span class="seal-tag">使用许可撤回 · 保留查证</span>':'')
   +'<p>'+esc(d.destination)+' · '+date(d.created_at)+'</p><small>SHA256 '+esc(d.checksum.slice(0,24))+'…</small></div>'
   +'<div>'+controls+'</div></div>';
}

export async function reportPage(){
 const [list,deliveries,allJobs]=await Promise.all([reports.list(),reports.deliveries(),jobs.list()]);
 workspace.reports=list;
 // 只有当前持有有效授权（approved）的已完成结果才能建新计划
 const approved=allJobs.filter(j=>j.approved&&j.status==='completed');
 const sealedCount=list.filter(r=>r.sealed).length;
 const sealedDeliveries=deliveries.filter(d=>d.sealed).length;
 return heading('05 / DISTRIBUTION','定时分发与归档','把有效授权的结果交付到本地业务收件箱。许可撤回后计划封存、简报保留查证但禁止下载。','<button class="button" id="refresh-reports">刷新收件箱 ↻</button>')
  +'<div class="report-grid"><section class="panel"><div class="section-title"><h2>创建分发计划</h2></div>'
  +'<form id="report-form"><label>简报名称<input name="name" required minlength="2" value="日间业务复核简报"></label>'
  +'<label>有效授权分析<select name="job_id" required '+(approved.length?'':'disabled')+'>'
  +(approved.length?approved.map(j=>'<option value="'+j.id+'">'+esc(j.name)+'</option>').join(''):'<option value="">暂无有效授权的分析结果</option>')+'</select></label>'
  +'<label>业务接收组<input name="destination" value="业务复核组 · 本地收件箱" required></label>'
  +'<div class="parameter-grid"><label>分发周期<select name="interval_seconds"><option value="86400">每日</option><option value="604800">每周</option><option value="60">每分钟（验收）</option></select></label>'
  +'<label>首次执行<select name="delay_seconds"><option value="0">立即</option><option value="60">1 分钟后</option><option value="3600">1 小时后</option></select></label></div>'
  +'<button type="submit" class="primary" '+(session.user.role!=='admin'||!approved.length?'disabled':'')+'>保存分发计划</button></form>'
  +'<p class="hint">计划绑定创建时的使用授权。授权被撤回后计划立即封存且不可重启；重新批准只产生新授权，需另建新计划。</p></section>'
  +'<section><div class="section-title"><h2>分发计划</h2><span>'+list.filter(r=>r.enabled).length+' 条启用 · '+sealedCount+' 条封存</span></div>'
  +'<div class="schedule-list">'+list.map(scheduleArticle).join('')+'</div>'
  +'<section class="panel inbox"><div class="section-title"><h2>本地收件箱</h2><span>'+deliveries.length+' 份归档 · '+sealedDeliveries+' 份封存</span></div>'
  +deliveries.map(deliveryRow).join('')
  +(!deliveries.length?'<p class="empty">计划执行后，文件会出现在此处。等待片刻后刷新。</p>':'')
  +(sealedDeliveries?'<p class="hint">封存简报保留全部查证信息（时间、指纹、目标组），但任何下载请求都会被拒绝。</p>':'')
  +'</section></section></div>';
}

export function bindReports(refresh){
 document.querySelector('#refresh-reports').onclick=refresh;
 submit(document.querySelector('#report-form'),async f=>{
   await reports.create({name:f.get('name'),job_id:Number(f.get('job_id')),destination:f.get('destination'),interval_seconds:Number(f.get('interval_seconds')),delay_seconds:Number(f.get('delay_seconds'))});
   notify('计划已保存，后台将按到期时间归档');await refresh();
 });
 document.querySelectorAll('[data-toggle]').forEach(b=>b.onclick=async()=>{
   try{await reports.toggle(b.dataset.toggle);await refresh();}catch(e){notify(e.message,true);}
 });
 document.querySelectorAll('[data-download]').forEach(b=>b.onclick=()=>
   download(b.dataset.download,b.dataset.format).catch(e=>notify(e.message,true)));
}
