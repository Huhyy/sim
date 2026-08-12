const money=new Intl.NumberFormat(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const scoreNumber=new Intl.NumberFormat(undefined,{minimumFractionDigits:0,maximumFractionDigits:2});
export const euro=value=>`${money.format(Number(value||0))} €`;
export const gbp=value=>`${money.format(Number(value||0))} GBP`;
export const number=value=>scoreNumber.format(Number(value||0));
export function safeUrl(value){try{const url=new URL(String(value||""),location.origin);return ["http:","https:"].includes(url.protocol)?url.href:"#"}catch{return"#"}}
export const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

export function plainLabel(value){
  return String(value??"")
    .replace(/^\s*#{1,6}\s+/,"")
    .replace(/\*\*/g,"")
    .replace(/\{value\}/g,"")
    .replace(/<\/?strong>/gi,"")
    .replace(/\s+/g," ")
    .replace(/:\s*$/,"")
    .trim();
}

function inlineMarkdown(value){
  return value
    .replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>")
    .replace(/`([^`]+)`/g,"<code>$1</code>")
    .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g,"<em>$1</em>");
}

function tableCells(line){
  const trimmed=line.trim().replace(/^\|/,"").replace(/\|$/,"");
  return trimmed.split("|").map(cell=>inlineMarkdown(cell.trim()));
}

function isTableDivider(line){
  return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(line.trim());
}

export function trustedMarkdown(source){
  let text=esc(source).replace(/&lt;div[^&]*&gt;/g,"").replace(/&lt;\/div&gt;/g,"")
    .replace(/&lt;strong&gt;/g,"**").replace(/&lt;\/strong&gt;/g,"**")
    .replace(/&lt;br\s*\/?&gt;/g,"\n")
    .replace(/&lt;ul&gt;/g,"\n").replace(/&lt;\/ul&gt;/g,"\n")
    .replace(/&lt;li&gt;/g,"\n- ").replace(/&lt;\/li&gt;/g,"");
  const lines=text.split("\n"); let html="",listType=null,paragraph=[];
  const flushParagraph=()=>{if(paragraph.length){html+=`<p>${inlineMarkdown(paragraph.join(" "))}</p>`;paragraph=[]}};
  const closeList=()=>{if(listType){html+=`</${listType}>`;listType=null}};
  const openList=type=>{if(listType!==type){closeList();html+=`<${type}>`;listType=type}};
  for(let index=0;index<lines.length;index+=1){
    const line=lines[index].trim();
    if(line.startsWith("|")&&index+1<lines.length&&isTableDivider(lines[index+1])){
      flushParagraph();closeList();
      const header=tableCells(line);index+=2;
      const rows=[];
      while(index<lines.length&&lines[index].trim().startsWith("|")){rows.push(tableCells(lines[index]));index+=1}
      index-=1;
      html+='<div class="rich-table-wrap"><table class="rich-table">';
      if(header.some(cell=>cell.replace(/<[^>]+>/g,"").trim()))html+=`<thead><tr>${header.map(cell=>`<th>${cell}</th>`).join("")}</tr></thead>`;
      html+=`<tbody>${rows.map(row=>`<tr>${row.map((cell,cellIndex)=>`<${cellIndex===0?"th":"td"}>${cell}</${cellIndex===0?"th":"td"}>`).join("")}</tr>`).join("")}</tbody></table></div>`;
      continue;
    }
    const heading=line.match(/^(#{1,3})\s+(.+)$/);
    if(heading){flushParagraph();closeList();const level=heading[1].length;html+=`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`;continue}
    if(/^(-{3,}|\*{3,})$/.test(line)){flushParagraph();closeList();html+="<hr>";continue}
    if(line.startsWith("- ")){flushParagraph();openList("ul");html+=`<li>${inlineMarkdown(line.slice(2))}</li>`;continue}
    const ordered=line.match(/^\d+\.\s+(.+)$/);
    if(ordered){flushParagraph();openList("ol");html+=`<li>${inlineMarkdown(ordered[1])}</li>`;continue}
    if(!line){flushParagraph();closeList();continue}
    closeList();paragraph.push(line);
  }
  flushParagraph();closeList();return html;
}
export const button=(label,cls="btn")=>`<button class="${cls}" type="submit">${esc(label)}</button>`;
export function progress(current,total){return `<div class="progress" aria-label="${current} of ${total}"><span style="width:${Math.max(0,Math.min(100,current/total*100))}%"></span></div>`}
export function message(text,tone="warning"){return `<div class="notice ${tone}">${esc(text)}</div>`}
export function metric(label,value){return `<div class="metric"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`}
export function field(name,label,type="text",value="",attrs=""){return `<label for="${name}">${esc(label)}</label><input id="${name}" name="${name}" type="${type}" value="${esc(value)}" ${attrs}>`}
export function selectField(name,label,options,value=""){return `<label for="${name}">${esc(label)}</label><select id="${name}" name="${name}"><option value=""></option>${options.map(x=>`<option ${x===value?"selected":""} value="${esc(x)}">${esc(x)}</option>`).join("")}</select>`}
