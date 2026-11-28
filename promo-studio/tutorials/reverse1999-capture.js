// 擷取逆雨檔案館各區塊截圖：node tutorials/reverse1999-capture.js jobs/r1999-promo/assets
const {chromium,devices}=require('playwright'); const fs=require('fs'); const O=process.argv[2];
const SITE='https://reverse-1999-art.vercel.app/';
(async()=>{const b=await chromium.launch({args:['--hide-scrollbars']});
const ctx=await b.newContext({viewport:{width:1440,height:900},deviceScaleFactor:2,locale:'zh-TW'}); const p=await ctx.newPage();
await p.goto(SITE,{waitUntil:'networkidle',timeout:60000}); await p.waitForTimeout(1500);
// 開場入館（雨夜 1999）
await p.screenshot({path:O+'/intro.jpg',type:'jpeg',quality:90});
await p.evaluate(()=>document.querySelectorAll('.gd-intro').forEach(e=>e.remove())); await p.waitForTimeout(600);
const pages=[]; const shot=async(name,id,prep)=>{
  await p.evaluate(h=>location.hash=h,'#'+id); await p.waitForTimeout(1400);
  await p.evaluate(s=>{const el=document.querySelector('#r-'+s); if(el) window.scrollTo(0, el.getBoundingClientRect().top+scrollY-(s==='hall'?0:56));}, id); await p.waitForTimeout(900);
  if(prep) await prep(); 
  const focus=await p.evaluate(s=>{const sec=document.querySelector('#r-'+s); const h=sec&&sec.querySelector('h1,h2'); if(!h) return null; const r=h.getBoundingClientRect(); return {x:r.left,y:r.top,w:Math.min(r.width,900),h:r.height,text:h.innerText.trim()};}, id);
  const lead=await p.evaluate(s=>{const sec=document.querySelector('#r-'+s); const q=sec&&[...sec.querySelectorAll('p')].map(x=>x.innerText.trim()).find(t=>t.length>12&&t.length<160); return q||'';}, id);
  const file=`p${pages.length}_hero.jpg`; await p.screenshot({path:O+'/'+file,type:'jpeg',quality:90});
  pages.push({id,navText:name,hero:file,focus,lead,url:SITE+'#'+id,title:name,description:'',heads:[],colors:{},sections:[],view:true});
  console.log(name, focus&&focus.text, '|', lead.slice(0,40));
};
await shot('大廳','hall');
await shot('暴雨年表','chronicle');
await shot('章節檔案','chapters');
await shot('放映廳','film', async()=>{ await p.locator('#r-film button.film-big').first().click({timeout:3000}).catch(()=>{}); await p.waitForTimeout(7500); });
await p.keyboard.press('Escape').catch(()=>{}); await p.locator('button:has-text("離開")').first().click({timeout:1500}).catch(()=>{}); await p.waitForTimeout(800);
await shot('司辰的抉擇','choices', async()=>{ await p.locator('#r-choices button.opt').first().click({timeout:3000}).catch(()=>{}); await p.waitForTimeout(1500); });
await shot('你的暴雨','rain');
await shot('接龍','relay');
await shot('創作坊','studio');
await shot('名詞索引','index', async()=>{ const i=p.locator('#r-index input').first(); await i.fill('手提箱').catch(()=>{}); await p.waitForTimeout(1200); });
await shot('未解之謎','questions');
await shot('入館考核','quiz');
await shot('值勤台','play');
// 整頁長圖
await p.evaluate(h=>location.hash=h,'#hall'); await p.evaluate(()=>window.scrollTo(0,0)); await p.waitForTimeout(1000);
const H=await p.evaluate(()=>document.documentElement.scrollHeight); const fullH=Math.min(H,7000);
await p.screenshot({path:O+'/full.jpg',type:'jpeg',quality:82,scale:'css',fullPage:true,clip:{x:0,y:0,width:1440,height:fullH}});
pages[0].full='full.jpg'; pages[0].fullH=fullH;
await ctx.close();
// 手機
const m=await b.newContext({...devices['iPhone 15'],viewport:{width:393,height:852},deviceScaleFactor:2}); const mp=await m.newPage();
await mp.goto(SITE,{waitUntil:'networkidle',timeout:60000}); await mp.waitForTimeout(1200); await mp.evaluate(()=>document.querySelectorAll('.gd-intro').forEach(e=>e.remove())); await mp.waitForTimeout(500);
const mh=Math.min(await mp.evaluate(()=>document.documentElement.scrollHeight),4200);
await mp.screenshot({path:O+'/mobile_full.jpg',type:'jpeg',quality:85,scale:'css',fullPage:true,clip:{x:0,y:0,width:393,height:mh}});
await m.close(); await b.close();
fs.writeFileSync(O+'/../site.json',JSON.stringify({pages,mobile:{full:'mobile_full.jpg',h:mh,w:393},iconFile:null,logoFile:null}));
})().catch(e=>{console.error(e);process.exit(1)});
