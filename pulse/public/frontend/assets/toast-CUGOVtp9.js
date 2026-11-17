import{J as n}from"./index-TYFazFep.js";let r=0;const c=n([]);function t(s,e="success",i=2600){const o=++r;return c.push({id:o,message:s,type:e}),setTimeout(()=>u(o),i),o}function u(s){const e=c.findIndex(i=>i.id===s);e>=0&&c.splice(e,1)}t.success=s=>t(s,"success");t.error=s=>t(s,"error",4200);t.info=s=>t(s,"info");export{t as a,c as t};
//# sourceMappingURL=toast-CUGOVtp9.js.map
