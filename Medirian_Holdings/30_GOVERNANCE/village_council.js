/* ---------- 13ج) الحكم (R26): مجلس الجزيرة — الوالي + حزب الميزان المعارض + المفتّش العام. الأغلبية تنفّذ، والخطوط الحمراء للمالك ---------- */
const CLERK_TRIG='trig_012R4evgJUvr4Q8sB2VWRdtV', REMOTE_SRV='Claude Code Remote', QUORUM=3, MAX_MATTERS=6;
let MCP=null, COUNCIL=[], OWNER_ACTS=[], CRUN=null;
// الخطوط الحمراء: نفس جدول 30_GOVERNANCE/COUNCIL.md. فحص نصّي قبل التصويت، والمفتّش يضيف ما يراه، وكاتب المجلس يعيد الفحص بنفسه
const RED=[
  ['money','صرف مال أو دفع أو اشتراك أو ميزانية','R2',/(\$|دولار|درهم|ريال|ندفع|الدفع|دفع مبلغ|اشتراك|ميزانية|budget|subscri|\bpay)/i],
  ['publish','نشر أو رفع على منصة عامة','R2',/(ننشر|نشره|نشرها|النشر|انشر|رفع على|نرفع|publish|upload|KDP|أمازون|Amazon|TPT|Etsy|Payhip|يوتيوب|YouTube|TikTok|تيك توك|انستقرام|Instagram|لينكدإن|LinkedIn)/i],
  ['external','إرسال أو تواصل أو توقيع خارج المجموعة','R2',/(أرسل إلى|إرسال إلى|راسل|نراسل|نتواصل مع|بريد إلى|email to|عقد مع|توقيع|نوقّع|نوقع)/i],
  ['secrets','كلمات سر أو مفاتيح أو فتح حسابات وربطها','R14',/(كلمة سر|كلمات سر|كلمة المرور|password|API key|مفتاح|فتح حساب|ربط حساب|بيانات الدخول)/i],
  ['trading','تداول بمال حقيقي أو تغيير بوت حيّ','R22',/(تداول حقيقي|حساب حقيقي|بوت حي|البوت الحي|live bot|أوامر التداول الحقيقية|real money)/i],
  ['freeze','رفع تجميد المالك أو إيقاظ مقاعد مجمّدة','owner_freeze',/(رفع التجميد|ارفع التجميد|فك التجميد|إلغاء التجميد|owner_freeze)/i],
  ['schedule','إنشاء مهام مجدولة أو تعطيلها أو تعديلها','المهام',/(مهمة مجدولة|المهام المجدولة|مهام مجدولة|مهمة المفتّش|تعطيل|عطّل|تفعيل المهمة|جدول|كل ست ساعات|كل ساعتين|كل ساعة|لصق|cron|trigger)/i],
  ['constitution','تغيير الدستور أو القواعد','R1',/(بند دستوري|الدستور|دستوري)/i],
  ['delete','حذف دائم','لا يُستردّ',/(احذف|حذف نهائي|حذف دائم|نحذف|delete)/i],
  ['brother','منتج Vocaris وسعره النهائي (قرار الأخ)','شقيقة',/(سعر Vocaris|منتج Vocaris|السعر النهائي)/i]];
const REDBY={}; RED.forEach(r=>REDBY[r[0]]={label:r[1],src:r[2]}); REDBY.owner_fact={label:'حقيقة لا يعرفها إلا المالك',src:'R10'};
function redScan(txt){ const t=String(txt||''); return RED.filter(r=>r[3].test(t)).map(r=>r[0]); }
const CST={passed:['أقرّته الأغلبية — عند كاتب المجلس','live'],needs_seal:['أقرّه المجلس — ينتظر ختمك','wait'],needs_fact:['يحتاج جوابك','rev'],rejected:['رفضته الأغلبية — بقي لك','block'],sealed:['ختمتَه','live'],refused:['رفضتَ التوصية','idle'],vetoed:['نقضتَه','pause'],failed:['تعذّرت الجلسة','block']};
const EXS={pending:'عند كاتب المجلس — لم يُكتب بعد',executed:'نُفّذ: كُتب في مركز القيادة',held_freeze:'كُتب في مركز القيادة — والأمر ينتظر رفع التجميد',awaiting_owner:'أوقفه الكاتب: خط أحمر — ينتظر ختمك',superseded:'أجبتَ أنت قبل المجلس — لم يُمسّ',blocked:'أوقفه الكاتب: النصاب غير مكتمل'};
const VERD={approved:'نعم — نوافق',rejected:'لا — نرفض',deferred:'نؤجّل',needs_fact:'يحتاج جواب المالك'};
const sitsOf=coId=>COUNCIL.filter(s=>s.co===coId);
const sitFor=ref=>COUNCIL.find(s=>s.ref===ref&&s.status!=='failed');
const inspectorSeat=()=>SEAT['chief-inspector']||null;
function councilOf(co){ return [co.governor].concat(co.opposition||[]).filter(Boolean); }
function councilCtx(co){ const al=(ALERTS[co.id]||[]).slice(0,5).map(a=>`- [${a.sev}] ${String(a.text).slice(0,220)}`).join('\n');
  return `الجزيرة: ${co.name} · الحالة: ${co.health} — ${co.statusLine||'—'} · المؤشر: ${co.kpi||'—'}${co.frozen?' · مجمّدة منذ '+fmtDate(co.frozen):''}\nدورها: ${String(co.desc||'').slice(0,400)}\nهذا الأسبوع: ${String(co.thisWeek||'—').slice(0,400)}\nالمقاعد: ${co.agents.slice(0,14).map(a=>`${a.name} [${a.status}]: ${String(a.task||'').slice(0,90)}`).join(' | ')}\nالتنبيهات المفتوحة:\n${al||'—'}`; }
function matterText(m){ return `المسألة (${m.kind==='motion'?'طلب من المالك':'قرار معلّق في مركز القيادة'}): «${m.title}»\nالتفاصيل: ${String(m.detail||'—').slice(0,700)}${m.owner_answer?'\nجواب المالك المكتوب بيده: «'+m.owner_answer+'»':''}`; }
const RED_LIST=RED.map(r=>`${r[0]} = ${r[1]}`).join('؛ ')+'؛ owner_fact = حقيقة لا يعرفها إلا المالك (رقم، رابط حساب، اسم، تفضيل شخصي)';
async function govPropose(co,m,objections){ const g=co.governor;
  const p=RULES+`\n\nأنت ${g.name}، والي جزيرة ${co.name}. بتفويض المالك (R26) تقترح جواباً لمسألة على مجلس الجزيرة. المعارضة (حزب الميزان) والمفتّش العام سيصوّتون، وتنفّذ الأغلبية.\n${councilCtx(co)}\n\n${matterText(m)}\n${objections?'\nاعتراضات الجولة الأولى — عدّل مقترحك لتعالجها أو اشرح لماذا لا:\n'+objections+'\n':''}\nقواعد المقترح: إن طلبت المسألة اختياراً فاختر شيئاً محدّداً من السجلّ واذكر السبب. إن احتاج الجواب حقيقة لا يعرفها إلا المالك فاجعل verdict = needs_fact واسأله سؤالاً واحداً. لا تخترع رقماً. إن مسّ التنفيذ خطاً أحمر (${RED_LIST}) فاقترح ما تراه صواباً، وسيذهب لختم المالك. order_text أمر عملي للمقعد المسؤول: ماذا يفعل، وأي حقل في القاعدة يتغيّر كإثبات، وإن كان الفعل نفسه للمالك (نشر، دفع…) فقل إن المقعد يجهّز فقط.\nأجب بـ JSON فقط: {"verdict":"approved|rejected|deferred|needs_fact","note":"الجواب بجملتين على الأكثر","order_text":"الأمر إن كان approved وإلا فارغ","target":"اسم المقعد المسؤول","reasons":["سبب من السجل","..."],"fact_question":"سؤال واحد للمالك أو فارغ"}`;
  const j=await SAMPLE.json(p,{modelTier:'default'}); const v=['approved','rejected','deferred','needs_fact'].includes(j&&j.verdict)?j.verdict:'deferred';
  return {verdict:v,note:String(j.note||'').slice(0,600),order_text:v==='approved'?String(j.order_text||'').slice(0,700):'',target:String(j.target||'').slice(0,80),reasons:(Array.isArray(j.reasons)?j.reasons:[]).slice(0,4).map(x=>String(x).slice(0,200)),fact_question:String(j.fact_question||'').slice(0,300)}; }
async function oppVote(co,m,prop,a){ const o=OPPBY[a.oppKey];
  const p=RULES+`\n\nأنت ${a.name}، عضو في «حزب الميزان» المعارض في جزيرة ${co.name}. ${o.lens}\nلا تعارض لمجرد المعارضة ولا توافق مجاملة. صوتك سبب من السجلّ لا رأي عام.\n${councilCtx(co)}\n\n${matterText(m)}\n\nمقترح الوالي: ${VERD[prop.verdict]} — ${prop.note}\nالأمر: ${prop.order_text||'—'}\nأسبابه: ${prop.reasons.join(' · ')||'—'}\n\nأجب بـ JSON فقط: {"vote":"yes|no","reason":"سبب بثلاثين كلمة على الأكثر","amend":"تعديل يجعلك توافق، أو فارغ"}`;
  const j=await SAMPLE.json(p,{modelTier:'default'}); return {vote:j&&j.vote==='yes'?'yes':'no',reason:String(j.reason||'').slice(0,300),amend:String(j.amend||'').slice(0,300)}; }
async function inspVote(co,m,prop){
  const p=RULES+`\n\nأنت المفتّش العام لمجموعة Meridian Holdings: مقعد مستقل لا يصنع ولا يُصلح، يفحص ويحكم. تفحص مقترح والي جزيرة ${co.name} على الدستور قبل أن تنفّذه الأغلبية.\nالدستور: R2 إنسان يوافق على ما يُنشر أو يُدفع أو يُوقَّع أو يُرسل خارج المجموعة (لا يُستثنى). R14 لا كلمات سر ولا مفاتيح عند العمّال (لا يُستثنى). R22 الذكاء الاصطناعي لا يلمس أوامر التداول الحيّة (لا يُستثنى). R1 المالك وحده يغيّر الدستور. R10 كل رقم يحمل مصدره. R20 لا يُبلَّغ عن فعل كأنه تمّ. تجميد المالك (owner_freeze) يرفعه المالك وحده.\nالخطوط الحمراء: ${RED_LIST}.\n${councilCtx(co)}\n\n${matterText(m)}\n\nمقترح الوالي: ${VERD[prop.verdict]} — ${prop.note}\nالأمر: ${prop.order_text||'—'}\n\nفي red_lines اذكر مفاتيح الخطوط التي يمسّها تنفيذ المقترح (تذهب لختم المالك، وهذا وحده ليس سبباً للرفض). صوّت no إن خالف المقترح قاعدة، أو اخترع حقيقة أو رقماً، أو ناقض السجلّ.\nأجب بـ JSON فقط: {"vote":"yes|no","reason":"ثلاثون كلمة على الأكثر مع رقم القاعدة","red_lines":["money", "..."]}`;
  const j=await SAMPLE.json(p,{modelTier:'default'}); const keys=Object.keys(REDBY);
  return {vote:j&&j.vote==='yes'?'yes':'no',reason:String(j.reason||'').slice(0,300),red_lines:(Array.isArray(j.red_lines)?j.red_lines:[]).map(String).filter(k=>keys.includes(k))}; }
const safeVote=async(fn)=>{ try{ return await fn(); }catch(e){ return {vote:'no',reason:'تعذّر الصوت ('+(e&&e.code||'خطأ')+') — يُحسب لا',amend:'',red_lines:[]}; } };
// المسائل: قرارات الجزيرة المعلّقة التي لم يحسمها المجلس بعد، الأعلى أولوية أولاً
function pendingMatters(co){ return (DECS[co.id]||[]).filter(d=>!sitFor(d.id))
  .sort((a,b)=>(a.prio||9)-(b.prio||9)).map(d=>({kind:'decision',ref:d.id,title:d.title,detail:d.detail,prio:d.prio})); }
function councilWalk(co,on){ const ws=councilOf(co).map(a=>workers.find(w=>w.a===a)).filter(Boolean);
  if(on){ if(MEET&&MEET.active)return; const C0=meetingCenter(co,null), spots=meetingSpots(C0.p,ws.length); ws.forEach((w,i)=>sendToMeeting(w,spots[i],C0.v)); if(CRUN)CRUN.center=C0; }
  else ws.forEach(w=>{w.meet=false;w.boost=1;w.path=null;w.wait=800;}); }
function sayAs(a,text,ms){ const w=workers.find(x=>x.a===a); if(!w)return; w.say={text:String(text).slice(0,90),until:TIME+(ms||5200)}; }
function cLog(html){ if(CRUN&&CRUN.box&&CRUN.box.isConnected){ CRUN.box.appendChild(el(html)); const pb=PB; pb.scrollTop=pb.scrollHeight; } }
async function sitOne(co,m){ const sid='cs-'+Date.now()+'-'+co.id; const g=co.governor, ins=inspectorSeat();
  cLog(`<div class="sect">المسألة: ${esc(m.title)}</div>`); sayAs(g,'أعرض على المجلس: '+m.title);
  let prop; try{ prop=await govPropose(co,m,''); }catch(e){ cLog(`<div class="al crit">تعذّر مقترح الوالي (${esc(e&&e.code||'خطأ')}) — لم تُعقد الجلسة على هذه المسألة.</div>`); return null; }
  const rec={id:sid,co:co.id,kind:m.kind,ref:m.ref,title:m.title,detail:String(m.detail||'').slice(0,700),at:new Date().toISOString(),round:1,proposal:prop,owner_answer:m.owner_answer||'',votes:[],gate:{hits:[]},tally:{yes:0,no:0,seats:5,quorum:QUORUM}};
  cLog(`<div class="turn said"><b>${esc(g.name)} — المقترح: ${esc(VERD[prop.verdict])}</b><div>${esc(prop.note)}</div>${prop.order_text?'<div class="dim">الأمر: '+esc(prop.order_text)+'</div>':''}${prop.reasons.length?'<div class="dim">الأسباب: '+esc(prop.reasons.join(' · '))+'</div>':''}</div>`);
  sayAs(g,VERD[prop.verdict]+': '+prop.note);
  if(prop.verdict==='needs_fact'){ rec.status='needs_fact'; rec.fact_question=prop.fact_question||'المجلس يحتاج جوابك ليقرّر.'; rec.exec_status='none';
    cLog(`<div class="al warn"><b>يحتاج جوابك:</b> ${esc(rec.fact_question)}</div>`); return rec; }
  const vote=async(p,round)=>{ const opp=co.opposition||[];
    const res=await Promise.all(opp.map(a=>safeVote(()=>oppVote(co,m,p,a))).concat([safeVote(()=>inspVote(co,m,p))]));
    const votes=[{who:g.id,name:g.name,party:'governor',vote:'yes',reason:'صاحب المقترح'}];
    opp.forEach((a,i)=>votes.push({who:a.id,name:a.name,party:'opposition',vote:res[i].vote,reason:res[i].reason,amend:res[i].amend||''}));
    const iv=res[res.length-1]; votes.push({who:ins?ins.id:'chief-inspector',name:ins?ins.name:'المفتّش العام',party:'inspector',vote:iv.vote,reason:iv.reason,red_lines:iv.red_lines||[]});
    votes.forEach((v,k)=>{ if(k===0)return; const a=SEAT[v.who]; if(a)setTimeout(()=>sayAs(a,(v.vote==='yes'?'✅ نعم: ':'✋ لا: ')+v.reason),k*900);
      cLog(`<div class="turn said"><b>${v.vote==='yes'?'✅':'✋'} ${esc(v.name)}${v.party==='inspector'?' (المفتّش)':' (حزب الميزان)'}${round>1?' — الجولة '+round:''}</b><div>${esc(v.reason)}</div>${v.amend?'<div class="dim">تعديل مقترح: '+esc(v.amend)+'</div>':''}</div>`); });
    return votes; };
  let votes=await vote(prop,1); let yes=votes.filter(v=>v.vote==='yes').length; let insOk=votes[votes.length-1].vote==='yes';
  if(!(yes>=QUORUM&&insOk)){ const obj=votes.filter(v=>v.vote==='no').map(v=>`- ${v.name}: ${v.reason}${v.amend?' (تعديل: '+v.amend+')':''}`).join('\n');
    if(votes.some(v=>v.amend||v.vote==='no')){ cLog(`<div class="dim">سقط المقترح ${yes}/5 — الوالي يعدّله مرة واحدة ويُعاد التصويت.</div>`); sayAs(g,'أعدّل المقترح وأعيده للتصويت');
      try{ const p2=await govPropose(co,m,obj); if(p2.verdict==='needs_fact'){ rec.proposal=p2; rec.status='needs_fact'; rec.fact_question=p2.fact_question; rec.exec_status='none'; rec.votes=votes; cLog(`<div class="al warn"><b>يحتاج جوابك:</b> ${esc(p2.fact_question)}</div>`); return rec; }
        prop=p2; rec.proposal=p2; rec.round=2; cLog(`<div class="turn said"><b>${esc(g.name)} — المقترح المعدّل: ${esc(VERD[p2.verdict])}</b><div>${esc(p2.note)}</div>${p2.order_text?'<div class="dim">الأمر: '+esc(p2.order_text)+'</div>':''}</div>`);
        votes=await vote(p2,2); yes=votes.filter(v=>v.vote==='yes').length; insOk=votes[votes.length-1].vote==='yes'; }catch(e){} } }
  rec.votes=votes; rec.tally={yes,no:5-yes,seats:5,quorum:QUORUM};
  const hits=prop.verdict==='approved'?Array.from(new Set(redScan([m.title,prop.note,prop.order_text].join(' ')).concat(votes[votes.length-1].red_lines||[]))):[];
  if(m.owner_answer) { const i=hits.indexOf('owner_fact'); if(i>=0)hits.splice(i,1); }
  rec.gate={hits};
  if(yes>=QUORUM&&insOk){ if(hits.length){ rec.status='needs_seal'; rec.exec_status='none'; } else { rec.status='passed'; rec.exec_status='pending'; } }
  else { rec.status='rejected'; rec.exec_status='none'; }
  const lbl=CST[rec.status][0]; cLog(`<div class="al ${rec.status==='passed'?'info':(rec.status==='rejected'?'crit':'dec')}"><b>النتيجة ${yes}/5 ${insOk?'· المفتّش وافق':'· المفتّش لم يوافق'}:</b> ${esc(lbl)}${hits.length?'<div>الخطوط الحمراء: '+hits.map(k=>esc(REDBY[k]?REDBY[k].label:k)).join('، ')+'</div>':''}</div>`);
  sayAs(g,rec.status==='passed'?'أقرّت الأغلبية — يُنفَّذ':(rec.status==='needs_seal'?'أقرّته الأغلبية — ينتظر ختم المالك':'سقط المقترح — يبقى للمالك'),6000);
  return rec; }
async function holdCouncil(cos,opts){ opts=opts||{};
  if(CRUN&&CRUN.active){ if(!opts.quiet)openCouncilRun(); return {busy:true}; }
  if(!SAMPLE){ alertNote('المجلس يحتاج صلاحية «اسأل Claude» لهذه الصفحة.'); return {error:'no_sample'}; }
  if(!CANWRITE){ alertNote('المجلس يكتب في قاعدة القرية: هذه النسخة للقراءة فقط.'); return {error:'read_only'}; }
  const queue=[]; cos.forEach(co=>{ (opts.matters&&opts.matters[co.id]||pendingMatters(co)).forEach(m=>queue.push({co,m})); });
  queue.sort((a,b)=>(a.m.prio||9)-(b.m.prio||9)); const todo=queue.slice(0,opts.max||MAX_MATTERS); if(!todo.length){ alertNote('لا قرار معلّق ينتظر المجلس في هذه الجزيرة.'); return {count:0}; }
  CRUN={active:true,todo,done:[],at:new Date().toISOString(),left:queue.length-todo.length};
  if(!opts.quiet)openCouncilRun(); feedEvent('⚖️','انعقد المجلس على '+todo.length+' مسألة'+(CRUN.left?' (وبقيت '+CRUN.left+' لجلسة تالية)':''));
  let lastCo=null;
  for(const {co,m} of todo){ if(co!==lastCo){ if(lastCo)councilWalk(lastCo,false); councilWalk(co,true); cLog(`<div class="sect" style="color:var(--gold)">⚖️ مجلس ${esc(co.short)}</div>`); lastCo=co; }
    const rec=await sitOne(co,m); if(!rec)continue;
    if(m.kind==='motion'){ try{ await DB.collection('motions').doc(m.ref).set({co:co.id,text:m.title,at:rec.at,by:'owner',status:'in_council',session:rec.id}); }catch(e){} }
    try{ await DB.collection('council').doc(rec.id).set(rec); rec._saved=true; }catch(e){ cLog(`<div class="al crit">لم يُحفظ محضر الجلسة: ${esc(e&&e.code||'تعذّر')}</div>`); }
    CRUN.done.push(rec); if(!COUNCIL.some(s=>s.id===rec.id))COUNCIL.unshift(rec); }
  if(lastCo)councilWalk(lastCo,false);
  const passed=CRUN.done.filter(r=>r.status==='passed'&&r._saved); let woke='';
  if(passed.length){ const r=await fireClerk('جلسات أقرّتها الأغلبية: '+passed.map(r=>r.id).join(', ')); woke=r.ok?'أُوقظ كاتب المجلس لينفّذ في مركز القيادة.':('لم يُوقَظ كاتب المجلس: '+r.why); }
  const c=k=>CRUN.done.filter(r=>r.status===k).length;
  cLog(`<div class="note"><b>انتهت الجلسة.</b> أقرّته الأغلبية للتنفيذ: ${c('passed')} · ينتظر ختمك: ${c('needs_seal')} · يحتاج جوابك: ${c('needs_fact')} · سقط: ${c('rejected')}.${CRUN.left?' بقيت '+CRUN.left+' مسألة لجلسة تالية.':''}<div>${esc(woke)}</div></div>`);
  CRUN.active=false; feedEvent('⚖️','انتهى المجلس: '+c('passed')+' للتنفيذ · '+c('needs_seal')+' لختمك · '+c('needs_fact')+' لجوابك');
  return {count:CRUN.done.length,passed:c('passed'),needs_seal:c('needs_seal'),needs_fact:c('needs_fact'),rejected:c('rejected'),left:CRUN.left,clerk:woke}; }
async function fireClerk(text){ if(!MCP)return {ok:false,why:'صلاحية «Claude Code Remote» غير ممنوحة لهذه الصفحة — افتح قائمة الصلاحيات وفعّلها، ثم اضغط «أيقظ الكاتب».'};
  try{ await MCP.callTool(REMOTE_SRV,'fire_trigger',{trigger_id:CLERK_TRIG,text:String(text).slice(0,1500)},{cache:false}); return {ok:true}; }
  catch(e){ const c=e&&e.code; return {ok:false,why:c==='not_granted'||c==='consent_denied'?'لم تُمنح صلاحية «Claude Code Remote».':(c==='rate_limited'?'الحدّ بلغ مؤقتاً — أعد المحاولة بعد قليل.':'تعذّر الاتصال ('+(c||'خطأ')+').')}; } }
async function ownerAct(kind,s,note){ if(!DB||!CANWRITE){alertNote('هذه النسخة للقراءة فقط.');return false;}
  const id='oa-'+Date.now(); try{ await DB.collection('owner_acts').doc(id).set({kind,session_id:s.id,co:s.co,ref:s.ref,title:s.title,note:String(note||'').slice(0,500),at:new Date().toISOString(),done:false}); }
  catch(e){ alertNote('لم يُحفظ: '+(e&&e.code||'تعذّر')); return false; }
  const r=await fireClerk(({seal:'ختم المالك',refuse:'رفض المالك',veto:'نقض المالك'}[kind]||kind)+' على الجلسة '+s.id); feedEvent(kind==='veto'?'⛔':'✍️',({seal:'ختمتَ',refuse:'رفضتَ',veto:'نقضتَ'}[kind])+' «'+String(s.title).slice(0,50)+'»'+(r.ok?' — الكاتب في الطريق':''));
  return r; }
function sitRow(s,showCo){ const st=CST[s.status]||[s.status,'idle']; return row(`<span class="dot ${st[1]}"></span><span style="flex:1"><span class="nm">${esc(s.title)}</span><span class="sb">${showCo&&COBY[s.co]?esc(COBY[s.co].short)+' · ':''}${esc(st[0])} · ${s.tally?s.tally.yes+'/5':''}${s.exec_status&&EXS[s.exec_status]?' · '+esc(EXS[s.exec_status]):''} · ${fmtDate(s.at)}</span></span><span style="color:var(--dim)">‹</span>`,()=>openSitting(s)); }
function councilRoster(co){ const ins=inspectorSeat(); const list=councilOf(co).concat(ins?[ins]:[]);
  list.forEach(a=>PB.appendChild(row(`<span class="dot ${a.kind==='opposition'?'block':(a.kind==='governor'?'ready':'rev')}"></span><span style="flex:1"><span class="nm">${esc(a.name)}</span><span class="sb">${a.kind==='governor'?'يقترح · صوت واحد':(a.kind==='opposition'?'حزب الميزان — المعارضة · '+esc(OPPBY[a.oppKey].short):'المفتّش العام · له حق النقض')}</span></span><span style="color:var(--dim)">‹</span>`,()=>openAgent(a,coOf(a))))); }
function openCouncil(co){ head('⚖️ مجلس '+co.short,'R26 · الوالي + حزب الميزان + المفتّش العام · النصاب 3 من 5 مع موافقة المفتّش'); backTo(co.name,()=>openCo(co));
  const n=pendingMatters(co).length; const tools=el(`<div class="chips"><button class="chip act" id="b-sit" ${n?'':'disabled'}>⚖️ اعقد المجلس على القرارات المعلّقة (${n})</button><button class="chip act" id="b-clerk">📜 أيقظ الكاتب</button></div>`); PB.appendChild(tools);
  tools.querySelector('#b-sit').onclick=()=>holdCouncil([co]); tools.querySelector('#b-clerk').onclick=async()=>{const r=await fireClerk('مراجعة يدوية من المالك'); alertNote(r.ok?'أُوقظ كاتب المجلس.':r.why);};
  PB.appendChild(el(`<div class="note">الوالي يقترح، وحزب الميزان المعارض ينظر من الجهة المعاكسة، والمفتّش العام يفحص على الدستور. إن وافق 3 من 5 ومعهم المفتّش يُنفَّذ: يكتبه كاتب المجلس في مركز القيادة كجوابك، ويصل الأمر للمقعد المسؤول. ما يمسّ خطاً أحمر (مال، نشر، تواصل خارجي، أسرار، تداول حقيقي، رفع التجميد، المهام المجدولة، الدستور، الحذف، منتج Vocaris، حقيقة تعرفها أنت وحدك) ينتظر ختمك بضغطة. ولك النقض على أي قرار نُفّذ.</div>`));
  PB.appendChild(el('<div class="sect">أعضاء المجلس</div>')); councilRoster(co);
  const ss=sitsOf(co.id); PB.appendChild(el(`<div class="sect">محاضر المجلس (${ss.length})</div>`)); if(ss.length)ss.slice(0,25).forEach(s=>PB.appendChild(sitRow(s))); else PB.appendChild(el('<div class="dim">لم ينعقد المجلس بعد.</div>'));
  if(!MCP)PB.appendChild(el('<div class="dim">تنبيه: لإيقاظ كاتب المجلس تحتاج الصفحة صلاحية «Claude Code Remote» (أداة fire_trigger) — تظهر في قائمة الصلاحيات.</div>'));
  openP(); }
function openCouncilRun(){ head('⚖️ جلسة المجلس الآن',CRUN?(CRUN.todo.length+' مسألة · '+CRUN.todo.map(x=>x.co.short).filter((v,i,a)=>a.indexOf(v)===i).join('، ')):''); const box=el('<div class="meet"></div>'); PB.appendChild(box);
  if(CRUN){ CRUN.box=box; box.appendChild(el(`<div class="dim">الأعضاء يمشون إلى ساحة الجزيرة. كل صوت يظهر هنا وفوق رأس صاحبه.</div>`)); CRUN.done.forEach(r=>box.appendChild(sitRow(r,true))); } openP(); }
function openSitting(s){ const co=COBY[s.co]||capCo, st=CST[s.status]||[s.status,'idle']; head('⚖️ '+s.title,'مجلس '+co.short+' · '+fmtDate(s.at)); backTo('مجلس '+co.short,()=>openCouncil(co));
  PB.appendChild(el(`<div class="al ${s.status==='passed'||s.status==='sealed'?'info':(s.status==='rejected'?'crit':'dec')}"><b>${esc(st[0])}</b>${s.tally?' · '+s.tally.yes+' من 5':''}${s.exec_status&&EXS[s.exec_status]?'<div>'+esc(EXS[s.exec_status])+'</div>':''}${s.clerk_note?'<div class="dim">الكاتب: '+esc(s.clerk_note)+'</div>':''}${s.order_id?'<div class="dim">الأمر: '+esc(s.order_id)+'</div>':''}</div>`));
  if(s.detail)PB.appendChild(el(`<div class="sect">المسألة</div><div class="note">${esc(s.detail)}</div>`));
  const p=s.proposal||{}; PB.appendChild(el(`<div class="sect">مقترح الوالي${s.round>1?' (بعد التعديل)':''}</div><div class="turn said"><b>${esc(VERD[p.verdict]||p.verdict||'—')}</b><div>${esc(p.note||'')}</div>${p.order_text?'<div class="dim">الأمر: '+esc(p.order_text)+'</div>':''}${(p.reasons||[]).length?'<div class="dim">الأسباب: '+esc(p.reasons.join(' · '))+'</div>':''}</div>`));
  if(s.owner_answer)PB.appendChild(el(`<div class="al info"><b>جوابك:</b> ${esc(s.owner_answer)}</div>`));
  if((s.gate&&s.gate.hits||[]).length)PB.appendChild(el(`<div class="sect">بوابة التفتيش — خطوط حمراء</div><div class="chips">${s.gate.hits.map(k=>`<span class="chip off">${esc(REDBY[k]?REDBY[k].label+' ('+REDBY[k].src+')':k)}</span>`).join('')}</div>`));
  if((s.votes||[]).length){ PB.appendChild(el('<div class="sect">الأصوات</div>')); s.votes.forEach(v=>PB.appendChild(el(`<div class="turn said"><b>${v.vote==='yes'?'✅':'✋'} ${esc(v.name)} · ${v.party==='governor'?'الوالي':(v.party==='inspector'?'المفتّش العام':'حزب الميزان')}</b><div>${esc(v.reason||'')}</div>${v.amend?'<div class="dim">تعديل: '+esc(v.amend)+'</div>':''}</div>`))); }
  const acts=OWNER_ACTS.filter(a=>a.session_id===s.id); if(acts.length)PB.appendChild(el(`<div class="sect">ضغطاتك</div>${acts.map(a=>`<div class="al ${a.done?'info':'warn'}">${esc({seal:'ختم',refuse:'رفض',veto:'نقض'}[a.kind]||a.kind)} · ${fmtDate(a.at)} · ${a.done?esc(a.result||'نفّذه الكاتب'):'عند الكاتب'}${a.note?'<div class="dim">'+esc(a.note)+'</div>':''}</div>`).join('')}`));
  const box=el(`<div class="chat"><input type="text" placeholder="ملاحظتك (اختيارية)…"><div class="chips" style="margin-top:6px"></div></div>`); const inp=box.querySelector('input'), bar=box.querySelector('.chips'); let any=false;
  const btn=(lab,cls,fn)=>{ const b=el(`<button class="chip ${cls}">${lab}</button>`); b.onclick=async()=>{b.disabled=true; await fn(); setTimeout(()=>openSitting(COUNCIL.find(x=>x.id===s.id)||s),400);}; bar.appendChild(b); any=true; };
  const open=a=>OWNER_ACTS.some(x=>x.session_id===s.id&&!x.done&&x.kind===a);
  if((s.status==='needs_seal'||s.status==='rejected')&&!open('seal')){ btn('✍️ وقّع التوصية','act',()=>ownerAct('seal',s,inp.value)); btn('✗ ارفضها','stop',()=>ownerAct('refuse',s,inp.value)); }
  if((s.status==='passed'||s.status==='sealed')&&s.exec_status!=='superseded'&&!open('veto')) btn('⛔ انقض قرار المجلس','stop',()=>ownerAct('veto',s,inp.value));
  if(s.status==='needs_fact'){ inp.placeholder=s.fact_question||'جوابك…'; PB.appendChild(el(`<div class="al warn"><b>سؤال المجلس لك:</b> ${esc(s.fact_question||'—')}</div>`));
    btn('↩ أرسل جوابي وأعد التصويت','act',async()=>{ const ans=inp.value.trim(); if(!ans){alertNote('اكتب جوابك أولاً.');return;}
      await holdCouncil([co],{matters:{[co.id]:[{kind:s.kind,ref:s.ref,title:s.title,detail:s.detail,owner_answer:ans.slice(0,400)}]}});
      try{ await DB.collection('council').doc(s.id).update({status:'failed',exec_status:'none',clerk_note:'أُعيد التصويت بجواب المالك'}); }catch(e){} }); }
  if(s.status==='rejected'){ btn('↻ أعد المسألة للمجلس','act',()=>holdCouncil([co],{matters:{[co.id]:[{kind:s.kind,ref:s.ref,title:s.title,detail:s.detail,owner_answer:inp.value.trim().slice(0,400)}]}})); }
  if(any&&CANWRITE)PB.appendChild(box);
  openP(); }
function councilsOverview(){ const ss=COUNCIL.slice(0,30); const waiting=COUNCIL.filter(s=>s.status==='needs_seal'||s.status==='needs_fact');
  PB.appendChild(el(`<div class="sect">مجالس الجزر — R26 (${COUNCIL.length} محضراً)</div>`));
  const b=el(`<div class="chips"><button class="chip act">⚖️ اعقد مجالس كل الجزر (حتى ${MAX_MATTERS} قرارات بالأولوية)</button></div>`); b.querySelector('button').onclick=()=>holdCouncil(C.filter(c=>c.governor)); PB.appendChild(b);
  if(waiting.length){ PB.appendChild(el(`<div class="sect">ينتظرك (${waiting.length})</div>`)); waiting.slice(0,12).forEach(s=>PB.appendChild(sitRow(s,true))); }
  PB.appendChild(el('<div class="sect">آخر المحاضر</div>')); if(ss.length)ss.forEach(s=>PB.appendChild(sitRow(s,true))); else PB.appendChild(el('<div class="dim">لم ينعقد أي مجلس بعد.</div>')); }
function councilTag(d){ const s=sitFor(d.id); if(!s)return '<div class="dim">⚖️ لم يُعرض على مجلس الجزيرة بعد</div>'; const st=CST[s.status];
  return '<div class="dim">⚖️ المجلس: '+esc(st?st[0]:s.status)+(s.tally?' · '+s.tally.yes+'/5':'')+(EXS[s.exec_status]?' · '+esc(EXS[s.exec_status]):'')+'</div>'; }
// أدوات الوالي في المحادثة: يعقد المجلس ويقرأ محاضره — لا ينفّذ وحده
function govTools(t){ if(!t||t.kind!=='agent'||!t.a||t.a.kind!=='governor')return [];
  const co=t.co||coOf(t.a), cap=co.id==='meridian';
  return [
    {name:'convene_council',description:'يعقد مجلس الجزيرة (R26) الآن على القرارات المعلّقة التي لم تُعرض عليه'+(cap?'، أو على مجالس كل الجزر إن كان scope = all':'')+'، أو على طلب جديد من المالك (motion). الوالي يقترح، وحزب الميزان المعارض والمفتّش العام يصوّتون، وكاتب المجلس ينفّذ ما تقرّه الأغلبية. استعمله فوراً حين يأمرك المالك بالتنفيذ أو بعرض شيء على المجلس. يعود فوراً والجلسة تجري أمام المالك.',
     inputSchema:{type:'object',properties:{scope:{type:'string',enum:cap?['island','all']:['island']},motion:{type:'string',description:'نص طلب المالك إن لم يكن قراراً معلّقاً'}}},
     execute:({scope,motion})=>{ if(!CANWRITE)return {status:'read_only',note:'هذه النسخة للقراءة فقط'}; if(!SAMPLE)return {status:'no_sample'}; if(CRUN&&CRUN.active)return {status:'busy',note:'المجلس منعقد الآن'};
       const cos=(cap&&scope==='all')?C.filter(c=>c.governor):[co]; const opts={quiet:true}; const mo=String(motion||'').trim();
       if(mo)opts.matters={[co.id]:[{kind:'motion',ref:'mo-'+Date.now(),title:mo.slice(0,200),detail:'طلب المالك للوالي في المحادثة: '+mo.slice(0,600),prio:1}]};
       const n=mo?1:cos.reduce((m,c)=>m+pendingMatters(c).length,0); if(!n)return {status:'nothing',note:'لا قرار معلّق إلا وقد عُرض على المجلس — راجع council_record'};
       setTimeout(()=>holdCouncil(cos,opts),50); return {status:'convened',matters_now:Math.min(n,MAX_MATTERS),left_for_next_sitting:Math.max(0,n-MAX_MATTERS),watch:'زرّ «⚖️ مجلس الجزيرة» في لوحة الجزيرة يعرض التصويت'}; }},
    {name:'council_record',description:'يعيد آخر محاضر المجلس: المسألة، النتيجة، الأصوات، الخطوط الحمراء، وهل نفّذها كاتب المجلس في مركز القيادة.',inputSchema:{type:'object',properties:{}},
     execute:()=>(cap?COUNCIL:sitsOf(co.id)).slice(0,12).map(s=>({island:s.co,title:s.title,result:CST[s.status]?CST[s.status][0]:s.status,votes:s.tally?s.tally.yes+'/5':'',execution:EXS[s.exec_status]||'',verdict:s.proposal&&s.proposal.verdict,red_lines:(s.gate&&s.gate.hits)||[],question_for_owner:s.fact_question||''}))}];
}
