# INSTALL — rebuild the full OneGov #2 build, step by step

This guide turns the base repo + the committed change-set artifact into a complete, **running**
build (scenario engine + GreenPT chatbot Phases 1–7), with the ~70 MB H3 datasets included.
It assumes you can copy-paste into a terminal but does **not** assume git/Python expertise.
Every command says what it does and what you should see.

**End state:** `knarayanareddy/onegov2-spatial-assistant` (your fork of the data-carrying base) on a
branch `full-build`, with the change-set applied, **132 backend tests passing**, and the API running.

---

## TL;DR (the whole flow)
```
fork the base on github.com  →  clone YOUR fork  →  make a branch
→  drop the change-set in (unzip the zip, or decode the artifact)
→  commit + push  →  python venv + install deps + run tests (132)  →  run the app
```
If you just want it on your laptop (not on GitHub), do steps 1, 3–4, 7 and skip the push.

---

## 0. What you need (prerequisites)

| Tool | Why | Check it's installed |
|---|---|---|
| **GitHub account** | to fork + push | log in at github.com |
| **Git** | clone/commit/push | `git --version` |
| **Python 3.12+** | backend + tests | `python3.12 --version` |
| **Node.js 18+** + npm | frontend (optional) | `node --version` |
| **curl, unzip, base64** | only for the artifact-decode path | `curl --version` etc. |

### Install the tools
**macOS** (with [Homebrew](https://brew.sh)):
```bash
brew install git python@3.12 node
```
**Ubuntu/Debian Linux:**
```bash
sudo apt update && sudo apt install -y git curl unzip python3.12 python3.12-venv nodejs npm
```
**Windows:** install [Git for Windows](https://git-scm.com/download/win) (gives you **Git Bash** — use it for the bash commands below), [Python 3.12](https://www.python.org/downloads/) (tick *"Add python.exe to PATH"*), and [Node.js](https://nodejs.org). PowerShell variants are given where commands differ.

> No Python 3.12? Easiest cross-platform installer is **uv**:
> `curl -LsSf https://astral.sh/uv/install.sh | sh` then `uv python install 3.12`.
> (Windows PowerShell: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`.)

---

## 1. Authenticate Git with GitHub (needed to *push*)

Pick **one** method. (You can skip this if you only want a local build, not a push.)

### Option A — GitHub CLI (recommended, easiest)
```bash
# install: macOS `brew install gh`; Linux see cli.github.com; Windows `winget install GitHub.cli`
gh auth login
# choose: GitHub.com → HTTPS → "Login with a web browser" → paste the one-time code
```
This also configures git so `git push` "just works". Verify: `gh auth status`.

### Option B — HTTPS + Personal Access Token (PAT)
1. github.com → your avatar → **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**.
2. Scope: tick **`repo`**. Generate, copy the token (starts `ghp_…`).
3. When `git push` asks for a password, **paste the token** (not your account password). To avoid re-typing: `git config --global credential.helper store` (caches it after the first push).

### Option C — SSH keys
```bash
ssh-keygen -t ed25519 -C "you@example.com"      # press Enter through the prompts
cat ~/.ssh/id_ed25519.pub                         # copy this
# github.com → Settings → SSH and GPG keys → New SSH key → paste → save
ssh -T git@github.com                             # should greet you by username
```
If you use SSH, clone with the `git@github.com:` URL in step 3 instead of the `https://` one.

---

## 2. Fork the data-carrying base repo (one click)

1. Open **https://github.com/govtechnl/onegov2-spatial-assistant**.
2. Top-right → **Fork** → keep the name → **Create fork**.
3. You now have **`https://github.com/knarayanareddy/onegov2-spatial-assistant`** — a copy that
   **includes `src/backend/data/` + `src/backend/extra_data/` (~70 MB of H3 parquet)**.

> Why fork instead of a plain new repo? The fork carries the datasets, which are too big to push
> through the API/zip. This is the only step that *must* be you (a fork is a per-user action).

---

## 3. Clone your fork and make a working branch
```bash
# HTTPS (Option A/B):
git clone https://github.com/knarayanareddy/onegov2-spatial-assistant.git
# …or SSH (Option C):
# git clone git@github.com:knarayanareddy/onegov2-spatial-assistant.git

cd onegov2-spatial-assistant
git checkout -b full-build
```
What you should see: a `Cloning into…` progress (it pulls the 70 MB data, may take a minute), then
`Switched to a new branch 'full-build'`. Sanity-check the data is there:
```bash
find src/backend/data src/backend/extra_data -name '*.parquet' | wc -l    # -> 88
```
(Windows PowerShell: `(Get-ChildItem src/backend/data,src/backend/extra_data -Recurse -Filter *.parquet).Count`)

---

## 4. Put the change-set on top — pick ONE path

The change-set (scenario engine + chatbot Phases 1–7 + docs) is **111 files** that overlay the base.
Both paths produce the same result; **Path B is simplest** if you still have the zip from chat.

### Path B (simplest) — unzip the file you already have
```bash
# from inside the onegov2-spatial-assistant folder:
unzip -o /path/to/onegov2-build-combined.zip -d .
```
(Windows PowerShell: `Expand-Archive -Path C:\path\to\onegov2-build-combined.zip -DestinationPath . -Force`)

### Path A (self-contained) — decode the base64 artifact from your `onegov2` repo
**macOS / Linux / Git Bash:**
```bash
curl -sL https://raw.githubusercontent.com/knarayanareddy/onegov2/full-build/build/onegov2-build-combined.zip.b64 -o cs.b64
base64 --decode cs.b64 > cs.zip      # macOS alt if needed: base64 -D -i cs.b64 -o cs.zip
unzip -o cs.zip -d .
rm cs.b64 cs.zip
```
**Windows PowerShell:**
```powershell
Invoke-WebRequest "https://raw.githubusercontent.com/knarayanareddy/onegov2/full-build/build/onegov2-build-combined.zip.b64" -OutFile cs.b64
$b = (Get-Content cs.b64 -Raw) -replace '\s',''
[IO.File]::WriteAllBytes("$PWD\cs.zip", [Convert]::FromBase64String($b))
Expand-Archive cs.zip -DestinationPath . -Force
Remove-Item cs.b64, cs.zip
```
> If the artifact URL 404s, the repo may be private — open the file on github.com and use **Download raw**, or `gh repo clone knarayanareddy/onegov2` and copy `build/onegov2-build-combined.zip.b64` locally.

### Verify the overlay landed
```bash
git status --short | wc -l                                   # many changed/new files
ls src/backend/app/services/chatbot/service.py               # exists -> chatbot is in
ls src/backend/app/services/scenario/real_scoring.py         # exists -> engine is in
```

---

## 5. Commit and push
```bash
git add -A
git commit -m "Add scenario engine + GreenPT chatbot (Phases 1-7)"
git push -u origin full-build
```
- First push will trigger your auth (browser via gh, or PAT prompt, or SSH key).
- Expected tail: `* [new branch]      full-build -> full-build`.
- **Open a PR (optional):** the push output prints a "Create a pull request" link, or run
  `gh pr create --fill --base main --head full-build`.

---

## 6. Backend — install and run the tests (Python ≥ 3.12)

```bash
cd src/backend

# create + activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
                                     # Windows Git Bash:  source .venv/Scripts/activate

python -m pip install --upgrade pip

# install the project's runtime deps:
pip install -e .

# install the EXTRA deps this build adds + the test runner (robust on any pip version):
pip install fpdf2 h3 httpx pyjwt pytest pytest-asyncio aiosqlite
```
> Why the extra line: the change-set uses `fpdf2` (PDF), `h3` (area selection), `httpx` (PDOK/Waterinfo)
> and `pyjwt` (auth). If your `pip` is **≥ 25.1** you can instead run `pip install -e . --group dev`,
> or with **uv**: `uv sync` — both pull everything from `pyproject.toml`. The explicit line above always works.

Run the suite + the source gate:
```bash
PYTHONPATH=. python -m pytest tests_scenario tests_chatbot -q
# expected: 132 passed
PYTHONPATH=. python scripts/check_assumption_sources.py
# expected: ASSUMPTION SOURCE GATE: PASSED
```

Run the API:
```bash
PYTHONPATH=. uvicorn app.main:app --reload --port 8001
```
Leave it running; in a second terminal, smoke-test it (see §9).

---

## 7. Frontend (optional)
```bash
cd src/frontend
npm install
npm run dev        # opens the dev server (usually http://localhost:5173)
```
> If `npm install` fails on `@pzh-temporary/...` packages, you need the PZH package registry
> configured (an `.npmrc` with the registry + token, provided by PZH). The backend + tests do **not**
> need the frontend.

The full app via Docker (alternative to the two steps above): from the repo root,
`cp src/backend/.env.example src/backend/.env` (set `GREENPT_KEY`), `cp src/frontend/.env.example src/frontend/.env`, then `docker compose up --build` → http://localhost:5173.

---

## 8. Optional production configuration (everything below is OFF by default)
Create `src/backend/.env` (never commit secrets):
```bash
GREENPT_KEY=...                      # live GreenPT answers/extraction (else deterministic fallbacks)
AUTH_MODE=jwt                        # or "header" behind an OIDC proxy; identifies users
AUTH_JWT_JWKS_URL=...                # your SSO (Keycloak/Azure AD); add AUTH_REQUIRED=true to enforce
FAQ_CACHE_BACKEND=postgres           # persist the FAQ cache ...
AUDIT_BACKEND=postgres               # ... and the audit trail
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
WATERINFO_LIVE=true                  # live RWS chloride for intake scenarios
MLFLOW_ENABLED=true                  # scenario + descriptive tracing
```
Create the Postgres tables (only if you set the postgres backends):
```bash
cd src/backend && alembic upgrade head      # creates faq_cache + audit_log
```

---

## 9. Verify end-to-end
With the API running on :8001 (from §6):
```bash
curl http://localhost:8001/api/health
# -> {"status":"ok"} (or similar)

curl -s -X POST http://localhost:8001/api/scenario/uncertainty \
  -H 'Content-Type: application/json' \
  -d '{"question":"Verzilting op de Hollandse IJssel in 2040"}'
# -> JSON with "n_total":5 and a verdict distribution (the uncertainty band)

curl -s http://localhost:8001/api/kennisbasis | head -c 300
# -> the dataset inventory (themes + sources + freshness)
```
Open http://localhost:8001/docs for the interactive API (Swagger) listing every endpoint.

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `git push` → *Authentication failed* | Use a **PAT** as the password (not your account password), or `gh auth login`, or switch to the SSH clone URL. |
| `ModuleNotFoundError: fpdf / h3 / httpx / jwt` | You skipped the extra-deps line in §6: `pip install fpdf2 h3 httpx pyjwt`. |
| `error: invalid choice: '--group'` | Old pip. Use the explicit `pip install …` line in §6, or `pip install --upgrade pip`, or `uv sync`. |
| `python3.12: command not found` | Install it (§0) or use `uv python install 3.12 && uv venv -p 3.12 .venv`. |
| Tests can't find `app` | Run pytest with `PYTHONPATH=.` from `src/backend`. |
| Windows: `base64`/`unzip` not found | Use **Git Bash**, or the PowerShell variants in §4 (`[Convert]::FromBase64String` + `Expand-Archive`). |
| `npm install` fails on `@pzh-temporary/*` | Configure the PZH npm registry (`.npmrc` + token), or skip the frontend. |
| Weird diffs / CRLF warnings on Windows | `git config --global core.autocrlf input` before committing. |
| Clone is slow / huge | That's the 70 MB parquet; let it finish, or `git clone --depth 1` for a shallow copy. |
| `alembic upgrade head` errors | Only needed for the Postgres backends; ensure `DATABASE_URL` is set and the DB is reachable. |

---

## Done
You now have a complete, running build: 132 passing tests, the API on :8001, and (optionally) the
frontend + Postgres + live integrations. For the architecture and per-module detail see
`docs/onegov2_design_v4_current_build.md`; for env specifics see `SETUP.md`.
