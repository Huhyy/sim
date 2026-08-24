import {esc,gbp,message,number} from "./render.js";

export async function renderAdminParticipants(root,api,auth,language="en"){
  if(!auth.is_admin){root.innerHTML=`<section class="card">${message("Administrator authorization is required.","error")}</section>`;return}
  const labels=await api.get(`/api/v1/admin/content/${language}`);
  const admin=labels||{};
  root.innerHTML=`<section class="card"><div class="eyebrow">${esc(admin.title||"Admin panel")}</div><nav class="admin-tabs" aria-label="Admin pages"><a class="btn secondary" href="/admin">${esc(admin.sessions_title||"Session management")}</a><a class="btn" href="/admin/participants">${esc(admin.participant_results_page||"Participant results")}</a></nav><h1>${esc(admin.participant_results_title||"Participant results")}</h1><p class="lead">${esc(admin.participant_results_note||"All participant identifiers and their final results across your study sessions.")}</p><div id="participant-results"><div class="spinner"></div></div></section>`;
  try{
    const rows=await api.get("/api/v1/admin/participants");
    const host=root.querySelector("#participant-results");
    host.innerHTML=rows.length?`<div class="table-wrap"><table class="admin-results"><thead><tr><th>${esc(admin.participant_id_label||"Participant ID")}</th><th>${esc(admin.session_code_label||"Session")}</th><th>${esc(admin.final_score_label||"Final score")}</th><th>${esc(admin.bonus_label||"Bonus")}</th><th>${esc(admin.payout_label||"Payout (GBP)")}</th><th>${esc(admin.status||"Status")}</th></tr></thead><tbody>${rows.map(resultRow).join("")}</tbody></table></div>`:message(admin.no_participant_results||"No participant identifiers are available yet.");
  }catch(error){root.querySelector("#participant-results").innerHTML=message(error.message,"error")}

  function resultRow(row){
    const score=row.final_score==null?"—":`${number(row.final_score)} / 100`;
    const bonus=row.performance_bonus_gbp==null?"—":gbp(row.performance_bonus_gbp);
    const payout=row.payout_gbp==null?"—":gbp(row.payout_gbp);
    return `<tr><td><strong>${esc(row.participant_code||"—")}</strong></td><td>${esc(row.session_code||"—")}</td><td>${esc(score)}</td><td>${esc(bonus)}</td><td>${esc(payout)}</td><td>${esc(row.status||"—")}</td></tr>`;
  }
}
