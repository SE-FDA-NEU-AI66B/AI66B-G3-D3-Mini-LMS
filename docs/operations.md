# Mini-LMS — Operations

## 1. How to run and release

Live URL: <https://ai66b-g3-d3-mini-lms.onrender.com>  
Demo v1.0: <https://github.com/SE-FDA-NEU-AI66B/AI66B-G3-D3-Mini-LMS/releases/tag/v1.0>  
Test accounts: minhhd@univ.edu / lanpt@univ.edu / admin@univ.edu (all pass: `password123`)


**Platform:** Render's free plan, using one **Web Service** for the FastAPI app and one **Render Postgres** database. Free web services sleep after 15 minutes of inactivity; the first request afterwards pays a ~30–60 second cold start. The M5 brief explicitly permits cold starts, so this is documented, not mitigated. Secrets (`DATABASE_URL`, `SESSION_SECRET`) live in the Render dashboard's Environment tab, not in Git.

**Release flow:** push to a feature branch → open a PR → GitHub Actions `ci.yml` runs → merge to `main` when the PR is approved and the run is green → Render sees the new `main` commit and, with **Auto-Deploy: After CI Checks Pass** turned on, redeploys only if the `ci.yml` run on that commit passed. A failed CI blocks the deploy. The live URL today runs the commit tagged **`v1.0`** (`a05c4b7`).

**Rollback:** Render dashboard → service → **Deploys** tab → the previous successful deploy → **Redeploy**. Takes about two minutes and does not touch git history. If the bad commit is already merged, the same tab can be used to redeploy `v1.0` directly. `git revert <bad-commit>` on `main` is the slower secondary path — it produces a new deploy, but the fix is recorded in the repo for future readers.

---

## 2. The CI pipeline

A single workflow, `.github/workflows/ci.yml`, runs on every push and every PR to `main`/`develop`. A typical green run finishes in **under 60 seconds**. Steps in order:

| Step | What it checks | Typical duration |
|---|---|---|
| Checkout | Fetches the commit under test | 3 s |
| Detect stack | Sets `python=true` if `requirements.txt` exists | 2 s |
| Install dependencies | `pip install -r requirements.txt` + `pytest`, `pytest-cov`, `ruff` | 20–35 s (cached) |
| Lint | `ruff check .` — warning only, non-blocking in the current sprint | 3 s |
| Test | `pytest -v --cov --cov-report=term-missing --junitxml=junit.xml` — the M4 suite (~44 tests) | 5–10 s |
| Publish summary | Parses `junit.xml` into the run's step summary | 2 s |
| Secrets scan | Fails on AWS keys, `ghp_` tokens, private keys, literal `password=` strings, or any `.env`/`.sql`/`.sqlite3`/`.dump` file tracked in Git | 3 s |

The **Deploy gate** is not a job in `ci.yml` — it is Render's own setting. Render monitors the same GitHub commit's check status and only redeploys when every check that `ci.yml` reports is green.

**Latest green run on `main`:** <https://github.com/SE-FDA-NEU-AI66B/AI66B-G3-D3-Mini-LMS/actions/runs/43685697178>

**Branch protection on `main`:** GitHub → Settings → Branches → `main` is protected (required PR review from another team member, required status checks from CI, no direct pushes).

---

## 3. Monitoring

**What we read:** Render dashboard → service → **Logs** tab. Uvicorn writes every request line and every traceback to stderr; the tab streams that stream live and keeps a rolling window. For a runtime that predates an incident, the tab retains the last few days — enough to diagnose the incident the next morning without any extra logging infrastructure.

**What we never log:** passwords (hashed with SHA-256 before any service touches the DB; the plaintext argument is never written to a log line), session tokens, `SESSION_SECRET`, or the database password (`settings.describe_target()` prints `user@host:port/db` — never the password). Route handlers that raise `InstructorServiceError`/`AdminServiceError`/`AttemptServiceError` produce a 4xx with a message that is safe to log; unhandled 5xx is logged by uvicorn's exception middleware.

**What `/health` checks:** it opens a short-lived psycopg connection and runs `SELECT 1`. Returns **200** when the round-trip succeeds, **503** when the DB is unreachable or erroring. `/health/live` is a pure process probe that never touches the DB — used by Render's own health check so a DB blip does not trigger a container restart.

**Two numbers to watch:**

| Metric | Where | What "bad" looks like |
|---|---|---|
| **Error rate** — 5xx responses ÷ total requests | Render dashboard → Metrics tab, filtered by service | > 2 % during a demo day; > 5 % means something real is broken |
| **p95 response time** — the 95th-percentile request latency | Render dashboard → Metrics tab | > 1 s on `/login` or any `/ui/html/*` page; excludes the first request after a cold start |

Both are checked once per demo day during the grading window. A spike in either triggers the rollback in §1 until the cause is identified from the Logs tab.

---

## 4. Known risks and technical debt

Five items, honest about what would break and what we'd do about it.

| Item | Layer | What could happen | Plan |
|---|---|---|---|
| **Render's free Postgres expires 30 days after creation** | infrastructure | All data is deleted if the database is not upgraded before expiry; the live URL then returns 503 until the DB is recreated. If grading falls after day 30, the demo cannot run without intervention. | Accepted for now — mitigate by upgrading the DB to a paid plan before day 30, or migrate to Neon (free, no expiry) if the demo runs past that window. Tracked as [issue placeholder]. |
| **Free web service sleeps after 15 min idle** | infrastructure | First request after a quiet period takes 30–60 s (cold start). A marker clicking the URL without warning will see a slow page. | Accepted — M5 explicitly allows cold starts. Mitigate by opening the URL ~5 minutes before any live demo to warm the container. |
| **`/api/quizzes`, `/api/student/courses`, `/api/student/courses/{id}/quizzes` accept `?email=` and do not check it against the caller** | code | Any visitor can read any student's quiz list or course list by typing a different email into the URL. | Tracked as [issue placeholder] — replace `Query(...)` with `Depends(current_email)` on the three routes; one-line change per route, no schema impact. |
| **Admin course delete uses `pg_terminate_backend` + a hard cascade delete** | code / data | A concurrent query touching the same tables can be killed mid-flight; a mis-click permanently destroys a course and every attempt inside it. No audit trail, no undo. | Tracked as [issue placeholder] — replace the backend sweep with a scoped `FOR UPDATE` lock and add a soft-delete `archived_at` column; only then re-enable the Delete button in the admin UI. |
| **No automated coverage of the repository layer** | tests | A SQL change that compiles but returns the wrong rows would only be caught by clicking through the app. | Accepted — the schema uses PostgreSQL-only features (real ENUM types, `SERIAL`, the partial unique index `attempt_one_active`) that SQLite cannot express; adding a live Postgres to CI would contradict M4's "no real database" rule. Manual verification via `db/init_db.py` + `db/verify_db.py` is the current guard. |

---

## 5. Maintenance plan

Five areas, one named owner each. Owners are taken from the team roster in `README.md`.

| Area | What to do | Owner | How often |
|---|---|---|---|
| **Bugs** | Triage issues by layer (code / data / UI); assign to the layer's owner; merge fixes through the same PR + CI process described in §2 | @thangkaka26 | Weekly during a sprint |
| **Dependency updates** | `pip list --outdated` → review changelogs → bump pins in `requirements.txt` → PR through CI | @BuiDut | Monthly, or immediately on any GitHub security advisory affecting a pinned package |
| **Backups** | `pg_dump` the Render DB into an encrypted archive; store off-platform. **Must run before day 25** of the DB's lifecycle to keep a recovery point ahead of the 30-day expiry | @thangkaka26 | Weekly during the grading window; once before the DB expiry date |
| **Monitoring** | Check §3's two numbers (error rate, p95 latency) and scan the Render Logs tab for new tracebacks | @Altimary | Daily during the grading window; weekly otherwise |
| **Keeping docs true** | Re-read `SETUP.md`, `ui.md`, `testing.md`, `operations.md` after any PR that touches the API surface, the schema, or environment variables | @VizAnh | After every PR of that kind |

---

## 6. Lessons learned

**The shared layout rendered every page unusable.** During M2, we introduced a `MutationObserver` on `layout.js` to strip a legacy footer string after every render. The observer fired on the strip itself, which set `innerHTML`, which fired the observer again — an infinite loop that locked the tab on any page load. It was caught only when a real user opened the app on a real browser; no test we had at the time exercised the layout end-to-end. We removed the observer and replaced it with a one-shot cleanup that writes only when there is something to strip. Next time: any self-modifying DOM code gets a second pair of eyes before merge, and gets a smoke test that renders the layout in a headless browser.

**A fake package broke every clean install.** `requirements.txt` contained `httpx2==2.13.1` and `httpcore2==2.13.1` — neither exists on PyPI. `pip install -r requirements.txt` succeeded on the machine that had already installed the real `httpx` and `httpcore` as transitive dependencies of FastAPI, and failed on every fresh clone. We only noticed the failure when a teammate set up on a new laptop after the sprint had already started. The workaround is documented in `SETUP.md`; the file itself was frozen by team vote before we fixed it. Next time: every dependency pin is added via a tool that resolves from a real PyPI query, never by hand-editing the file, and the first push of a new pin runs in a fresh venv before it merges.

**A `.html` file contained nothing but JavaScript.** During a merge conflict resolution in M3, `src/ui/html/quiz-take.html` was accidentally overwritten with the exact contents of `src/ui/js/quiz-take.js`. The browser received the JS as HTML text, rendered a blank page, and the "Take" button on the dashboard silently failed for two days before anyone clicked it. We rebuilt the file and added a `_FakeConn`-based pytest layer around `attempt_service` so the take-quiz flow has a compile-time guard independent of the browser. Next time: any change to a file whose name ends in `.html` gets its first render diffed against the deployed version before merge — the merge would have been one `diff` command away from caught.