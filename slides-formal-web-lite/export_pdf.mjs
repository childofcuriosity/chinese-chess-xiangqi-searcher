/** Export the local tutorial as a searchable, vector PDF. */
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); }
catch (error) {
  const globalModule = process.env.PLAYWRIGHT_MODULE_PATH || (process.env.APPDATA && path.join(process.env.APPDATA, 'npm/node_modules/playwright'));
  if (!globalModule) throw error;
  playwright = require(globalModule);
}
const here = path.dirname(fileURLToPath(import.meta.url));
const output = path.join(here, 'xiangqi-engine-tutorial.pdf');
const qaIndex=process.argv.indexOf('--qa-dir');
const qaDir=qaIndex>=0 ? path.resolve(process.argv[qaIndex+1]) : null;
if(qaDir)fs.mkdirSync(qaDir,{recursive:true});
const browser=await playwright.chromium.launch({headless:true});
try {
  const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(here,'index.html')).href+'?export-pdf',{waitUntil:'load'});
  await page.waitForFunction(()=>document.documentElement.dataset.slidesReady==='true');
  await page.emulateMedia({media:'screen'});
  const audit=await page.evaluate(()=>[...document.querySelectorAll('#slides>section')].map(s=>{
    const r=s.getBoundingClientRect();
    const elements=[...s.querySelectorAll('h1,h2,h3,p,.step,td,th,pre,.board-card,.teaching-figure,.tree-stage')].filter(e=>!e.closest('aside'));
    const overflow=elements.filter(e=>{const b=e.getBoundingClientRect();return b.bottom>r.bottom-25 || b.right>r.right-20 || b.left<r.left;}).map(e=>e.textContent.slice(0,90));
    return {id:s.id,title:s.querySelector('h1,h2')?.textContent,fontSize:getComputedStyle(s).fontSize,overflow};
  }));
  const broken=await page.locator('img').evaluateAll(xs=>xs.filter(x=>!x.complete||!x.naturalWidth).map(x=>x.src));
  if(errors.length||broken.length)throw new Error(JSON.stringify({errors,broken}));
  if(audit.some(x=>x.overflow.length))throw new Error('Slide overflow: '+JSON.stringify(audit.filter(x=>x.overflow.length)));
  await page.pdf({path:output,printBackground:true,preferCSSPageSize:true,tagged:true});
  if(qaDir){
    fs.writeFileSync(path.join(qaDir,'audit.json'),JSON.stringify(audit,null,2));
    for(let i=0;i<audit.length;i++)await page.locator('#slides>section').nth(i).screenshot({path:path.join(qaDir,`${String(i+1).padStart(3,'0')}.png`)});
  }
  console.log(`Exported ${audit.length} pages: ${output}`);
} finally { await browser.close(); }
