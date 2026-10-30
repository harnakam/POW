#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createHash, randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const CRITERIA = ['hierarchy', 'identity', 'consistency', 'usability', 'accessibility'];
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const fail = (message) => { throw new Error(message); };
const inside = (root, target) => { const rel = path.relative(root, target); return rel && !rel.startsWith(`..${path.sep}`) && rel !== '..' && !path.isAbsolute(rel); };
const escape = (s) => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function parse(argv) {
  const [command = 'help', ...rest] = argv, args = {};
  for (let i = 0; i < rest.length; i++) {
    const key = rest[i];
    if (!['--root', '--brief', '--round', '--browser', '--url', '--review'].includes(key) || args[key.slice(2)] !== undefined || !rest[i + 1] || rest[i + 1].startsWith('--')) fail(`Unknown, repeated or incomplete option: ${key}`);
    args[key.slice(2)] = rest[++i];
  }
  return { command, args };
}

async function regular(file) {
  const stat = await fs.lstat(file);
  if (!stat.isFile() || stat.isSymbolicLink()) fail(`Expected a regular file: ${file}`);
  return stat;
}
async function json(file) {
  if ((await regular(file)).size > 2 * 1024 * 1024) fail(`JSON input exceeds 2 MiB: ${file}`);
  return JSON.parse(await fs.readFile(file, 'utf8'));
}
async function safeChild(root, relative, mustExist = true) {
  if (typeof relative !== 'string' || !relative || path.isAbsolute(relative) || relative.includes('\\') || relative.includes(':')) fail('Use a nonempty repository-relative path with / separators');
  const target = path.resolve(root, relative);
  if (!inside(root, target) || relative.split('/').some(x => !x || x === '.' || x === '..' || x.toLowerCase() === '.git' || x.toLowerCase() === '.pow')) fail(`Unsafe source path: ${relative}`);
  let part = root;
  for (const name of relative.split('/')) {
    part = path.join(part, name);
    try { if ((await fs.lstat(part)).isSymbolicLink()) fail(`Symlink is not a source boundary: ${relative}`); }
    catch (error) { if (!mustExist && error.code === 'ENOENT') break; throw error; }
  }
  if (mustExist) await regular(target);
  return target;
}
async function stateDir(root) {
  let dir = root;
  for (const name of ['.pow', 'design-reasoning']) {
    dir = path.join(dir, name);
    try { const stat = await fs.lstat(dir); if (!stat.isDirectory() || stat.isSymbolicLink()) fail(`Unsafe state directory: ${dir}`); }
    catch (error) { if (error.code !== 'ENOENT') throw error; await fs.mkdir(dir); }
  }
  return dir;
}
async function save(dir, state) {
  const temp = path.join(dir, `state-${randomUUID()}.tmp`);
  await fs.writeFile(temp, JSON.stringify(state, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  await fs.rename(temp, path.join(dir, 'state.json'));
}
async function sourceIdentity(root, brief) {
  const entries = [];
  for (const relative of brief.sourcePaths) entries.push([relative, sha(await fs.readFile(await safeChild(root, relative)))]);
  return sha(JSON.stringify(entries));
}
function validateBrief(brief) {
  for (const key of ['goal', 'audience', 'primaryAction', 'direction', 'implementer']) if (typeof brief[key] !== 'string' || !brief[key].trim()) fail(`Brief requires ${key}`);
  if (!Array.isArray(brief.sourcePaths) || !brief.sourcePaths.length || brief.sourcePaths.length > 64 || new Set(brief.sourcePaths).size !== brief.sourcePaths.length) fail('sourcePaths needs 1..64 distinct files');
  if (!Array.isArray(brief.preserve) || brief.preserve.some(x => typeof x !== 'string' || !x.trim())) fail('preserve must list the behaviors/design decisions to retain');
  brief.maxRounds ??= 3;
  if (!Number.isInteger(brief.maxRounds) || brief.maxRounds < 1 || brief.maxRounds > 5) fail('maxRounds must be 1..5');
  brief.viewports ??= [{ id: 'desktop', width: 1280, height: 800 }, { id: 'mobile', width: 390, height: 844 }];
  if (!Array.isArray(brief.viewports) || brief.viewports.length < 1 || brief.viewports.length > 4) fail('Use 1..4 viewports');
  const ids = new Set();
  for (const v of brief.viewports) {
    if (!/^[a-z][a-z0-9-]{0,30}$/.test(v.id) || ids.has(v.id) || !Number.isInteger(v.width) || !Number.isInteger(v.height) || v.width < 320 || v.width > 2560 || v.height < 240 || v.height > 2160) fail('Invalid or duplicate viewport');
    ids.add(v.id);
  }
  brief.interactions ??= [];
  if (!Array.isArray(brief.interactions) || brief.interactions.length > 12 || (!brief.staticSurface && !brief.interactions.length)) fail('Interactive surfaces need 1..12 actual interaction steps; staticSurface is for noninteractive pages');
  for (const step of brief.interactions) {
    if (!['click', 'fill', 'press'].includes(step.action) || typeof step.selector !== 'string' || !step.selector || typeof step.expect?.selector !== 'string' || typeof step.expect?.textIncludes !== 'string' || !step.expect.textIncludes) fail('Each interaction needs action, selector, and expect {selector,textIncludes}');
    if (step.action === 'fill' && typeof step.value !== 'string') fail('fill requires value');
    if (step.action === 'press' && !['Enter', 'Escape', 'Tab', 'Space'].includes(step.key)) fail('press supports Enter, Escape, Tab, Space');
  }
}

class CDP {
  constructor(socket) {
    this.socket = socket; this.next = 0; this.pending = new Map(); this.documents = [];
    socket.addEventListener('message', event => {
      let m; try { m = JSON.parse(event.data); } catch { return; }
      if (m.method === 'Network.responseReceived' && m.params.type === 'Document') {
        this.documents.push({frame:m.params.frameId,loader:m.params.loaderId,status:m.params.response.status});
        if(this.documents.length>128)this.documents.shift();
      }
      if (!this.pending.has(m.id)) return;
      const item = this.pending.get(m.id); this.pending.delete(m.id); clearTimeout(item.timer);
      m.error ? item.reject(new Error(m.error.message)) : item.resolve(m.result);
    });
    socket.addEventListener('close', () => { for (const p of this.pending.values()) { clearTimeout(p.timer); p.reject(new Error('Browser connection closed')); } this.pending.clear(); });
  }
  static async open(url) {
    if (typeof WebSocket === 'undefined') fail('Browser capture requires Node 22+ for its built-in WebSocket; no package is installed');
    const socket = new WebSocket(url);
    await new Promise((resolve, reject) => { const timer = setTimeout(() => { socket.close(); reject(new Error('Browser connection timeout')); }, 8000); socket.addEventListener('open', () => { clearTimeout(timer); resolve(); }, { once: true }); socket.addEventListener('error', () => { clearTimeout(timer); reject(new Error('Browser connection failed')); }, { once: true }); });
    return new CDP(socket);
  }
  send(method, params = {}) {
    return new Promise((resolve, reject) => { const id = ++this.next; const timer = setTimeout(() => { this.pending.delete(id); reject(new Error(`Browser operation timed out: ${method}`)); }, 10000); this.pending.set(id, { resolve, reject, timer }); this.socket.send(JSON.stringify({ id, method, params })); });
  }
  async evaluate(expression, awaitPromise = false) {
    const result = await this.send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true });
    if (result.exceptionDetails) fail(result.exceptionDetails.text || 'Page evaluation failed');
    return result.result?.value;
  }
  close() { this.socket.close(); }
}

const AUDIT = `(() => {
 const visible = e => { const r=e.getBoundingClientRect(),s=getComputedStyle(e); return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'; };
 const name = e => e.getAttribute('aria-label') || (e.getAttribute('aria-labelledby')||'').split(/\\s+/).map(id=>document.getElementById(id)?.textContent||'').join(' ').trim() || Array.from(e.labels||[]).map(x=>x.textContent).join(' ').trim() || e.getAttribute('alt') || e.getAttribute('title') || (e.matches('button,a')?e.textContent.trim():'') || (e.matches('input[type=submit],input[type=button]')?e.value:'');
 const controls=Array.from(document.querySelectorAll('button,a[href],input:not([type=hidden]),select,textarea,[role=button]')).filter(visible);
 return {url:location.href,title:document.title,viewport:{width:innerWidth,height:innerHeight},horizontalOverflow:document.documentElement.scrollWidth>innerWidth+1,unnamedControls:controls.filter(e=>!name(e)).slice(0,30).map(e=>({tag:e.tagName,id:e.id,role:e.getAttribute('role')})),controlCount:controls.length,headings:Array.from(document.querySelectorAll('h1,h2,h3')).slice(0,30).map(e=>({level:e.tagName,text:e.textContent.trim()})),coverage:'DOM name/overflow observations only; not a full accessibility or aesthetic audit'};
})()`;

async function interaction(cdp, step) {
  const target = await cdp.evaluate(`(() => { const e=document.querySelector(${JSON.stringify(step.selector)}); if(!e) return null; e.scrollIntoView({block:'center'}); e.focus(); const r=e.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2,width:r.width,height:r.height}; })()`);
  if (!target || !target.width || !target.height) return { ...step, passed: false, observed: 'Target absent or not visible' };
  if (step.action === 'click') {
    await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: target.x, y: target.y, button: 'left', clickCount: 1 });
    await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: target.x, y: target.y, button: 'left', clickCount: 1 });
  } else if (step.action === 'fill') {
    await cdp.evaluate(`(() => {const e=document.querySelector(${JSON.stringify(step.selector)}); if('value' in e){e.value='';e.dispatchEvent(new Event('input',{bubbles:true}));}})()`);
    await cdp.send('Input.insertText', { text: step.value });
  } else {
    const key = step.key === 'Space' ? ' ' : step.key;
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: step.key, windowsVirtualKeyCode: ({ Enter:13, Escape:27, Tab:9, Space:32 })[step.key] });
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: step.key });
  }
  const deadline = Date.now() + 3000; let observed = '';
  do {
    observed = await cdp.evaluate(`document.querySelector(${JSON.stringify(step.expect.selector)})?.textContent ?? ''`);
    if (observed.includes(step.expect.textIncludes)) return { ...step, passed: true, observed: observed.slice(0,2000) };
    await new Promise(r => setTimeout(r, 100));
  } while (Date.now() < deadline);
  return { ...step, passed: false, observed: observed.slice(0,2000) };
}

async function collect(browser, url, viewports, steps, dir, round) {
  const endpoint = new URL(url);
  if (!['http:', 'https:'].includes(endpoint.protocol) || endpoint.username || endpoint.password) fail('Capture requires an http(s) URL without embedded credentials');
  const executable = await fs.realpath(browser); await regular(executable);
  const tempBase = await fs.realpath(os.tmpdir()), profile = await fs.mkdtemp(path.join(tempBase, 'pow-design-browser-'));
  const child = spawn(executable, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore','ignore','pipe'], windowsHide: true, detached: process.platform !== 'win32' });
  let startupError, diagnostic = ''; child.on('error', e => { startupError = e; }); child.stderr.on('data', b => { if (diagnostic.length < 8000) diagnostic += b.toString().slice(0,8000-diagnostic.length); });
  let cdp;
  try {
    const deadline = Date.now() + 20000; let port;
    while (Date.now() < deadline) {
      if (startupError) throw startupError;
      if (child.exitCode !== null) fail(`Browser exited ${child.exitCode}: ${diagnostic}`);
      try { port = Number((await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]); if (port > 0) break; } catch {}
      await new Promise(r => setTimeout(r,100));
    }
    if (!port) fail(`Browser startup timed out: ${diagnostic}`);
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`, { signal: AbortSignal.timeout(5000) })).json();
    const page = targets.find(x=>x.type==='page'); if (!page) fail('Browser has no page target');
    cdp = await CDP.open(page.webSocketDebuggerUrl);
    await cdp.send('Page.enable'); await cdp.send('Runtime.enable'); await cdp.send('Network.enable');
    const captures = {};
    for (const v of viewports) {
      await cdp.send('Emulation.setDeviceMetricsOverride', { width:v.width,height:v.height,deviceScaleFactor:1,mobile:v.width<600 });
      cdp.documents = [];
      const navigation = await cdp.send('Page.navigate',{url});
      if (navigation.errorText) fail(`Navigation failed: ${navigation.errorText}`);
      const readyDeadline = Date.now()+12000; let ready=false;
      do {
        const tree=await cdp.send('Page.getFrameTree');
        ready=tree.frameTree.frame.id===navigation.frameId && (!navigation.loaderId||tree.frameTree.frame.loaderId===navigation.loaderId) && await cdp.evaluate(`location.href!=='about:blank' && document.readyState==='complete'`);
        if(ready) break; await new Promise(r=>setTimeout(r,100));
      } while(Date.now()<readyDeadline);
      if (!ready) fail('Page did not finish navigation before timeout');
      await cdp.evaluate(`Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,1500))]).then(()=>new Promise(r=>setTimeout(r,200)))`,true);
      const actions = [];
      for (const step of steps) { const outcome=await interaction(cdp,step); actions.push(outcome); if(!outcome.passed) break; }
      await cdp.evaluate('window.scrollTo(0,0)');
      const audit=await cdp.evaluate(AUDIT);
      const document=cdp.documents.findLast(x=>x.frame===navigation.frameId&&(!navigation.loaderId||x.loader===navigation.loaderId));
      if(!document) fail('No main-frame document response was observed; navigation cannot be verified');
      const image=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      const bytes=Buffer.from(image.data,'base64'), relative=`${round}-${v.id}.png`;
      if(bytes.length>16*1024*1024 || !bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) fail('Invalid screenshot');
      await fs.writeFile(path.join(dir,relative),bytes,{flag:'wx',mode:0o600});
      captures[v.id]={image:relative,sha256:sha(bytes),width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20),httpStatus:document.status,audit,interactions:actions};
    }
    return captures;
  } finally {
    cdp?.close();
    if(child.pid && child.exitCode===null) {
      if(process.platform==='win32') { await new Promise(resolve=>{const killer=spawn('taskkill',['/pid',String(child.pid),'/T','/F'],{stdio:'ignore',windowsHide:true});killer.on('error',resolve);killer.on('exit',resolve);setTimeout(resolve,3000);}); }
      else { try {process.kill(-child.pid,'SIGKILL');} catch {} }
    }
    if(inside(tempBase,profile)&&path.basename(profile).startsWith('pow-design-browser-')) await fs.rm(profile,{recursive:true,force:true,maxRetries:2}).catch(()=>{});
  }
}

async function assess(root,dir,state) {
  const candidate=state.rounds.filter(x=>x.id!=='baseline').at(-1);
  const reasons=[];
  if(!candidate) return {status:'needs-capture',reasons:['No candidate screenshots'],rounds:state.rounds.length,maxRounds:state.brief.maxRounds};
  if(candidate.source!==await sourceIdentity(root,state.brief)) reasons.push('Candidate evidence is stale after a source change');
  if(!state.brief.newSurface && !state.rounds.find(x=>x.id==='baseline')) reasons.push('Existing surfaces require a baseline');
  for(const round of state.rounds) for(const capture of Object.values(round.captures)) {
    await regular(path.join(dir,capture.image));
    if(sha(await fs.readFile(path.join(dir,capture.image)))!==capture.sha256) reasons.push(`Screenshot changed: ${capture.image}`);
  }
  for(const v of state.brief.viewports) {
    const c=candidate.captures[v.id]; if(!c){reasons.push(`Missing viewport ${v.id}`);continue;}
    if(c.width!==v.width || c.height!==v.height) reasons.push(`Screenshot dimensions differ from viewport ${v.id}`);
    if(c.audit.viewport.width!==v.width) reasons.push(`Layout viewport expanded beyond the requested width on ${v.id}`);
    if(c.httpStatus>=400) reasons.push(`HTTP error ${c.httpStatus} on ${v.id}`);
    if(c.audit.horizontalOverflow) reasons.push(`Page overflows horizontally on ${v.id}`);
    if(c.audit.unnamedControls.length) reasons.push(`Unnamed controls on ${v.id}`);
    if(!state.brief.staticSurface && (c.interactions.length!==state.brief.interactions.length || c.interactions.some(x=>!x.passed))) reasons.push(`Interaction incomplete or failed on ${v.id}`);
  }
  if(!candidate.review) reasons.push('Independent visual review is missing');
  else {
    if(candidate.review.criteria.some(x=>x.status!=='pass') || candidate.review.preserved.some(x=>x.status!=='pass') || candidate.review.issues.some(x=>x.blocking)) reasons.push('Reviewer reports unresolved quality/preservation issues');
  }
  const exhausted=state.rounds.filter(x=>x.id!=='baseline').length>=state.brief.maxRounds;
  return {status:reasons.length?(exhausted?'blocked':'needs-improvement'):'complete',round:candidate.id,reasons,rounds:state.rounds.filter(x=>x.id!=='baseline').length,maxRounds:state.brief.maxRounds,limits:'DOM/interaction observations are executed. Visual judgments and reviewer independence are externally supplied, not authenticated or reduced to an objective beauty score. Coverage is limited to named files, URL, viewports, and interaction steps.'};
}

async function review(dir,state,file,id) {
  const round=state.rounds.find(x=>x.id===id); if(!round) fail('Unknown round');
  const r=await json(file);
  if(typeof r.reviewer!=='string'||!r.reviewer.trim()||r.reviewer===state.brief.implementer) fail('Review requires a distinct identified reviewer');
  if(r.round!==id || !Array.isArray(r.criteria) || r.criteria.length!==CRITERIA.length || new Set(r.criteria.map(x=>x.id)).size!==CRITERIA.length || CRITERIA.some(id=>!r.criteria.some(x=>x.id===id))) fail(`Review must cover exactly: ${CRITERIA.join(', ')}`);
  if(!Array.isArray(r.preserved)||r.preserved.length!==state.brief.preserve.length||new Set(r.preserved.map(x=>x.requirement)).size!==state.brief.preserve.length||state.brief.preserve.some(p=>!r.preserved.some(x=>x.requirement===p))) fail('Review must cover every preservation requirement exactly once');
  for(const x of [...r.criteria,...r.preserved]) if(!['pass','needs-work','blocked'].includes(x.status)||typeof x.evidence!=='string'||!x.evidence.trim()||typeof x.viewport!=='string'||!round.captures[x.viewport]) fail('Each review finding needs status, visual evidence, and a captured viewport');
  if(!Array.isArray(r.issues)||r.issues.length>50||r.issues.some(x=>typeof x.message!=='string'||typeof x.blocking!=='boolean')) fail('issues must be bounded {message,blocking} observations');
  for(const v of state.brief.viewports) if(r.screenshots?.[v.id]!==round.captures[v.id]?.sha256) fail(`Review is not bound to current screenshot: ${v.id}`);
  round.review={...r,recordedAt:new Date().toISOString(),verification:'Declared external reviewer; CLI checks identity difference and evidence binding, not authenticity of their opinion'};
  await save(dir,state);
}

async function render(root,dir,state) {
  const status=await assess(root,dir,state);
  const cards=state.rounds.map(r=>`<section><h2>${escape(r.id)}</h2><p>Source ${escape(r.source)}</p><div class="screens">${Object.entries(r.captures).map(([id,c])=>`<figure><figcaption>${escape(id)} ${c.width}×${c.height}</figcaption><img src="${escape(c.image)}" alt="${escape(r.id+' '+id)}"><details><summary>Executed observations</summary><pre>${escape(JSON.stringify({audit:c.audit,interactions:c.interactions},null,2))}</pre></details></figure>`).join('')}</div><h3>Review</h3><pre>${escape(JSON.stringify(r.review??'Pending',null,2))}</pre></section>`).join('');
  const html=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>POW design evidence</title><style>body{font:16px/1.6 system-ui;margin:2rem;color:#202326;background:#fff}main{max-width:1200px;margin:auto}.screens{display:flex;gap:2rem;align-items:start;flex-wrap:wrap}figure{margin:0;flex:1 1 320px;min-width:0}img{max-width:100%;height:auto;border:1px solid #c6cbd2}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f4f6;padding:1rem}section{padding-block:1rem;border-top:1px solid #c6cbd2}</style><main><h1>${escape(state.brief.goal)}</h1><p>${escape(state.brief.direction)}</p><pre>${escape(JSON.stringify(status,null,2))}</pre>${cards}</main></html>`;
  const reportTemp=path.join(dir,`report-${randomUUID()}.tmp`);
  await fs.writeFile(reportTemp,html,{mode:0o600,flag:'wx'});
  await fs.rename(reportTemp,path.join(dir,'report.html'));
  return {report:path.join(dir,'report.html'),...status};
}

export async function main(argv=process.argv.slice(2)) {
  try {
    const {command,args}=parse(argv);
    if(command==='help'||command==='--help') {console.log('design-reasoning init --root DIR --brief FILE\ncapture --root DIR --round baseline|candidate-N --url URL --browser EXECUTABLE\nreview --root DIR --round ID --review FILE\nstatus|finish|report --root DIR\nStandalone state/critique workflow: Node 20+. Real Chromium capture: Node 22+ and an existing Chrome/Edge/Chromium.');return 0;}
    if(!['init','capture','review','status','finish','report'].includes(command)) fail(`Unknown command: ${command}`);
    const root=await fs.realpath(args.root??process.cwd()),dir=await stateDir(root),lock=path.join(dir,'writer.lock');
    let handle;
    try { handle=await fs.open(lock,'wx',0o600); await handle.writeFile(JSON.stringify({pid:process.pid,command})); }
    catch(error){if(error.code==='EEXIST')fail(`State is locked: ${lock}. Inspect its PID; never auto-remove a live lock.`);throw error;}
    try {
      if(command==='init') {
        if(!args.brief) fail('init requires --brief');
        try{await fs.lstat(path.join(dir,'state.json'));fail('Design session already exists; use status or finish it before starting a separate task');}catch(e){if(e.code!=='ENOENT')throw e;}
        const brief=await json(path.resolve(args.brief));validateBrief(brief);
        const state={version:1,root,brief,briefHash:sha(JSON.stringify(brief)),initialSource:await sourceIdentity(root,brief),rounds:[]};
        await save(dir,state); console.log(JSON.stringify({status:'initialized',state:path.join(dir,'state.json'),criteria:CRITERIA}));return 0;
      }
      const state=await json(path.join(dir,'state.json'));
      if(state.version!==1||state.root!==root||state.briefHash!==sha(JSON.stringify(state.brief))||!Array.isArray(state.rounds))fail('Invalid session identity or modified brief');
      validateBrief(state.brief);
      if(command==='capture') {
        const id=args.round;
        if(!id||(!/^candidate-[1-5]$/.test(id)&&id!=='baseline')||!args.browser||!args.url)fail('capture needs --round baseline|candidate-N, --browser and --url');
        if(state.rounds.some(x=>x.id===id)) fail('Round already captured; do not overwrite evidence or repeat a successful capture');
        const candidates=state.rounds.filter(x=>x.id!=='baseline');
        if(id==='baseline'&&state.rounds.length)fail('Baseline must be the first capture');
        if(id!=='baseline'&&(candidates.length>=state.brief.maxRounds||id!==`candidate-${candidates.length+1}`))fail('Round budget exhausted or candidate order is invalid');
        if(id!=='baseline'&&!state.brief.newSurface&&!state.rounds.some(x=>x.id==='baseline'))fail('Capture the existing surface baseline first');
        const source=await sourceIdentity(root,state.brief);
        if(candidates.at(-1)?.source===source)fail('No source change since the previous candidate; do not repeat unchanged validation');
        const captures=await collect(args.browser,args.url,state.brief.viewports,state.brief.interactions,dir,id);
        if(source!==await sourceIdentity(root,state.brief))fail('Source changed during capture; evidence cannot be committed');
        state.rounds.push({id,source,capturedAt:new Date().toISOString(),url:args.url,captures});await save(dir,state);
        console.log(JSON.stringify({captured:id,screenshots:captures,...await render(root,dir,state)}));return 0;
      }
      if(command==='review'){if(!args.review||!args.round)fail('review needs --round and --review');await review(dir,state,path.resolve(args.review),args.round);}
      const result=command==='report'?await render(root,dir,state):await assess(root,dir,state);console.log(JSON.stringify(result,null,2));
      return command==='finish'&&result.status!=='complete'?2:0;
    } finally {await handle.close();await fs.unlink(lock);}
  } catch(error) {console.error(JSON.stringify({error:error.message}));return 1;}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))process.exitCode=await main();
