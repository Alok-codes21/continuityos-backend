import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import './styles/global.css';
import './styles/layout.css';
import './styles/components.css';
import './live/live.css';
import { renderSidebar, initSidebar } from './components/sidebar.js';
import { apiGet, apiPost, session } from './services/api-client.js';
import { renderLive, esc } from './live/pages.js';
let projects=[], user=null, epoch=0;
const app=document.getElementById('app');
function error(el,e){el.textContent=e.message;el.hidden=false;}
function logout(){session.token=null;session.projectId='';user=null; mount();}
function login(){
 app.innerHTML=`<main class="auth-wrap"><section class="cos-card auth-card"><div class="brand-title">Continuity<span>OS</span></div><p>Preserve knowledge. Keep the evidence.</p><h1>Welcome to your workspace</h1><div class="alert alert-danger" id="auth-error" role="alert" hidden></div><form id="auth-form"><label>Work email<input name="email" type="email" required autocomplete="username"></label><label>Password<input name="password" type="password" required minlength="10" autocomplete="current-password"></label><div id="registration" hidden><label>Your name<input name="name"></label><label>Organisation name<input name="org_name"></label></div><button class="cos-btn cos-btn-primary" type="submit">Sign in</button><button type="button" class="cos-btn cos-btn-secondary" id="register-toggle">Create an account</button></form><p class="muted mt-3">Live FastAPI workspace. No sample data is loaded.</p></section></main>`;
 let registering=false;
 document.getElementById('register-toggle').onclick=()=>{registering=!registering;document.getElementById('registration').hidden=!registering;document.querySelector('[type=submit]').textContent=registering?'Register':'Sign in';};
 document.getElementById('auth-form').onsubmit=async e=>{e.preventDefault();const b=e.target.querySelector('[type=submit]');b.disabled=true;try{const data=Object.fromEntries(new FormData(e.target));const result=await apiPost(registering?'/auth/register':'/auth/login',data);session.token=result.token;await mount();}catch(err){error(document.getElementById('auth-error'),err);}finally{b.disabled=false;}};
}
async function page(){
 const current=++epoch, el=document.getElementById('page-content');if(!el)return;
 document.querySelector('.sidebar')?.classList.remove('mobile-open');document.querySelector('.sidebar-overlay')?.classList.remove('active');
 document.querySelectorAll('.sidebar-nav-item').forEach(n=>n.classList.toggle('active',n.getAttribute('href')===(location.hash||'#/overview')));
 el.innerHTML='<div class="loading-state">Loading live project data...</div>';
 const selected=projects.find(p=>p.id===session.projectId);if(document.querySelector('.sidebar-user-role'))document.querySelector('.sidebar-user-role').textContent=selected?.role||'Member';if(document.querySelector('.sidebar-org'))document.querySelector('.sidebar-org').textContent=user?.orgs.find(o=>o.org_id===selected?.org_id)?.name||'Connected organisation';
 const surface=document.createElement('div');el.replaceChildren(surface);
 try{await renderLive(surface,location.hash||'#/overview',{project:projects.find(p=>p.id===session.projectId),user,refresh:mount});}catch(e){if(current!==epoch)return;el.replaceChildren();const box=document.createElement('div');box.className='alert alert-danger';box.textContent=e.message;el.append(box);}
}
async function mount(){
 if(!session.token){login();return;}
 try{user=await apiGet('/auth/me');projects=await apiGet('/projects');if(!projects.some(p=>p.id===session.projectId))session.projectId=projects[0]?.id||'';
 app.innerHTML=`<div class="app-layout">${renderSidebar()}<div class="main-area" id="main-area"><header class="topbar"><div class="d-flex gap-3 align-items-center"><button id="nav-toggle" class="cos-btn cos-btn-secondary" aria-label="Toggle navigation"><i class="bi bi-list"></i></button><span class="live-label">LIVE WORKSPACE</span><select id="project-picker" aria-label="Current project">${projects.map(p=>`<option value="${esc(p.id)}" ${p.id===session.projectId?'selected':''}>${esc(p.name)} (${esc(p.role)})</option>`).join('')||'<option>No projects</option>'}</select></div><div class="d-flex gap-3 align-items-center"><button id="refresh" class="cos-btn cos-btn-secondary">Refresh data</button><span>${esc(user.name)}</span><button id="signout" class="cos-btn cos-btn-secondary">Sign out</button></div></header><main class="page-content" id="page-content"></main></div></div>`;
 initSidebar();document.querySelector('.sidebar-user-name')?.replaceChildren(document.createTextNode(user.name));
 document.getElementById('refresh').onclick=page;document.getElementById('signout').onclick=logout;document.getElementById('project-picker').onchange=e=>{session.projectId=e.target.value;page();};document.getElementById('nav-toggle').onclick=()=>{const open=document.querySelector('.sidebar').classList.toggle('mobile-open');document.querySelector('.sidebar-overlay').classList.toggle('active',open);};
 document.querySelector('.sidebar-user-role').textContent=projects.find(p=>p.id===session.projectId)?.role||'Member';document.querySelector('.sidebar-org').textContent=user.orgs.find(o=>o.org_id===projects.find(p=>p.id===session.projectId)?.org_id)?.name||'Connected organisation';await page();
 }catch(e){if(!session.token)login();else{app.innerHTML='<main class="auth-wrap"><div class="cos-card auth-card"><h1>Workspace could not load</h1><p id="load-error"></p><button id="retry">Retry</button><button id="leave">Sign out</button></div></main>';document.getElementById('load-error').textContent=e.message;document.getElementById('retry').onclick=mount;document.getElementById('leave').onclick=logout;}}
}
window.addEventListener('hashchange',page);window.addEventListener('session-expired',logout);mount();
