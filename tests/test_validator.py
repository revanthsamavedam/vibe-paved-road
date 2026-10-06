from pathlib import Path

from validator.vibe_check import check_project

ROOT = Path(__file__).parent.parent
STARTER = ROOT / "templates" / "app-starter"


def _rules(findings):
    return {f.rule for f in findings}


def test_starter_template_passes_clean():
    assert check_project(STARTER) == []


def test_catches_offsite_secret_external_and_frontend_db(tmp_path):
    (tmp_path / "vercel.json").write_text("{}")
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "app.js").write_text(
        "// live at https://myapp.vercel.app\n"
        "const api_key = 'supersecretvalue123';\n"
        "fetch('https://api.random-saas.com/v1');\n"
        "const DATABASE_URL = 'x'; const c = createConnection();\n")
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "main.py").write_text(
        "conn = 'postgres://user:pw@db.internal.example/app'\n")
    rules = _rules(check_project(tmp_path))
    assert {"OFFSITE_CONFIG", "OFFSITE_HOST", "HARDCODED_SECRET",
            "EXTERNAL_CALL", "CONNECTION_STRING", "FRONTEND_DB",
            "MISSING_AUTH"} <= rules


def test_internal_calls_and_auth_pass(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "main.py").write_text(
        "# validates Authorization header via entra token\n"
        "url = 'https://gateway.internal.example/v1'\n")
    assert check_project(tmp_path) == []
