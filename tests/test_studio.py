import os

os.environ.setdefault("STUDIO_APPS_DIR", "/tmp/vibe-studio-test-apps")

from fastapi.testclient import TestClient  # noqa: E402

from studio.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)
AUTH = {"Authorization": "Bearer demo:alice"}


def _session():
    r = client.post("/api/session", json={"user": "alice"}, headers=AUTH)
    assert r.status_code == 200
    return r.json()


def test_health_and_auth_gate():
    assert client.get("/healthz").status_code == 200
    assert client.post("/api/session", json={"user": "alice"}).status_code == 401


def test_session_scaffolds_and_preview_serves():
    st = _session()
    assert st["validator"] == "pass"
    assert "frontend/index.html" in st["files"]
    page = client.get(st["preview_url"])
    assert page.status_code == 200 and "Vibe App" in page.text


def test_chat_runs_agent_pipeline_end_to_end():
    st = _session()
    r = client.post("/api/chat", json={
        "session_id": st["session_id"],
        "message": "Add a heading about team updates"}, headers=AUTH)
    assert r.status_code == 200
    out = r.json()
    assert out["reply"] and "validator:" in out["reply"]
    assert out["validator"] in ("pass", "fail")
    assert out["agents_used"] == ["builder", "data", "reviewer"]
    assert set(out["reviewer"]) == {"approved", "issues", "summary"}
    # preview still serves after the plan was applied
    assert client.get(out["preview_url"]).status_code == 200


def test_chat_screens_pasted_secrets_before_model():
    st = _session()
    r = client.post("/api/chat", json={
        "session_id": st["session_id"],
        "message": "use this api_key = 'supersecretvalue123' for the data feed"},
        headers=AUTH)
    assert r.status_code == 200
    assert "secret" in r.json()["reply"].lower()
    assert r.json()["changed"] == []
    assert r.json()["agents_used"] == [] and r.json()["reviewer"] is None


def test_preview_items_endpoint_matches_starter_shape():
    _session()
    r = client.get("/api/items", headers=AUTH)
    assert r.status_code == 200 and r.json()["freshness"]
