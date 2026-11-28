// 逆雨檔案館宣傳片（雨夜主題）：先跑 reverse1999-capture.js，再 node tutorials/reverse1999-promo.js
const P=require('path').join(__dirname,'..','src')+'/';
const fs=require('fs'); const {spawnSync}=require('child_process');
const st=require(P+'story.js'); const {render,stills}=require(P+'render.js');
const J=require('path').join(__dirname,'..','jobs','r1999-promo'); const A=J+'/assets';
const site=JSON.parse(fs.readFileSync(J+'/site.json'));
const id=(n)=>{const i=site.pages.findIndex(p=>p.navText===n); if(i<1) throw new Error(n); return `p${i}v`;};
const F=[
 ['暴雨年表','01 · THE STORMS','十一場雨，\n一條時間線。','日曆在一九九九與一九一二之間來回折返，每一場雨都標在年表上。'],
 ['章節檔案','02 · THE CHAPTERS','十四間展間。','序幕至第十三章，每一間是一組底片和它們的說明。'],
 ['放映廳','10 · SCREENING ROOM','把故事，\n放給你看。','即時繪製的底片，旁白一句一句浮現。'],
 ['司辰的抉擇','03 · DECISIONS','換你，\n站在她的位置。','八個時刻，選完揭曉主線裡發生的事。'],
 ['你的暴雨','04 · YOUR STORM','走一遍\n屬於你的那場雨。','寫下名字和生日，選一樣想留下的東西。'],
 ['名詞索引','07 · INDEX','每一個名詞，\n都有出處。','術語、組織、人物、地點，標出它出現的章節。'],
 ['入館考核','11 · EXAMINATION','先考試，\n再發證。','十道題，全部出自館內的年表、底片與索引。'],
 ['接龍','05 · THE RELAY','一次一段，\n接著寫下去。',''],
 ['創作坊','06 · ATELIER','替一張底片題寫。',''],
 ['未解之謎','08 · OPEN QUESTIONS','還沒有答案的問題。',''],
 ['值勤台','12 · ON DUTY','記錄員的日常。',''],
];
const copy0={ brand:'逆雨檔案館', intro:'REVERSE: 1999 · UNOFFICIAL FAN ARCHIVE', tagline:'十一場雨，十四章故事。',
 hook:['雨從地面升起。','日曆，往回翻。','有些人，被留在另一邊。'],
 features:F.map(([n,k,t,b])=>{const sid=id(n); const pg=site.pages[+sid.slice(1,-1)]; return {sectionId:sid,kicker:k,title:t,body:b,on:true,img:pg.hero,rect:pg.focus};}),
 gridLine:'十四間展間，\n一座檔案館。', scrollLine:'一路往下，\n都是雨的痕跡。', pagesLine:'每一頁，\n都是一份檔案。', mobileLine:'放進口袋，\n雨也跟著你。',
 outroLine:'An Archive Against the Rain', cta:'進館', source:'manual' };
// 放映廳：鏡頭對準倒數計時
const filmI=site.pages.findIndex(p=>p.navText==='放映廳'); site.pages[filmI].focus={x:500,y:330,w:440,h:170,text:'放映廳'};
const copy=copy0;
const palette={accent:'#d9b77a',accent2:'#b89a63',accent3:'#8fa3b8'};
const tl=st.buildTimeline(site,copy,palette,{length:'full',spot:7,iconStyle:'none',lang:'zh-Hant'});
tl.theme='rain'; tl.numeral='1999'; tl.calm=true;
// 開場用網站自己的入館雨夜當主視覺
tl.scenes.find(s=>s.type==='hero').img='intro.jpg';
console.log(tl.duration+'s', tl.scenes.map(s=>s.type+'@'+s.start).join(' '));
fs.writeFileSync(J+'/tl.json',JSON.stringify(tl));
(async()=>{
 if(process.argv[2]==='stills'){ const pk=(t,n=0,d=2.6)=>tl.scenes.filter(s=>s.type===t)[n].start+d;
   const f=await stills({timeline:tl,assetsDir:A,times:[pk('intro',0,2.4),pk('hook',0,4.6),pk('hero',0,2),pk('feature',0),pk('feature',1),pk('feature',2),pk('grid',0,5),pk('wall',0,2.2),pk('outro',0,3.3)],outPattern:J+'/st_%t.jpg'}); console.log(f.length); return; }
 const music=J+'/music.m4a';
 spawnSync('ffmpeg',['-y','-loglevel','error','-i',J+'/../r1999/theme-suitcase.m4a','-af',`atrim=0:${tl.duration},afade=t=in:d=1,afade=t=out:st=${tl.duration-3}:d=3`,'-c:a','aac','-b:a','192k',music]);
 await render({timeline:tl,assetsDir:A,audioFile:music,outFile:J+'/promo.mp4',log:console.log,onProgress:()=>{}});
 console.log('DONE');
})().catch(e=>{console.error(e);process.exit(1)});
