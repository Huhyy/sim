from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_has_no_retired_ui_or_frontend_framework_dependency():
    runtime_files = list((ROOT / "sim_app").rglob("*.py")) + [ROOT / "requirements.txt"]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in runtime_files)
    retired = "stream" + "lit"
    assert f"import {retired}" not in combined
    assert f"from {retired}" not in combined
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert retired not in requirements
    for package in ("react", "vue", "angular", "svelte", "vite", "webpack"):
        assert package not in requirements


def test_api_routes_depend_on_services_not_supabase_or_domain_calculation():
    route_files = [
        ROOT / "sim_app/api/routes.py",
        ROOT / "sim_app/api/admin_routes.py",
        ROOT / "sim_app/api/auth_routes.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in route_files)
    assert "supabase" not in combined.lower()
    assert ".table(" not in combined and ".rpc(" not in combined
    assert "compute_month" not in combined and "calculate_final_scores" not in combined


def test_browser_assets_contain_no_authoritative_or_sensitive_state_names():
    browser_files = [
        ROOT / "sim_app/frontend/static/js/app.js",
        ROOT / "sim_app/frontend/static/js/api.js",
        ROOT / "sim_app/frontend/static/js/render.js",
        ROOT / "sim_app/frontend/index.html",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in browser_files)
    for forbidden in (
        "account_key", "ACCOUNT_KEY_PEPPER", "SUPABASE_SERVICE_ROLE_KEY",
        "experimental_condition", "score_frame", "monthly_score_feedback",
        "ParticipantState", "PROLIFIC_API_TOKEN",
    ):
        assert forbidden not in combined


def test_browser_normalizes_session_envelopes_before_building_mutation_urls():
    app_js = (ROOT / "sim_app/frontend/static/js/app.js").read_text(encoding="utf-8")
    assert "normalizeState" in app_js
    assert 'sessionStorage.setItem("sim.session_id"' in app_js
    assert "reloadAuthoritativeState" in app_js
    assert 'error.code==="session_state_invalid"' in app_js
    assert "state=await api.mutate" not in app_js
    assert "state=await api.get" not in app_js


def test_no_node_build_or_cloud_deployment_files_were_added():
    # Phase 6 deliberately adds the production Dockerfile. Frontend build
    # tooling and provider-specific deployment configuration remain deferred.
    forbidden = ("package.json", "vite.config.js", "cloudbuild.yaml")
    assert not [name for name in forbidden if (ROOT / name).exists()]
