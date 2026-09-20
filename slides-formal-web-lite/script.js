(function(){
  const chapters=window.XQ_CHAPTERS||[];
  const slidesRoot=document.querySelector('#slides');
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const chapterBySlide=new Map();
  const pendingBoards=[];
  const shortSources=sources=>(sources||[]).map(String).filter(s=>/\.(?:cpp|py|h):\d+$/i.test(s)||/^PDF\s*P?\d+/i.test(s)).map(s=>s.replace(/^.*[\\/]/,'')).slice(0,3);
  const gateMeta=[
    {ids:['01'],label:'规则与走法',hint:'表示棋盘、生成候选、试走与撤销'},
    {ids:['03'],label:'局面评价',hint:'子力、位置与静态判断'},
    {ids:['04','05'],label:'向前搜索',hint:'对手应手、缓存、剪枝与时间'}
  ];

  function notesHtml(slide){
    const timing=(slide.steps||[]).length?`\n\n【揭示时机】${slide.steps.map((s,i)=>`第${i+1}拍：${s}`).join('；')}`:'';
    const sources=(slide.sources||[]).length?`\n\n【证据】${slide.sources.join('；')}`:'';
    return `<aside class="notes">${esc((slide.notes||'本页讲稿待补充。')+timing+sources).replace(/\n/g,'<br>')}</aside>`;
  }
  function stepsHtml(steps=[]){return steps.length?`<div class="steps">${steps.map((s,i)=>`<div class="step fragment" data-fragment-index="${i}">${esc(s)}</div>`).join('')}</div>`:''}
  function boardsHtml(slide){
    const boards=slide.boards||[]; if(!boards.length)return '';
    return `<div class="boards" style="--board-count:${Math.min(boards.length,4)}">${boards.map((b,i)=>{const id=`board-${slide.id}-${i}`;pendingBoards.push([id,b]);const step=b.fragmentIndex??b.step;return `<div class="board-card ${step!=null?'fragment':''}" ${step!=null?`data-fragment-index="${step}"`:''}><div class="board-host" id="${id}"></div>${b.caption?`<div class="board-caption">${esc(b.caption)}</div>`:''}${b.subcaption?`<div class="board-subcaption">${esc(b.subcaption)}</div>`:''}</div>`}).join('')}</div>`;
  }
  function cardsHtml(cards=[]){return cards.length?`<div class="cards" style="--card-cols:${Math.min(cards.length,3)}">${cards.map((c,i)=>`<article class="card fragment" data-fragment-index="${i}">${c.kicker?`<div class="card-kicker">${esc(c.kicker)}</div>`:''}<h3>${esc(c.title)}</h3><p>${esc(c.text)}</p></article>`).join('')}</div>`:''}
  function tableHtml(t){if(!t)return'';return `<table class="data-table"><thead><tr>${(t.headers||[]).map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${(t.rows||[]).map((r,i)=>`<tr class="fragment" data-fragment-index="${i}">${r.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>`}
  function figureHtml(f){if(!f)return'';const legend=(f.legend||[]).length?`<div class="figure-legend">${f.legend.map(item=>`<span><i style="--legend-color:${esc(item.color)}"></i>${esc(item.text)}</span>`).join('')}</div>`:'';return `<figure class="teaching-figure"><img src="${esc(f.src)}" alt="${esc(f.alt)}">${legend}<figcaption><span class="figure-caption">${esc(f.caption)}</span><span class="figure-credit">${esc(f.credit)}</span></figcaption></figure>`}
  function treeHtml(t={}){
    if(t.kind==='minimax'&&Array.isArray(t.values)){
      const v=t.values,a=Math.min(v[0],v[1]),b=Math.min(v[2],v[3]);
      return `<div class="tree-stage teaching-tree"><div class="tree-root">红方 MAX <b class="fragment" data-fragment-index="2">= ${Math.max(a,b)}</b></div><div class="tree-branches" style="--tree-cols:2"><div class="tree-branch fragment" data-fragment-index="0"><div class="tree-label">A · 黑方 MIN = ${a}</div><div class="tree-children"><div class="tree-leaf">${esc(v[0])}</div><div class="tree-leaf bad">${esc(v[1])}</div></div></div><div class="tree-branch fragment" data-fragment-index="1"><div class="tree-label">B · 黑方 MIN = ${b}</div><div class="tree-children"><div class="tree-leaf bad">${esc(v[2])}</div><div class="tree-leaf">${esc(v[3])}</div></div></div></div>${t.caption?`<div class="board-subcaption">${esc(t.caption)}</div>`:''}</div>`;
    }
    if(t.kind==='alphabeta'&&Array.isArray(t.values)){
      const [a1,a2,b1]=t.values,stage=Number(t.stage||1),a=Math.min(a1,a2);
      if(stage===1)return `<div class="tree-stage teaching-tree"><div class="tree-root">红方 MAX</div><div class="tree-branches" style="--tree-cols:2"><div class="tree-branch"><div class="tree-label">A · 黑方 MIN <b class="fragment" data-fragment-index="2">= ${a}</b></div><div class="tree-children"><div class="tree-leaf fragment" data-fragment-index="0">${esc(a1)}</div><div class="tree-leaf fragment" data-fragment-index="1">${esc(a2)}</div></div></div><div class="tree-branch muted-tree"><div class="tree-label">B · 稍后再看</div></div></div>${t.caption?`<div class="board-subcaption">${esc(t.caption)}</div>`:''}</div>`;
      if(stage===2)return `<div class="tree-stage teaching-tree"><div class="tree-root">红方 MAX <b>已有 A = ${a}</b></div><div class="tree-branches" style="--tree-cols:2"><div class="tree-branch"><div class="tree-label best-label">A = ${a}</div></div><div class="tree-branch"><div class="tree-label">B · 黑方 MIN</div><div class="tree-children"><div class="tree-leaf bad fragment" data-fragment-index="0">${esc(b1)}</div><div class="tree-leaf fragment" data-fragment-index="1">?</div><div class="tree-leaf fragment" data-fragment-index="1">?</div></div></div></div>${t.caption?`<div class="board-subcaption">${esc(t.caption)}</div>`:''}</div>`;
      return `<div class="tree-stage teaching-tree"><div class="tree-root">红方 MAX <b>已有 A = ${a}</b></div><div class="tree-branches" style="--tree-cols:2"><div class="tree-branch"><div class="tree-label best-label">选择 A = ${a}</div></div><div class="tree-branch"><div class="tree-label">B ≤ ${esc(b1)}</div><div class="tree-children"><div class="tree-leaf bad">${esc(b1)}</div><div class="tree-leaf cut fragment" data-fragment-index="0">不搜</div><div class="tree-leaf cut fragment" data-fragment-index="0">不搜</div></div></div></div>${t.caption?`<div class="board-subcaption">${esc(t.caption)}</div>`:''}</div>`;
    }
    let branches=t.branches||[];
    if(!branches.length&&t.kind==='ordering') branches=[{label:'原顺序',children:(t.before||[]).map(v=>({label:v}))},{label:'先找好走法',children:(t.after||[]).map((v,i)=>({label:v,best:i===0}))}];
    return `<div class="tree-stage"><div class="tree-root">${esc(t.root||(t.kind==='minimax'?'我方选择 MAX':t.kind==='alphabeta'?'Alpha-Beta':'候选走法'))}</div><div class="tree-branches" style="--tree-cols:${Math.max(branches.length,1)}">${branches.map((b,i)=>`<div class="tree-branch fragment" data-fragment-index="${b.step??i}"><div class="tree-label">${esc(b.label||'分支')}${b.value!=null?` = ${esc(b.value)}`:''}</div><div class="tree-children">${(b.children||[]).map(c=>`<div class="tree-leaf ${c.cut?'cut':''} ${c.best?'best':''} ${c.bad?'bad':''}">${esc(c.label??c.value??'?')}</div>`).join('')}</div></div>`).join('')}</div>${t.caption?`<div class="board-subcaption">${esc(t.caption)}</div>`:''}</div>`
  }
  function routeHtml(current=0){return `<div class="route">${gateMeta.map((g,i)=>`${i?'<i class="route-line"></i>':''}<div class="route-node ${i<current?'done':''} ${i===current?'current':''}"><b>${esc(g.label)}</b><small>${esc(g.hint)}</small></div>`).join('')}</div>`}
  function contentHtml(slide){
    const blocks={
      boards:boardsHtml(slide),
      tree:slide.tree?treeHtml(slide.tree):'',
      code:slide.code?`<div><pre><code>${esc(slide.code)}</code></pre>${slide.codeNote?`<div class="code-note">${esc(slide.codeNote)}</div>`:''}</div>`:'',
      table:tableHtml(slide.table),
      figure:figureHtml(slide.figure),
      cards:cardsHtml(slide.cards),
      steps:stepsHtml(slide.steps)
    };
    if(slide.layout==='map'&&!blocks.boards&&!blocks.tree&&!blocks.code&&!blocks.table&&!blocks.cards&&!blocks.figure)return `${routeHtml(slide.currentChapter||0)}${blocks.steps}`;
    const order={tree:['tree','boards','figure','code','table','cards','steps'],code:['code','boards','figure','cards','table','tree','steps'],table:['table','boards','figure','cards','code','tree','steps'],cards:['cards','boards','figure','code','table','tree','steps'],board:['boards','figure','code','table','cards','tree','steps'],compare:['boards','figure','cards','table','code','tree','steps'],heatmap:['boards','figure','table','cards','code','tree','steps'],map:['boards','figure','cards','tree','table','code','steps'],figure:['figure','cards','table','code','boards','tree','steps']}[slide.layout]||['boards','figure','tree','code','table','cards','steps'];
    const used=order.filter(k=>blocks[k]).map(k=>blocks[k]);
    if(!used.length)return '<p class="lead">内容正在汇入。</p>';
    if(used.length===1)return used[0];
    if((slide.boards||[]).length>=3&&blocks.boards){const rest=order.filter(k=>k!=='boards'&&blocks[k]).map(k=>blocks[k]);return `<div class="wide-layout">${blocks.boards}<div class="supplement-row">${rest.join('')}</div></div>`}
    return `<div class="content-grid"><div>${used[0]}</div><div class="supplement-stack">${used.slice(1).join('')}</div></div>`;
  }
  function addSection(html,chapterId,slideId){const wrap=document.createElement('div');wrap.innerHTML=html.trim();const section=wrap.firstElementChild;slidesRoot.appendChild(section);chapterBySlide.set(slideId,chapterId)}

  if(!chapters.length){
    addSection(`<section id="empty"><p class="eyebrow">正式版构建器</p><h1>章节内容正在汇入</h1><p class="lead">运行 build.py 后，章节脚本会按文件名加载到这里。</p>${notesHtml({notes:'这是空壳提示页。章节文件写入后会自动替换为正式内容。'})}</section>`,'','empty');
  } else {
    addSection(`<section id="title" class="section-cover"><p class="eyebrow">业余象棋引擎</p><h1>如何让电脑帮你下棋</h1><p class="chapter-summary">从什么都不会开始，一关一关造出能思考的象棋搭子。</p><p class="chapter-count">M 打开冒险地图 · S 打开演讲者视图</p>${notesHtml({notes:'开场先讲个人动机：我下不过别人，但电脑算得快。能不能让电脑帮我下棋？今天我们从什么都没有开始，一起把它造出来。'})}</section>`,'','title');
    chapters.forEach((chapter,ci)=>{
    (chapter.slides||[]).forEach(slide=>{const screenSources=shortSources(slide.sources);addSection(`<section id="${esc(slide.id)}" data-chapter="${esc(chapter.id)}"><p class="eyebrow">${esc(slide.eyebrow||chapter.title)}</p><h2>${esc(slide.title)}</h2>${slide.lead?`<p class="lead">${esc(slide.lead)}</p>`:''}${contentHtml(slide)}${slide.takeaway?`<p class="takeaway fragment">${esc(slide.takeaway)}</p>`:''}${screenSources.length?`<div class="source-tag">证据：${esc(screenSources.join(' · '))}</div>`:''}${notesHtml(slide)}</section>`,chapter.id,slide.id)});
    });
  }

  pendingBoards.forEach(([id,b])=>XiangqiBoard.render(`#${id}`,b));
  const nav=document.querySelector('#chapterNav');
  nav.innerHTML=`<div class="nav-panel"><h2>三个阶段</h2><div class="nav-grid">${gateMeta.map((g,i)=>{const c=chapters.find(x=>g.ids.includes(String(x.id))),target=c?.slides?.[0]?.id;return `<button class="nav-item" ${target?`data-target="${esc(target)}"`:''}><b>0${i+1}</b><span>${esc(g.label)}</span><small>${esc(g.hint)}</small></button>`}).join('')}</div><div class="nav-hint">点击跳转 · M 或 Esc 关闭</div></div>`;
  function toggleNav(force){nav.classList.toggle('open',force===undefined?!nav.classList.contains('open'):force)}
  nav.addEventListener('click',e=>{const btn=e.target.closest('[data-target]');if(btn){const target=document.getElementById(btn.dataset.target);Reveal.slide([...slidesRoot.children].indexOf(target));toggleNav(false)}else if(e.target===nav)toggleNav(false)});

  Reveal.initialize({hash:true,controls:true,progress:true,slideNumber:false,center:true,width:1280,height:720,margin:.045,transition:'none',backgroundTransition:'none',navigationMode:'linear',controlsTutorial:false,pdfSeparateFragments:false,plugins:[RevealNotes]});
  function updateMeta(){const current=Reveal.getCurrentSlide();const chapter=chapters.find(c=>c.id===(current?.dataset.chapter||chapterBySlide.get(current?.id)));document.querySelector('#chapterName').textContent=chapter?.title||'';const i=Reveal.getIndices().h;document.querySelector('#slideCounter').textContent=`${i+1} / ${slidesRoot.children.length}`}
  Reveal.on('ready',updateMeta);Reveal.on('slidechanged',updateMeta);
  document.addEventListener('keydown',e=>{if(e.key.toLowerCase()==='m'){e.preventDefault();toggleNav()}if(e.key==='Escape'&&nav.classList.contains('open')){e.stopImmediatePropagation();toggleNav(false)}},true);
})();
