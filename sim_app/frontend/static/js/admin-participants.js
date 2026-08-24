import {esc,gbp,message,number} from "./render.js";

export async function renderAdminParticipants(root,api,auth,language="en"){
  if(!auth.is_admin){root.innerHTML=`<section class="card">${message("Administrator authorization is required.","error")}</section>`;return}
  const labels=await api.get(`/api/v1/admin/content/${language}`);
  const admin=labels||{};
  root.innerHTML=`<section class="card"><div class="eyebrow">${esc(admin.title||"Admin panel")}</div><nav class="admin-tabs" aria-label="Admin pages"><a class="btn secondary" href="/admin">${esc(admin.sessions_title||"Session management")}</a><a class="btn" href="/admin/participants">${esc(admin.participant_results_page||"Participant results")}</a></nav><h1>${esc(admin.participant_results_title||"Participant results")}</h1><p class="lead">${esc(admin.participant_results_note||"All participant identifiers and their final results across your study sessions.")}</p><div id="participant-results"><div class="spinner"></div></div></section>`;
  try{
    const rows=await api.get("/api/v1/admin/participants");
    const host=root.querySelector("#participant-results");
    host.innerHTML=rows.length?`<div class="admin-results-panel"><div class="admin-results-toolbar"><div><span class="admin-results-count">${rows.length}</span> <span>${esc(admin.participant_count_label||"participants listed")}</span></div><span class="admin-results-hint">${esc(admin.participant_results_note||"Final results across all study sessions")}</span></div><div class="table-wrap"><table class="admin-results"><thead><tr><th>${esc(admin.participant_code_label||"Participant code")}</th><th>${esc(admin.prolific_id_label||"Prolific ID")}</th><th>${esc(admin.session_code_label||"Session")}</th><th class="numeric">${esc(admin.final_score_label||"Final score")}</th><th class="numeric">${esc(admin.bonus_label||"Bonus")}</th><th class="numeric">${esc(admin.payout_label||"Payout (GBP)")}</th><th>${esc(admin.status||"Status")}</th></tr></thead><tbody>${rows.map(resultRow).join("")}</tbody></table></div></div>`:message(admin.no_participant_results||"No participant identifiers are available yet.");
  }catch(error){root.querySelector("#participant-results").innerHTML=message(error.message,"error")}

  function resultRow(row){
    const participantCode=row.participant_code||"—";
    const prolificId=row.prolific_pid||(!row.participant_code?row.participant_identifier:"")||"—";
    const score=row.final_score==null?"—":`${number(row.final_score)} / 100`;
    const bonus=row.performance_bonus_gbp==null?"—":gbp(row.performance_bonus_gbp);
    const payout=row.payout_gbp==null?"—":gbp(row.payout_gbp);
    const status=row.status||"—";
    const statusClass=String(status).toLowerCase().replace(/[^a-z0-9_-]/g,"-");
    return `<tr><td class="identifier-cell"><strong>${esc(participantCode)}</strong></td><td class="identifier-cell prolific-cell">${esc(prolificId)}</td><td class="session-cell">${esc(row.session_code||"—")}</td><td class="numeric">${esc(score)}</td><td class="numeric">${esc(bonus)}</td><td class="numeric">${esc(payout)}</td><td><span class="admin-status admin-status-${statusClass}">${esc(status)}</span></td></tr>`;
  }
}
