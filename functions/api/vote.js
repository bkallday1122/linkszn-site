// Cloudflare Pages Function: shared deal votes in KV (binding VOTES). No secrets.
// GET /api/vote?slug=..  -> {up,down,score}
// POST /api/vote {slug, vote: 1|-1, prev: 0|1|-1} -> {up,down,score}
const SLUG=/^[a-z0-9-]{3,120}$/;
const j=(o,s=200)=>new Response(JSON.stringify(o),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}});
async function get(env,slug){const v=await env.VOTES.get('v:'+slug,'json');return v||{up:0,down:0};}
const out=v=>({up:v.up,down:v.down,score:v.up-v.down});
export async function onRequestGet({request,env}){
  const slug=new URL(request.url).searchParams.get('slug')||'';
  if(!SLUG.test(slug))return j({error:'bad slug'},400);
  return j(out(await get(env,slug)));
}
export async function onRequestPost({request,env}){
  let b; try{b=await request.json();}catch{return j({error:'bad json'},400);}
  const {slug,vote}=b; const prev=[1,-1].includes(b.prev)?b.prev:0;
  if(!SLUG.test(slug||'')||![1,-1].includes(vote))return j({error:'bad vote'},400);
  if(!await env.VOTES.get('slug-ok:'+slug)){ // only real deal pages
    const r=await env.ASSETS.fetch(new URL(`/deals/${slug}/`,request.url));
    const t=r.ok?await r.text():''; if(!t.includes(`/deals/${slug}/"`))return j({error:'unknown deal'},404);
    await env.VOTES.put('slug-ok:'+slug,'1');
  }
  const ip=request.headers.get('cf-connecting-ip')||'0'; const hr=Math.floor(Date.now()/3600e3);
  const rk=`rl:${ip}:${hr}`, n=+(await env.VOTES.get(rk)||0);
  if(n>=30)return j({error:'rate limited'},429);
  const dk=`d:${ip}:${slug}`; if(await env.VOTES.get(dk)===String(vote))return j({...out(await get(env,slug)),dup:true});
  await env.VOTES.put(rk,String(n+1),{expirationTtl:3700});
  await env.VOTES.put(dk,String(vote),{expirationTtl:86400*30});
  const v=await get(env,slug);
  if(prev===1)v.up=Math.max(0,v.up-1); if(prev===-1)v.down=Math.max(0,v.down-1);
  if(vote===1)v.up++; else v.down++;
  await env.VOTES.put('v:'+slug,JSON.stringify(v));
  return j(out(v));
}
