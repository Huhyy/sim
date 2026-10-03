"""Local-only UI preview. Uses disposable in-memory data; never production data.

python scripts/preview_ui.py
Open http://127.0.0.1:8765/review to review an authenticated simulation.
"""
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
from fastapi.responses import RedirectResponse
from sim_app.api.app import create_app
from sim_app.application.principal import ParticipantPrincipal
from sim_app.application.services import ExperimentService
from sim_app.application.state import ParticipantState
from sim_app.application.admin_services import AdminService
from sim_app.auth.browser_session import BrowserSessionManager
from sim_app.config import SCENARIO_VERSION
from sim_app.persistence.memory import InMemoryExperimentRepository
from sim_app.persistence.admin_memory import MemoryAdminRepository
from sim_app.domain.experimental_conditions import condition_config

service = ExperimentService(InMemoryExperimentRepository())
manager = BrowserSessionManager('disposable-local-ui-preview', secure=False)
app = create_app(service=service, browser_session_manager=manager, admin_service=AdminService(MemoryAdminRepository()), docs_enabled=False)

@app.get('/review')
def review():
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.session_id = str(uuid.uuid4()); state.page = 'simulation'
    for key, value in condition_config('C1').items(): setattr(state, key, value)
    state.treatment_bound = True
    account = uuid.uuid4().hex * 2
    service.create_session(state, account_key=account, request_id='local-ui-preview')
    response = RedirectResponse('/')
    manager.set_principal_cookie(response, ParticipantPrincipal(account, email='review@example.test', display_name='Review participant', is_admin=True, bound_session_id=state.session_id))
    return response

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8765, log_level='error')
