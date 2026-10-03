// A reading transition, confined to narration. Financial controls remain immediate.
// Preserve text nodes and whitespace so selection, wrapping and accessibility work.
export function revealNarrative(host){
  if(!host||matchMedia("(prefers-reduced-motion: reduce)").matches)return;
  const walker=document.createTreeWalker(host,NodeFilter.SHOW_TEXT);
  const nodes=[];
  while(walker.nextNode())nodes.push(walker.currentNode);
  const words=[];
  for(const node of nodes){
    const fragment=document.createDocumentFragment();
    for(const part of node.textContent.split(/(\s+)/)){
      if(!part)continue;
      if(/^\s+$/.test(part)){fragment.append(document.createTextNode(part));continue;}
      const span=document.createElement("span");
      span.className="narrative-word";
      span.textContent=part;
      fragment.append(span);words.push(span);
    }
    node.replaceWith(fragment);
  }
  // Short passages keep a readable cadence; long passages finish within 1.8s.
  const step=Math.min(14,1600/Math.max(1,words.length-1));
  const animations=words.map((word,index)=>word.animate(
    [{opacity:0},{opacity:1}],
    {duration:180,delay:index*step,easing:"ease-out",fill:"backwards"}
  ));
  const finish=()=>{for(const animation of animations)animation.finish();};
  const preference=matchMedia("(prefers-reduced-motion: reduce)");
  const onPreference=event=>{if(event.matches)finish();};
  preference.addEventListener("change",onPreference);
  // Clicking the passage reveals it immediately. Nothing gates the decision.
  host.addEventListener("click",finish,{once:true});
  Promise.all(animations.map(animation=>animation.finished.catch(()=>{}))).then(()=>{
    preference.removeEventListener("change",onPreference);
    host.removeEventListener("click",finish);
    for(const word of words)word.replaceWith(document.createTextNode(word.textContent));
    host.normalize();
  });
}
// Keep the masthead steady while the new page settles into view.
// No outgoing delay, movement, or disabled controls.
export function transitionPage(host){
  for(const animation of host.getAnimations())animation.cancel();
  const preference=matchMedia("(prefers-reduced-motion: reduce)");
  if(preference.matches)return;
  const animation=host.animate([{opacity:0.65},{opacity:1}],{
    duration:180,easing:"ease-out"
  });
  const onPreference=event=>{if(event.matches)animation.finish();};
  preference.addEventListener("change",onPreference);
  animation.finished.catch(()=>{}).finally(()=>preference.removeEventListener("change",onPreference));
}
