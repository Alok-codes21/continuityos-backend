import {apiPatch,session} from '../services/api-client.js';
import {resultView} from './results.js';
export async function augment(el,hash,ctx,h){
 const {path,org,manager,contributor,reload,show,form,input,select,area,btn,panel,rows,bindForm,actions,esc,get,post,del}=h,p=ctx.project,user=ctx.user;
 const add=html=>el.insertAdjacentHTML('beforeend',html);
 const out=id=>`<section id="${id}" class="live-output" hidden></section>`;
 const options=items=>items.map(x=>[x.key,x.name]);
 const run=async(id,fn)=>show(el,id,await fn());
 if(hash==='#/sources'){
  const [sources,integrations]=await Promise.all([get(path('/sources')),get(org('/integrations'))]);
  add(panel('Connected integrations',rows(integrations,i=>`<strong>${esc(i.connector)}</strong><p>${esc(i.status)}</p>${resultView({permissions:i.scopes,created_at:i.created_at})}${p.role==='admin'&&i.status==='active'?btn('Revoke connection','revoke',i.id):''}`))+out('source-tools-result'));

  if(manager)add(panel('Delete all records from a source',form('purge-source',select('source','Source to purge',sources.map(s=>[s.id,s.name])),'Permanently delete source records')+out('purge-result')));
  // Contributor scope requests follow the backend approval workflow rather than changing source access directly.
  if(contributor)add(panel('Request source scope review',form('scope-request',select('selection_id','Selected source',sources.flatMap(s=>s.selections.map(t=>[t.id,s.name])))+select('included','Requested inclusion',[['false','Exclude'],['true','Include']])+input('reason','Scope review reason'),'Request scope review')+out('scope-result')));
  bindForm(el,'purge-source',async d=>{if(confirm('Permanently delete every record from this source?')){const r=await del(path(`/sources/${d.source}/records`));const owner=el.parentElement;await reload();show(owner,'purge-result',r);}});
  bindForm(el,'scope-request',d=>run('scope-result',()=>post(path('/scope-changes'),{...d,included:d.included==='true'})));
  actions(el,{revoke:async id=>{if(confirm('Revoke this integration? Previously imported records remain until deleted.')){await del(org(`/integrations/${id}`));await reload();}}});
  // Add explicit record buttons rather than expecting people to copy an ID.
  const records=await get(path('/records'));add(panel('Read more stored records',form('record-limit',input('limit','Record list limit','number','100'),'Load record list')+out('more-records')));bindForm(el,'record-limit',d=>run('more-records',()=>get(path(`/records?limit=${encodeURIComponent(d.limit)}`))));add(panel('Stored record content',rows(records,r=>`<strong>${esc(r.title)}</strong>${btn('Read record content','record-open',r.id)}`)+out('record-detail')));actions(el,{'record-open':id=>run('record-detail',()=>get(path(`/records/${id}`)))});
 }
 if(hash==='#/uncertainty-ledger'){add(panel('Search backend claims',form('claim-query',input('q','Search text','search','',false)+input('status','Claim status filter','text','',false)+input('category','Claim category filter','text','',false),'Search claims')+out('query-claims')));bindForm(el,'claim-query',d=>run('query-claims',()=>get(path('/claims?'+new URLSearchParams(Object.entries(d).filter(([,v])=>v)).toString()))));add(panel('Read earlier ledger entries',form('ledger-page',input('before_seq','Before sequence','number')+input('limit','Maximum entries','number','100'),'Read earlier entries')+out('earlier-ledger')));bindForm(el,'ledger-page',d=>run('earlier-ledger',()=>get(path(`/ledger?before_seq=${encodeURIComponent(d.before_seq)}&limit=${encodeURIComponent(d.limit)}`))));}
 if(hash==='#/uncertainty-ledger'&&manager){
  add(panel('Knowledge maintenance',btn('Re-analyse evidence','analyse')+btn('Verify ledger integrity','verify-ledger')+out('maintenance-result')));
  actions(el,{analyse:async()=>{const r=await post(path('/analyse'));const owner=el.parentElement;await reload();show(owner,'maintenance-result',r);},'verify-ledger':()=>run('maintenance-result',()=>get(path('/ledger/verify')))});
 }
 if(hash==='#/knowledge-graph'&&manager){const ps=await get(path('/graph/people'));if(ps.length>1){add(panel('Merge duplicate identities','<p>Only merge identifiers confirmed to be the same person. This changes the documented identity graph.</p>'+form('merge-people',select('keep','Keep identity',options(ps))+select('merge','Merge identity',options(ps)),'Merge identities')+out('merge-result')));bindForm(el,'merge-people',async d=>{if(d.keep===d.merge)throw Error('Select two different identities.');if(confirm('Merge these identities permanently?')){await post(path('/graph/people/merge'),d);await reload();}});}}
 if(hash==='#/impact-simulator'&&manager){const [risk,history]=await Promise.all([get(path('/risk/people')),get(path('/simulations'))]);add(panel('People risk',resultView(risk))+panel('Simulation history',resultView(history)));}
 if(hash==='#/rehearsal'){
  add(panel('Read a previous rehearsal session',form('resume-session',input('id','Rehearsal session reference'),'Read session history')+out('session-history')));bindForm(el,'resume-session',d=>run('session-history',()=>get(path(`/rehearsal/${encodeURIComponent(d.id)}`))));
 }
 if(hash==='#/security'&&manager){add(panel('Extended audit history',form('audit-limit',input('limit','Audit entry limit','number','100'),'Read audit entries')+out('extended-audit')));bindForm(el,'audit-limit',d=>run('extended-audit',()=>get(org(`/audit?limit=${encodeURIComponent(d.limit)}`))));add(panel('Service readiness',btn('Check service health','service-health')+out('service-health')));actions(el,{'service-health':()=>run('service-health',async()=>({health:await get('/health'),readiness:await get('/ready')}))});}
 if(hash==='#/settings'){
  add(panel('Session security',btn('Revoke all sessions','revoke-sessions')));actions(el,{'revoke-sessions':async()=>{if(confirm('Sign out every session for this account?')){await post('/auth/revoke-all-sessions');session.token=null;window.dispatchEvent(new Event('session-expired'));}}});
  if(manager){const members=await get(org('/members'));if(p.role!=='admin'){add(panel('Project membership',form('manager-project-member',select('user_id','Member to add',members.map(m=>[m.user_id,m.name])),'Add project member')));bindForm(el,'manager-project-member',d=>post(path('/members'),d));}
   if(p.role==='admin'){add(panel('Edit organisation roles',form('edit-role',select('user_id','Member to change',members.map(m=>[m.user_id,`${m.name} (${m.role})`]))+select('role','New organisation role',[['contributor','Contributor'],['manager','Manager'],['incoming','Incoming'],['admin','Admin']]),'Save member role')+out('role-result')));bindForm(el,'edit-role',async d=>{await apiPatch(org(`/members/${d.user_id}`),{role:d.role});await ctx.refresh();});}}
 }
 if(hash==='#/handover-centre'&&manager){add(panel('Approval history',form('approval-history',select('status','Approval status',[['approved','Approved'],['rejected','Rejected'],['pending','Pending']]),'Load approval history')+out('approval-history-result')));bindForm(el,'approval-history',d=>run('approval-history-result',()=>get(path(`/approvals?status=${d.status}`))));}
 if(hash==='#/sources'&&!el.querySelector('#source select')?.options.length)el.querySelector('[data-action=discover]')?.remove();
 // Hide forms without a valid selectable value, instead of offering impossible actions.
 el.querySelectorAll('form').forEach(f=>{if([...f.querySelectorAll('select')].some(s=>s.options.length===0)){f.hidden=true;const n=document.createElement('p');n.className='muted';n.textContent='No eligible records for this action.';f.after(n);}});
}
