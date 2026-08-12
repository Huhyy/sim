const money=new Intl.NumberFormat(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
export const euro=value=>`${money.format(Number(value||0))} €`;
export const gbp=value=>`${money.format(Number(value||0))} GBP`;
export function safeUrl(value){try{const url=new URL(String(value||""),location.origin);return ["http:","https:"].includes(url.protocol)?url.href:"#"}catch{return"#"}}
export const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

export function trustedMarkdown(source){
  let text=esc(source).replace(/&lt;div[^&]*&gt;/g,"").replace(/&lt;\/div&gt;/g,"")
    .replace(/&lt;strong&gt;/g,"**").replace(/&lt;\/strong&gt;/g,"**")
    .replace(/&lt;ul&gt;/g,"\n").replace(/&lt;\/ul&gt;/g,"\n")
    .replace(/&lt;li&gt;/g,"\n- ").replace(/&lt;\/li&gt;/g,"");
  text=text.replace(/^### (.+)$/gm,"<h3>$1</h3>").replace(/^## (.+)$/gm,"<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>");
  const lines=text.split("\n"); let html="",inList=false,paragraph=[];
  const flushParagraph=()=>{if(paragraph.length){html+=`<p>${paragraph.join(" ")}</p>`;paragraph=[]}};
  const closeList=()=>{if(inList){html+="</ul>";inList=false}};
  for(const raw of lines){const line=raw.trim();if(line.startsWith("- ")){flushParagraph();if(!inList){html+="<ul>";inList=true}html+=`<li>${line.slice(2)}</li>`;continue}
    if(!line){flushParagraph();closeList();continue}closeList();if(line.startsWith("<h")){flushParagraph();html+=line}else paragraph.push(line)}
  flushParagraph();closeList();return html;
}
export const button=(label,cls="btn")=>`<button class="${cls}" type="submit">${esc(label)}</button>`;
export function progress(current,total){return `<div class="progress" aria-label="${current} of ${total}"><span style="width:${Math.max(0,Math.min(100,current/total*100))}%"></span></div>`}
export function message(text,tone="warning"){return `<div class="notice ${tone}">${esc(text)}</div>`}
export function metric(label,value){return `<div class="metric"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`}
export function field(name,label,type="text",value="",attrs=""){return `<label for="${name}">${esc(label)}</label><input id="${name}" name="${name}" type="${type}" value="${esc(value)}" ${attrs}>`}
export function selectField(name,label,options,value=""){return `<label for="${name}">${esc(label)}</label><select id="${name}" name="${name}"><option value=""></option>${options.map(x=>`<option ${x===value?"selected":""} value="${esc(x)}">${esc(x)}</option>`).join("")}</select>`}
