import fs from 'node:fs';
import path from 'node:path';
export const deals = fs.readdirSync('deals').filter(f=>f.endsWith('.json')).map(f=>({...JSON.parse(fs.readFileSync(path.join('deals',f),'utf8')),slug:f.slice(0,-5)})).sort((a,b)=>(Date.parse(b.posted_at)-Date.parse(a.posted_at))||(Date.parse(b.checked_at??0)-Date.parse(a.checked_at??0)));
export const money=(n:number)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n);
export const date=(s:string)=>new Intl.DateTimeFormat('en-US',{dateStyle:'medium',timeStyle:'short',timeZone:'America/New_York'}).format(new Date(s))+' ET';
