// Screenshots of rooms as /play draws them, for the art audit (tools/jev_audit.py shots DIR).
//   node tools/audit/shoot_rooms.js ROOMS.json OUTDIR      (ROOMS: [{"vnum": 1042}, ...])
// The game server must be running (python3 src/main.py); it logs in as the gauntlet character
// (tools/gauntlet/config.json) and `goto`s each room, snaps the mood, hides the HUD and saves a JPEG.
// A shot already in OUTDIR is skipped, so a stopped run picks up where it left off. A crashed
// browser is relaunched and the rooms it missed are tried once more at the end.
// On a machine with a GPU it renders with it; SOFTWARE_GL=1 forces SwiftShader (a cloud container).
const fs=require('fs');const {chromium}=require('playwright');const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const CFG=JSON.parse(fs.readFileSync(require('path').join(__dirname,'..','gauntlet','config.json'),'utf8'));
const picks=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));const out=process.argv[3];fs.mkdirSync(out,{recursive:true});
let b=null,p=null;
async function open(){
  if(b) try{await b.close();}catch(e){}
  b=await chromium.launch({args:process.env.SOFTWARE_GL?['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader']:['--enable-webgl','--ignore-gpu-blocklist','--enable-gpu']});
  p=await (await b.newContext({viewport:{width:768,height:480}})).newPage();
  p.on('pageerror',e=>console.log('PAGEERROR',String(e).slice(0,200)));
  await p.goto('http://localhost:4001/play?q=med',{waitUntil:'load'});
  for(let i=0;i<600;i++){if(await p.evaluate(()=>document.getElementById('loading').classList.contains('done')))break;await sleep(1000);}
  await p.evaluate(([n,pw])=>{const f=document.getElementById('login-form');if(f)f.classList.remove('hidden');document.getElementById('login-name').value=n;document.getElementById('login-pass').value=pw;document.getElementById('login-btn').click();},[CFG.character.name,CFG.character.password]);
  for(let i=0;i<600;i++){if(await p.evaluate(()=>!!(MH.state.isLoggedIn&&window.MH3D&&MH3D.hero)))break;await sleep(1000);}
  await p.evaluate(()=>{MH.sendCommand('nohassle',false);});
  await sleep(2000);
}
async function shoot(pk){
  const f=`${out}/${pk.vnum}.jpg`; if(fs.existsSync(f)) return true;
  const t0=Date.now();
  await p.evaluate(()=>MH3D.engine.setManual(false));
  await p.evaluate(v=>MH.sendCommand('goto '+v,false),pk.vnum);
  let ok=false;for(let i=0;i<60;i++){ok=await p.evaluate(v=>{const r=MH3D.heroRoom&&MH3D.heroRoom();return !!r&&r.vnum===v;},pk.vnum);if(ok)break;await sleep(1000);}
  await sleep(6000);
  await p.evaluate(()=>{const E=MH3D.engine;E.setManual(true);E.setMood({},true);for(let i=0;i<3;i++)E.step(1/30,1);
    const cv=document.querySelector('canvas');document.querySelectorAll('body *').forEach(el=>{if(el!==cv&&!el.contains(cv))el.style.visibility='hidden';});});
  await p.screenshot({path:f,type:'jpeg',quality:72,timeout:240000});
  await p.evaluate(()=>{document.querySelectorAll('body *').forEach(el=>{el.style.visibility='';});});
  console.log('shot',pk.vnum,ok?'':'(room not confirmed)',((Date.now()-t0)/1000).toFixed(0)+'s');
  return true;
}
(async()=>{
  await open();
  const missed=[];
  for(const pass of [picks, null]){
    const list=pass||missed.splice(0);
    for(const pk of list){
      try{await shoot(pk);}catch(e){console.log('fail',pk.vnum,String(e).slice(0,120));if(pass)missed.push(pk);try{await open();}catch(e2){console.log('reopen failed',String(e2).slice(0,120));}}
    }
  }
  await b.close();
})();
