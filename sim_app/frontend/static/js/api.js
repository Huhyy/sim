const unresolvedKey = "sim.unresolvedMutation";

export class ApiClient {
  constructor() { this.csrf = null; this.inFlight = false; }
  async request(url, options={}) {
    const headers = {Accept:"application/json", ...(options.headers||{})};
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    if (this.csrf && !["GET","HEAD"].includes(options.method||"GET")) headers["X-CSRF-Token"] = this.csrf;
    headers["X-Request-ID"] = crypto.randomUUID();
    let response;
    try { response = await fetch(url,{...options,headers,credentials:"same-origin"}); }
    catch (error) { throw new ApiError("network_error","Connection lost. Your action was not discarded.",0,true,null,error); }
    const data = await response.json().catch(()=>({}));
    if (!response.ok) {
      const detail=data.error||{};
      throw new ApiError(detail.code||"http_error",detail.message||`Request failed (${response.status})`,response.status,!!detail.retryable,detail.request_id);
    }
    return data;
  }
  get(url){ return this.request(url); }
  async mutate(url,payload,controls=[]) {
    if(this.inFlight) throw new ApiError("in_flight","An action is already in progress.",0,false);
    const existing=this.unresolved();
    const snapshot=existing && existing.url===url && JSON.stringify(existing.payload)===JSON.stringify(payload)
      ? existing : {url,payload,idempotencyKey:crypto.randomUUID()};
    sessionStorage.setItem(unresolvedKey,JSON.stringify(snapshot));
    this.inFlight=true; controls.forEach(node=>node.disabled=true);
    try {
      const result=await this.request(url,{method:"POST",body:JSON.stringify(payload),headers:{"Idempotency-Key":snapshot.idempotencyKey}});
      sessionStorage.removeItem(unresolvedKey); return result;
    } finally { this.inFlight=false; controls.forEach(node=>node.disabled=false); }
  }
  unresolved(){ try{return JSON.parse(sessionStorage.getItem(unresolvedKey)||"null");}catch{return null;} }
  clearUnresolved(){sessionStorage.removeItem(unresolvedKey)}
}

export class ApiError extends Error {
  constructor(code,message,status,retryable=false,requestId=null,cause=null){super(message,{cause});Object.assign(this,{code,status,retryable,requestId});}
}
