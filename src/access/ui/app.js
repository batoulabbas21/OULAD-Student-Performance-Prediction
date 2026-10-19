const el = id => document.getElementById(id);
const number = new Intl.NumberFormat('en-US');
const titles = {'enrollments':'Enrollment by presentation','students':'Distinct students','types':'Assessment types','banked':'Banked assessment records','unknown':'Missing scores','submissions':'New assessment records','resources':'Learning resources','pass':'Pass results in 2013J'};
const modeNames = {catalog:'Example questions',record:'Gemini · recorded',live:'Gemini · live',replay:'Saved AI answers'};
const modeNotes = {catalog:'Example mode runs the eight published questions without an AI call.',record:'New questions use Gemini. Responses are saved for replay.',live:'New questions use Gemini. API usage follows your account settings.',replay:'Replay uses saved AI responses. The question must match an existing recording.'};
let currentResult = null;
let busy = false;
let activeTab = 'answer';
let copyTimer;
el('student-count').textContent = number.format(APP.stats.students);
el('enrollment-count').textContent = number.format(APP.stats.enrollments);
el('record-count').textContent = number.format(APP.stats.records);
el('library-count').textContent = APP.examples.length;
el('mode-badge').textContent = modeNames[APP.mode] || APP.mode;
el('mode-note').textContent = modeNotes[APP.mode];
el('about-mode').textContent = 'Current mode: '+modeNames[APP.mode]+'. '+modeNotes[APP.mode];
el('mode-description').textContent = APP.mode==='catalog' ? 'Choose a question from the library to explore the data.' : 'Ask in plain English. See the facts behind the answer.';

function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
  const use = document.createElementNS('http://www.w3.org/2000/svg','use');
  use.setAttribute('href','#i-'+name);svg.append(use);svg.setAttribute('aria-hidden','true');return svg;
}
function syncQuestion() {
  const question = el('question').value;
  el('character-count').textContent = number.format(question.length)+' / 1,000';
  el('ask').disabled = busy || !question.trim();
  document.querySelectorAll('.example-item').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.question===question.trim())));
}
APP.examples.forEach((example,index)=>{
  const button = document.createElement('button');button.type='button';button.className='example-item';button.dataset.question=example.question;button.setAttribute('aria-pressed','false');
  const n=document.createElement('span');n.className='example-number';n.textContent=String(index+1).padStart(2,'0');
  const text=document.createElement('span');const title=document.createElement('strong');title.textContent=titles[example.id.split('-').slice(1).join('-')]||'Explore question '+(index+1);
  const question=document.createElement('small');question.textContent=example.question;text.append(title,question);button.append(n,text,icon('chevron'));
  button.addEventListener('click',()=>{if(busy)return;el('question').value=example.question;syncQuestion();el('question').focus({preventScroll:true});if(innerWidth<981)el('question-form').scrollIntoView({behavior:'smooth',block:'center'});});
  el('examples').append(button);
});
el('question').value=APP.examples[0]?.question||'';syncQuestion();el('question').addEventListener('input',syncQuestion);

function selectTab(name,focus=false) {
  activeTab=name;
  for(const tab of ['answer','query','evidence']) {
    const selected=tab===name;el('tab-'+tab).setAttribute('aria-selected',String(selected));el('tab-'+tab).tabIndex=selected?0:-1;el('panel-'+tab).hidden=!selected;
  }
  if(focus)el('tab-'+name).focus();
}
for(const name of ['answer','query','evidence'])el('tab-'+name).addEventListener('click',()=>selectTab(name));
document.querySelector('.result-tabs').addEventListener('keydown',event=>{
  const tabs=['answer','query','evidence'];let index=tabs.indexOf(activeTab);
  if(event.key==='ArrowRight')index=(index+1)%3;else if(event.key==='ArrowLeft')index=(index+2)%3;else if(event.key==='Home')index=0;else if(event.key==='End')index=2;else return;
  event.preventDefault();selectTab(tabs[index],true);
});
const dialog=el('about-dialog');
for(const name of ['about-button','help-button'])el(name).addEventListener('click',()=>dialog.showModal());
el('close-about').addEventListener('click',()=>dialog.close());dialog.addEventListener('click',event=>{if(event.target===dialog){const rect=dialog.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)dialog.close();}});

const label = value => value.replace(/([a-z])([A-Z])/g,'$1 $2').replace(/_/g,' ').replace(/^./,c=>c.toUpperCase());
function displayValue(value) {
  if(value===null||value===undefined)return 'Unknown';
  if(typeof value==='string'&&value.startsWith('https://example.org/oulad/schema#'))return label(value.split('#')[1]);
  if(typeof value==='string'&&/^\d+$/.test(value)&&!/^0\d/.test(value))return number.format(Number(value));
  return String(value);
}
function message(title,description) {
  const box=document.createElement('div');box.className='answer-message';const heading=document.createElement('strong');heading.textContent=title;
  const paragraph=document.createElement('p');paragraph.textContent=description;box.append(heading,paragraph);el('answer').replaceChildren(box);
}
function renderAnswer(result) {
  el('answer').replaceChildren();el('answer-toolbar').hidden=false;
  if('boolean' in result) {
    el('answer-meta').textContent='Boolean answer';el('download').hidden=true;
    const metric=document.createElement('div');metric.className='result-metric';const value=document.createElement('div');value.className='metric-value';value.textContent=result.boolean?'True':'False';
    const description=document.createElement('p');description.className='metric-label';description.textContent='Returned by the graph';metric.append(value,description);el('answer').append(metric);return;
  }
  el('answer-meta').textContent=number.format(result.rows.length)+(result.rows.length===1?' result':' results')+' · '+result.columns.length+(result.columns.length===1?' column':' columns');el('download').hidden=false;
  if(!result.rows.length){message('No matching rows.','The query ran successfully, but returned no matches. An empty answer is different from missing knowledge.');return;}
  if(result.columns.length===1&&result.rows.length===1&&/^[-+]?\d+(\.\d+)?$/.test(result.rows[0][result.columns[0]]||'')) {
    const metric=document.createElement('div');metric.className='result-metric';const value=document.createElement('div');value.className='metric-value';value.textContent=displayValue(result.rows[0][result.columns[0]]);
    const description=document.createElement('p');description.className='metric-label';description.textContent=label(result.columns[0]);metric.append(value,description);el('answer').append(metric);return;
  }
  const wrapper=document.createElement('div');wrapper.className='table-scroll';wrapper.tabIndex=0;wrapper.setAttribute('role','region');wrapper.setAttribute('aria-label','Query answer table');
  const table=document.createElement('table');const head=document.createElement('thead');const header=document.createElement('tr');
  const numeric=result.columns.map(c=>result.rows.every(r=>r[c]===null||/^[-+]?\d+(\.\d+)?$/.test(r[c]??'')));
  result.columns.forEach((c,i)=>{const th=document.createElement('th');th.scope='col';th.textContent=label(c);if(numeric[i])th.className='numeric';header.append(th);});head.append(header);table.append(head);
  const body=document.createElement('tbody');
  for(const row of result.rows){const tr=document.createElement('tr');result.columns.forEach((c,i)=>{const td=document.createElement('td');td.textContent=displayValue(row[c]);if(numeric[i])td.className='numeric';if(row[c]!==null&&row[c]!==undefined)td.title=String(row[c]);tr.append(td);});body.append(tr);}
  table.append(body);wrapper.append(table);el('answer').append(wrapper);
}
function renderEvidence(data) {
  el('evidence').replaceChildren();const attempts=data.attempts||[];el('attempt-count').hidden=!attempts.length;el('attempt-count').textContent=attempts.length;
  if(!attempts.length){const p=document.createElement('p');p.textContent='No query attempts were made.';el('evidence').append(p);return;}
  attempts.forEach((attempt,index)=>{
    const card=document.createElement('section');card.className='attempt-card';const heading=document.createElement('div');heading.className='attempt-heading';heading.append(icon('check'));
    const text=document.createElement('span');text.textContent='Attempt '+(index+1)+' · '+(attempt.problems?.length?'Problems reported':attempt.reply?'Model refusal':'No query problems reported');heading.append(text);card.append(heading);
    if(attempt.problems?.length){const list=document.createElement('ul');attempt.problems.forEach(problem=>{const item=document.createElement('li');item.textContent=problem;list.append(item);});card.append(list);}
    const pre=document.createElement('pre');pre.textContent=attempt.query||attempt.reply||'';card.append(pre);el('evidence').append(card);
  });
  const p=document.createElement('p');p.className='query-note';p.textContent='Checks establish whether a query can run. They do not prove that its meaning matches your question.';el('evidence').append(p);
}
function badge(text,state='') {el('result-badge').textContent=text;el('result-badge').className='result-badge '+state;}
function setBusy(value) {busy=value;el('question').disabled=value;el('results').setAttribute('aria-busy',String(value));document.querySelectorAll('.example-item').forEach(b=>b.disabled=value);el('ask-label').textContent=value?'Exploring…':'Explore answer';syncQuestion();}
el('question-form').addEventListener('submit',async event=>{
  event.preventDefault();if(busy||!el('question').value.trim())return;setBusy(true);selectTab('answer');badge('Looking for answers','loading');el('status').textContent='Running your question against the local graph.';
  currentResult=null;el('answer-toolbar').hidden=true;el('copy-query').disabled=true;el('copy-query').querySelector('span').textContent='Copy query';clearTimeout(copyTimer);el('attempt-count').hidden=true;el('evidence').replaceChildren();el('query').textContent='Preparing your query…';
  const loading=document.createElement('div');loading.className='loading-state';const spinner=document.createElement('span');spinner.className='spinner';loading.append(spinner,document.createTextNode('Following the connections…'));el('answer').replaceChildren(loading);
  try {
    const response=await fetch('/?'+new URLSearchParams({question:el('question').value.trim(),dataset:APP.dataset}));const data=await response.json();if(!response.ok)throw Error(data.error||'The request could not be completed.');
    el('query').textContent=data.query||'No query was generated.';el('copy-query').disabled=!data.query;renderEvidence(data);
    if(data.status==='answered'&&data.result){currentResult=data.result;renderAnswer(data.result);badge('Answer ready','success');el('status').textContent='Answer ready. Results are displayed below.';}
    else{const title=data.status==='unsupported'?'Choose one of the example questions.':data.status==='refused'?'The graph cannot answer this question.':'A valid query could not be produced.';message(title,data.reason||'Try another question.');badge(data.status==='refused'?'Missing information':data.status==='unsupported'?'Example mode':'Query not completed','warning');el('status').textContent=title;}
  } catch(error) {badge('Unable to connect','error');message('Something interrupted the request.',error.message);el('query').textContent='No query is available for this request.';el('status').textContent='Request failed: '+error.message;}
  finally{setBusy(false);}
});
el('question').addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){event.preventDefault();el('question-form').requestSubmit();}});
el('copy-query').addEventListener('click',async()=>{
  try{await navigator.clipboard.writeText(el('query').textContent);el('copy-query').querySelector('span').textContent='Copied';}
  catch{el('copy-query').querySelector('span').textContent='Select text to copy';const range=document.createRange();range.selectNodeContents(el('query'));const selection=getSelection();selection.removeAllRanges();selection.addRange(range);}
  copyTimer=setTimeout(()=>el('copy-query').querySelector('span').textContent='Copy query',2200);
});
el('download').addEventListener('click',()=>{
  if(!currentResult?.rows)return;
  const cell=v=>{let value=String(v??'');if(/^[=+\-@\t\r]/.test(value))value="'"+value;return '"'+value.replaceAll('"','""')+'"';};
  const csv=[currentResult.columns.map(cell).join(','),...currentResult.rows.map(r=>currentResult.columns.map(c=>cell(r[c])).join(','))].join('\r\n');
  const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='oulad-answer.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
