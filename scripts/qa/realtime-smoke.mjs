/** Real HTTP + Socket.IO privacy smoke. Only run against a disposable QA site.
 * PULSE_ADMIN_PASSWORD_FILE must reference a mode-0600 local file.
 * Uses installed frontend socket.io-client, creates unique fixtures and removes them.
 */
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
const {io}=require('socket.io-client');
const base=process.env.PULSE_HTTP_URL||'http://127.0.0.1:18016';
const site=process.env.PULSE_SITE||'pulse-qa.localhost';
const socketBase=process.env.PULSE_SOCKET_URL||'http://127.0.0.1:19016';
const suffix=Date.now().toString(36), sockets=[], created=[], follows=[];
const delay=ms=>new Promise(r=>setTimeout(r,ms));
function client(){return {cookie:'',csrf:'',async request(path,data,method=data?'POST':'GET'){
 const headers={Host:site,'X-Frappe-Site-Name':site,...(this.cookie?{Cookie:this.cookie}:{}),...(this.csrf?{'X-Frappe-CSRF-Token':this.csrf}:{})};
 if(data && !(data instanceof FormData))headers['Content-Type']='application/json';
 const r=await fetch(base+path,{method,headers,body:data?(data instanceof FormData?data:JSON.stringify(data)):undefined,redirect:'manual'});
 const cookies=r.headers.getSetCookie(); if(cookies.some(c=>c.startsWith('sid='))) this.cookie=cookies.map(c=>c.split(';')[0]).join('; ');
 const body=await r.text(); let json;try{json=JSON.parse(body)}catch{}
 return {status:r.status,body,json};
},async rpc(name,data){const r=await this.request('/api/method/'+name,data);assert.equal(r.status,200,`${name}: HTTP ${r.status} ${r.json?.exc_type||''} ${r.json?.exception||''}`);return r.json.message;},async login(user,pwd){await this.rpc('login',{usr:user,pwd}); const page=await this.request('/pulse');this.csrf=page.body.match(/csrf_token["'\]\s]*[:=]\s*["']([^"']+)/)?.[1]||'';}};}
const admin=client(),member=client(),outsider=client(),guest=client();
async function create(doc){const data=await admin.rpc('frappe.client.insert',{doc}); created.push([data.doctype,data.name]);return data;}
async function socket(c){const s=io(socketBase+'/'+site,{transports:['websocket'],extraHeaders:{Cookie:c.cookie,Origin:base,'X-Frappe-Site-Name':site},reconnection:false});s.events=[];s.onAny((name,data)=>s.events.push({name,data}));sockets.push(s);await new Promise((resolve,reject)=>{s.once('connect',resolve);s.once('connect_error',reject);setTimeout(()=>reject(new Error('socket connect timeout')),8000).unref()});return s;}
async function denied(c,method,args){const r=await c.request('/api/method/'+method,args);assert.ok([403,404].includes(r.status),`${method}: expected deny got ${r.status}`);}
try{
 await admin.login('Administrator',readFileSync(process.env.PULSE_ADMIN_PASSWORD_FILE,'utf8').trim());
 const password='QA!'+crypto.randomUUID();
 const u=await create({doctype:'User',email:`pulse-rt-member-${suffix}@example.com`,first_name:'Realtime Member',send_welcome_email:0,new_password:password,roles:[{role:'Pulse Senior Developer'}]});
 const o=await create({doctype:'User',email:`pulse-rt-other-${suffix}@example.com`,first_name:'Realtime Outsider',send_welcome_email:0,new_password:password,roles:[{role:'Pulse Senior Developer'}]});
 const companies=await admin.rpc('frappe.client.get_list',{doctype:'Company',fields:['name'],limit_page_length:1});
 const project=await create({doctype:'Project',project_name:`Realtime QA ${suffix}`,company:companies[0].name,users:[{user:u.name,welcome_email_sent:1}]});
 const task=await create({doctype:'Task',subject:`Realtime QA task ${suffix}`,project:project.name});
 await member.login(u.name,password);await outsider.login(o.name,password);
 const ms=await socket(member), os=await socket(outsider);
 await member.rpc('pulse.api.personal.remember',{doctype:'Task',name:task.name,kind:'Follow'}); follows.push(task.name);
 const comment=await admin.rpc('pulse.api.spa.add_comment',{task:task.name,text:`HTTP comment ${suffix}`});created.push(['Pulse Comment',comment.name]);
 await delay(1500);
 assert.ok(ms.events.some(e=>e.name==='pulse_notification'),'member missing real notification socket event');
 assert.equal(os.events.filter(e=>e.name==='pulse_notification').length,0,'outsider received private notification');
 const inbox=await member.rpc('pulse.api.personal.inbox',{});const note=inbox.find(n=>n.reference_name===task.name);assert.ok(note,'notification missing from HTTP inbox');created.push(['Pulse Notification',note.name]);
 await denied(outsider,'pulse.api.personal.mark_read',{name:note.name});
 await member.rpc('pulse.api.personal.mark_read',{name:note.name});
 await denied(outsider,'pulse.api.spa.add_comment',{task:task.name,text:'Forbidden'});
 await denied(outsider,'pulse.api.spa.list_attachments',{task:task.name});
 console.log('PASS real comment, follower inbox, mark-read isolation and recipient-only Socket.IO notification');
 const file=new FormData();file.set('doctype','Task');file.set('docname',task.name);file.set('is_private','1');file.set('file',new Blob([`Private QA ${suffix}`],{type:'text/plain'}),`qa-${suffix}.txt`);
 const upload=await member.request('/api/method/upload_file',file);assert.equal(upload.status,200,`upload: ${upload.status} ${upload.json?.exc_type}`);const attachment=upload.json.message;created.push(['File',attachment.name]);
 assert.equal(attachment.is_private,1);const content=await member.request(attachment.file_url);assert.equal(content.status,200);assert.equal(content.body,`Private QA ${suffix}`);
 for(const c of [outsider,guest]){const r=await c.request(attachment.file_url);assert.notEqual(r.status,200,'private file disclosed');assert.ok(!r.body.includes(`Private QA ${suffix}`));}
 await denied(outsider,'pulse.api.spa.delete_attachment',{name:attachment.name});
 const publicFile=new FormData();publicFile.set('doctype','Task');publicFile.set('docname',task.name);publicFile.set('is_private','0');publicFile.set('file',new Blob(['Public forbidden'],{type:'text/plain'}),`public-${suffix}.txt`);
 const publicUpload=await member.request('/api/method/upload_file',publicFile);assert.ok([403,417].includes(publicUpload.status),`public upload accepted: ${publicUpload.status}`);
 console.log('PASS multipart upload, authorized private read, outsider/guest denial and delete denial');
 const page=await admin.rpc('pulse.api.documents.save_page',{project:project.name,title:`Realtime page ${suffix}`,content:'<p>First</p>'});created.push(['Pulse Document',page.name]);
 // The member receives page events through its authenticated personal room,
 // without subscribing to the page. Outsider document subscriptions must not help.
 os.emit('doc_subscribe','Pulse Document',page.name);await delay(1500);
 const savedPage=await admin.rpc('pulse.api.documents.save_page',{project:project.name,name:page.name,modified:page.modified,title:page.title,content:'<p>Second</p>'});await delay(1500);
 const pageEventNames=['pulse_page_updated','doc_update','list_update'];
 for(const event of pageEventNames){
  assert.ok(ms.events.some(e=>e.name===event&&e.data?.name===page.name),`member missing personal-room ${event}`);
  assert.ok(!os.events.some(e=>e.name===event&&e.data?.name===page.name),`outsider received ${event} metadata`);
 }
 // Retain an authorized document-room subscription across revocation to prove
 // neither custom nor native document/list broadcasts leak metadata afterward.
 ms.emit('doc_subscribe','Pulse Document',page.name);await delay(1500);
 await denied(outsider,'pulse.api.documents.get_page',{name:page.name});
 console.log('PASS personal-room page updates: current reader receives all events; outsider receives no metadata');
 await member.rpc('pulse.api.personal.remember',{doctype:'Task',name:task.name,kind:'Follow',enabled:0}); follows.length=0;
 const latest=await admin.rpc('frappe.client.get',{doctype:'Project',name:project.name});latest.users=[];await admin.rpc('frappe.client.save',{doc:latest});
 const priorPageEvents=ms.events.filter(e=>pageEventNames.includes(e.name)&&e.data?.name===page.name).length;
 await admin.rpc('pulse.api.documents.save_page',{project:project.name,name:page.name,modified:savedPage.modified,title:page.title,content:'<p>After revocation</p>'});await delay(1500);
 assert.equal(ms.events.filter(e=>pageEventNames.includes(e.name)&&e.data?.name===page.name).length,priorPageEvents,'revoked member received page metadata');
 console.log('PASS revoked member receives no document update metadata');
 await denied(member,'pulse.api.spa.list_attachments',{task:task.name});
 const revoked=await member.request(attachment.file_url);assert.notEqual(revoked.status,200,'revoked file owner can download');assert.ok(!revoked.body.includes(`Private QA ${suffix}`));
 console.log('PASS revoked uploader denied attachment list and private download');
}finally{
 for(const s of sockets)s.disconnect();
 for(const name of follows)await member.request('/api/method/pulse.api.personal.remember',{doctype:'Task',name,kind:'Follow',enabled:0});
 // Remove fixture-owned audit/status records before the native linked documents.
 for(const [doctype,name] of created){
  const related=doctype==='Task'?['Pulse Task Status Log','task']:doctype==='Project'?['Pulse Activity Log','project']:null;
  if(!related)continue;
  const r=await admin.request('/api/method/frappe.client.get_list',{doctype:related[0],filters:{[related[1]]:name},fields:['name'],limit_page_length:0});
  for(const row of r.json?.message||[])await admin.request('/api/method/frappe.client.delete',{doctype:related[0],name:row.name});
 }
 for(const [doctype,name] of created.reverse()){const r=await admin.request('/api/method/frappe.client.delete',{doctype,name});if(r.status!==200)console.log(`CLEANUP pending ${doctype} ${name}: HTTP ${r.status}`);}
}
