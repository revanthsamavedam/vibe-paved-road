"""vibe-check — the enforcement half of the patterns.

Scans a generated app and fails it against PATTERNS.md. Built to coach,
not punish: every finding names the pattern, why it exists, and the
on-pattern fix the coding agent can apply automatically.

Usage:  python -m validator.vibe_check <project_dir> [--json]
Exit:   0 = pass, 1 = error-severity findings
Scope:  code + config only (.py .js .ts .tsx .jsx .html .json .toml .yaml
        .yml .env* Dockerfiles). Markdown/docs are out of scope — the
        pattern docs themselves name the banned services.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".json",
            ".toml", ".yaml", ".yml"}
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".next", "dist"}
# Hosts a generated app may talk to. Extend per firm; keep it short on purpose.
ALLOWED_HOSTS = ("localhost", "127.0.0.1", "internal.example", "gateway.internal.example")

OFFSITE_FILES = {"vercel.json": "P1", "netlify.toml": "P1", "procfile": "P1",
                 "fly.toml": "P1", "railway.json": "P1", "app.yaml": "P1"}
OFFSITE_RE = re.compile(r"vercel|netlify|heroku|railway\.app|fly\.io|render\.com|\.vercel\.app", re.I)
SECRET_RES = [
    re.compile(r"(api[_-]?key|secret|passwd|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.I),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
]
URL_RE = re.compile(r"https?://([A-Za-z0-9.\-]+)")
CONNSTR_RE = re.compile(r"(postgres|mysql|mongodb)(\+srv)?://", re.I)
FRONTEND_SUFFIXES = {".js", ".ts", ".tsx", ".jsx", ".html"}


@dataclass
class Finding:
    rule: str
    pattern: str
    severity: str  # "error" | "warn"
    file: str
    line: int
    message: str
    fix: str


def _files(root: Path):
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file() and (p.suffix.lower() in SUFFIXES or p.name.startswith(".env")
                            or p.name.lower().startswith("dockerfile")):
            yield p


def check_project(root: str | Path) -> list[Finding]:
    root = Path(root)
    findings: list[Finding] = []
    backend_has_auth = False
    backend_files: list[Path] = []

    for p in root.iterdir():
        if p.is_file() and p.name.lower() in OFFSITE_FILES:
            findings.append(Finding(
                "OFFSITE_CONFIG", OFFSITE_FILES[p.name.lower()], "error", p.name, 1,
                f"'{p.name}' deploys to an offsite PaaS (Pattern P1: internal hosting only).",
                "Delete it. The starter's Dockerfile + internal preview is the deploy path."))

    for p in _files(root):
        rel = str(p.relative_to(root))
        text = p.read_text(encoding="utf-8", errors="ignore")
        is_frontend = "frontend" in rel or p.suffix.lower() in FRONTEND_SUFFIXES and "backend" not in rel
        if p.suffix.lower() == ".py" and "backend" in rel:
            backend_files.append(p)
            low_all = text.lower()
            if "authorization" in low_all or "entra" in low_all or "require_auth" in low_all:
                backend_has_auth = True
        for i, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if OFFSITE_RE.search(line) and p.suffix.lower() != ".md":
                findings.append(Finding(
                    "OFFSITE_HOST", "P1", "error", rel, i,
                    "Reference to an offsite hosting platform (Pattern P1).",
                    "Deploy to the internal platform; preview behind SSO."))
            for rgx in SECRET_RES:
                if rgx.search(line):
                    findings.append(Finding(
                        "HARDCODED_SECRET", "P4", "error", rel, i,
                        "Possible hardcoded secret (Pattern P4: apps hold zero secrets).",
                        "Remove it. Service credentials live in Vault/CyberArk; "
                        "config names go in .env.example with empty values."))
                    break
            for m in URL_RE.finditer(line):
                host = m.group(1).lower()
                if not any(host == a or host.endswith("." + a) for a in ALLOWED_HOSTS):
                    findings.append(Finding(
                        "EXTERNAL_CALL", "P5", "error", rel, i,
                        f"Call/URL to non-allowlisted host '{host}' (Pattern P5).",
                        "Use an internal API or the sanctioned gateway, vendor the asset, "
                        "or register an approved exception."))
            if CONNSTR_RE.search(line):
                findings.append(Finding(
                    "CONNECTION_STRING", "P3", "error", rel, i,
                    "Database connection string in code (Pattern P3).",
                    "Data goes through the service tier with its own governed account; "
                    "generated code never carries connection strings."))
            if is_frontend and ("database_url" in low or "createconnection" in low
                                or "psycopg" in low or "pg-promise" in low):
                findings.append(Finding(
                    "FRONTEND_DB", "P3", "error", rel, i,
                    "Frontend appears to reach a database directly (Pattern P3).",
                    "Frontend calls only the app's backend API; the API calls the data tier."))

    if backend_files and not backend_has_auth:
        findings.append(Finding(
            "MISSING_AUTH", "P2", "error", str(backend_files[0].relative_to(root)), 1,
            "Backend has no sign of token validation / auth (Pattern P2: Entra SSO + internal JWT authz).",
            "Add the starter's auth middleware — validate the forwarded token on every route except /healthz."))
    return findings


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    findings = check_project(args[0])
    if as_json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for f in findings:
            print(f"[{f.severity.upper()}] {f.rule} ({f.pattern}) {f.file}:{f.line}\n  {f.message}\n  Fix: {f.fix}")
        errors = sum(1 for f in findings if f.severity == "error")
        print(f"\n{errors} error(s), {len(findings) - errors} warning(s) — "
              + ("FAIL" if errors else "PASS"))
    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
