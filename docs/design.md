# Milestone 2 — Design Document


## 1. Architecture

Mini-LMS is a **three-tier layered monolith**: a single FastAPI process serves HTML pages, applies business rules in services, and speaks SQL to PostgreSQL. A mock SSO sits outside our boundary as an external system. Every arrow below is labelled with what travels along it.


```text
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Student  │    │ Lecturer │    │ Admin    │
  │ (browser)│    │ (browser)│    │ (browser)│
  └────┬─────┘    └────┬─────┘    └────┬─────┘
       │               │               │
       └───────────────┼───────────────┘
                       │ HTTPS / HTML forms
                       ▼
  ┌─────────────────────────────────────────────────┐      ┌──────────────────┐
  │   FastAPI web app  (src/app.py)                 │ (1)  │  Mock SSO        │
  │   ┌───────────────────────────────────────┐     │─────▶  /authorize      │
  │   │ Presentation: static CSS              │     │ 302  │  (external)      │
  │   └────────────┬──────────────────────────┘     │      │                  │
  │                │                                │      │                  │
  │                │ function calls                 │ (2)  │                  │
  │   ┌────────────▼──────────────────────────┐     ◀─────│                  │
  │   │ Services (business rules BR1–BR10)    │     │id_tok│                  │
  │   │ quiz ; attempt ; grading ; admin      │     │      └──────────────────┘
  │   └────────────┬──────────────────────────┘     │
  │                │                                │
  │                │ SQLAlchemy / psycopg           │
  │   ┌────────────▼──────────────────────────┐     │
  │   │ Repositories (queries only)           │     │
  │   └────────────┬──────────────────────────┘     │
  └────────────────┼────────────────────────────────┘
                   │ SQL over TCP (localhost:5432)
                   ▼
          ┌─────────────────────┐
          │  PostgreSQL         │
          │                     │
          └─────────────────────┘
```

| From → To | Payload | Purpose |
|---|---|---|
| Browser → FastAPI | HTTPS / HTML form POST | User interaction |
| FastAPI → Mock SSO | OIDC-lite redirect to `/mock-sso/authorize` | Login (step 1) |
| Mock SSO → FastAPI | `id_token` (JSON) + `code` to `/auth/callback` | Identity assertion (step 2) |
| FastAPI → PostgreSQL | SQL over TCP on `localhost:5432` | Read / write |
| FastAPI → Browser | Rendered HTML + static CSS | Response |

All validation and permission checks live in the **service layer**, never in the client.

---

## 2. Data model

Eight tables. The full ERD image lives at `docs/images/erd.png`; its source is `docs/diagrams/erd.puml`.

![ERD](images/erd.png)

**The ERD in brief (full attributes in the image):**

```text
  user ──1:N──▶ course (as lecturer_id)
  user ──1:N──▶ enrollment ◀──N:1── course
  course ──1:N──▶ quiz
  user ──1:N──▶ quiz (as created_by)
  quiz ──1:N──▶ question ──1:N──▶ option
  quiz ──1:N──▶ attempt ──1:N──▶ answer ──N:1── question
  user ──1:N──▶ attempt (as student_id)
```

| Table | Purpose | Columns | Constraint · M1 rule |
|---|---|---|---|
| **user** | Every person who can sign in. | `user_id` PK · `email` UNIQUE NOT NULL · `full_name` · `role` ENUM(Student, Lecturer, Admin) · `status` ENUM(Active, Disabled) · `created_at` | `email` UNIQUE → identity key from SSO (**BR7**). `status='Disabled'` blocks login (**US06**). |
| **course** | A taught unit that quizzes belong to. | `course_id` PK · `code` UNIQUE · `name` · `lecturer_id` FK → user NOT NULL | `lecturer_id NOT NULL` → exactly one lecturer per course (**BR9**). |
| **enrollment** | M:N link between students and courses. | `enrollment_id` PK · `student_id` FK · `course_id` FK · `enrolled_at` · `status` ENUM(Active, Removed) · **UNIQUE(student_id, course_id)** | UNIQUE prevents double enrolment (**US12**). Only `Active` rows count for quiz visibility (**BR6**). |
| **quiz** | A quiz inside a course. | `quiz_id` PK · `course_id` FK · `created_by` FK · `title` · `time_limit_min` INT · `due_at` TIMESTAMP · `status` ENUM(Draft, Published, Unpublished) · `answers_released` BOOL · `created_at` | `CHECK (time_limit_min BETWEEN 5 AND 120)` (**BR2**). `status='Published'` gates visibility (**BR6**). `answers_released` gates **US10**. |
| **question** | One question in a quiz. | `question_id` PK · `quiz_id` FK · `position` INT · `question_type` ENUM(MCQ, SHORT) · `prompt` TEXT · `accepted_answers` TEXT (JSON, for SHORT) · `points` INT DEFAULT 1 · **UNIQUE(quiz_id, position)** | `points = 1` (**BR4**). |
| **option** | One selectable choice for an MCQ. | `option_id` PK · `question_id` FK · `label` CHAR(1) · `text` · `is_correct` BOOL | Exactly one `is_correct=TRUE` per MCQ (**BR4**). |
| **attempt** | One student's attempt on one quiz. | `attempt_id` PK · `quiz_id` FK · `student_id` FK · `started_at` · `submitted_at` NULL · `auto_submitted` BOOL · `score` INT NULL · `total` INT NULL · `tab_switch_count` INT DEFAULT 0 · **PARTIAL UNIQUE(student_id, quiz_id) WHERE submitted_at IS NULL** | Partial UNIQUE (**BR1**). `auto_submitted` (**BR3**). `tab_switch_count > 3` → ⚠ flag (**BR10**). |
| **answer** | One question's answer inside an attempt. | `answer_id` PK · `attempt_id` FK · `question_id` FK · `chosen_option_id` FK NULL · `text_answer` TEXT NULL · `is_correct` BOOL · **UNIQUE(attempt_id, question_id)** | `is_correct` computed at submit time (**BR4**). Required for **US10** (per-question review). |

Every table, PK, and FK above appears in `erd.puml`; the image and this table agree.

---

## 3. API design

Sixteen endpoints covering every P0 story. Each error code points at the business rule it enforces.

| # | Method | Path | Role | Input | Success | Errors |
|---|---|---|---|---|---|---|
| 1 | POST | `/auth/login` | G | — | 302 redirect to mock SSO | 500 SSO unreachable |
| 2 | GET | `/auth/callback` | G | `code` | 302 to `/dashboard`, cookie set | 401 invalid SSO token (**BR7**) |
| 3 | GET | `/api/quizzes` | U | — | 200 list of visible quizzes | 401 not signed in |
| 4 | GET | `/api/quizzes/{id}` | U | — | 200 quiz + questions | 404 unknown quiz · 403 not enrolled (**BR6/BR8**) |
| 5 | POST | `/api/quizzes` | A | title, time_limit_min, due_at, course_id | 201 quiz_id | 400 malformed · 422 time limit out of range (**BR2**) · 403 not assigned to course (**BR8**) |
| 6 | PUT | `/api/quizzes/{id}/publish` | A | — | 200 status = Published | 404 unknown · 422 no questions · 403 not owner |
| 7 | PUT | `/api/quizzes/{id}/unpublish` | A | — | 200 status = Unpublished | 404 unknown · 403 not owner |
| 8 | POST | `/api/attempts` | U | quiz_id | 201 attempt_id | 409 active attempt exists (**BR1**) · 422 quiz not visible (**BR6**) |
| 9 | POST | `/api/attempts/{id}/submit` | U | answers[], auto=false | 200 score, total, percent | 404 unknown · 422 timer expired (**BR3**) · 403 not owner |
| 10 | GET | `/api/attempts/{id}/result` | U | — | 200 score/total/percent (+ per-question if released) | 404 unknown · 403 not owner |
| 11 | GET | `/api/quizzes/{id}/students` | A | — | 200 roster + per-student status + ⚠ flag | 403 not owner (**BR8**) · 404 unknown |
| 12 | GET | `/api/quizzes/{id}/stats` | A | — | 200 average, distribution, difficulty | 403 not owner · 404 unknown |
| 13 | POST | `/api/admin/accounts` | AD | email, full_name, role | 201 user_id | 409 email exists · 422 invalid role |
| 14 | POST | `/api/admin/courses` | AD | code, name, lecturer_id | 201 course_id | 409 code exists · 422 lecturer_id not a Lecturer |
| 15 | PUT | `/api/admin/courses/{id}/lecturer` | AD | lecturer_id | 200 updated | 404 unknown · 422 not a Lecturer (**BR9**) |
| 16 | POST | `/api/admin/courses/{id}/students` | AD | student_id | 201 enrollment_id | 404 unknown · 409 already enrolled |

**Story coverage.** US01 (#5) · US02 (#3) · US03 (#8, #9) · US04 (#9, #10) · US05 (#6, #7) · US06 (#13) · US11 (#14, #15) · US12 (#16) · US07 (#10) · US08 (#12) · US09 (#12) · US10 (#10 with `answers_released=true`).

---

## 4. Walking skeleton

**Route:** `GET /api/quizzes` · **Table read:** `quiz` (joined with `course`).

**Seed size:** 3 courses, 2 lecturers, 10 students, 12 quizzes, 48 questions, 2 completed attempts with answers.

**Screenshot:** `docs/images/walking-skeleton.png` — the dashboard rendering 12 seeded quizzes.

**The SQL behind the page:**

```sql
SELECT q.quiz_id, q.title, c.code AS course_code, q.due_at, q.time_limit_min
FROM quiz q
JOIN course c      ON c.course_id = q.course_id
JOIN enrollment e  ON e.course_id = c.course_id
WHERE q.status = 'Published'
  AND q.due_at > NOW()
  AND e.student_id = :current_user_id
  AND e.status = 'Active'
ORDER BY q.due_at;
```

**Proof that the data is real.** Stop the local PostgreSQL service:

- **macOS (Homebrew):** `brew services stop postgresql@{version}`
- **Linux (systemd):** `sudo systemctl stop postgresql`
- **Windows:** Services panel → stop the `postgresql-x64-{version}` service

Then refresh the dashboard → FastAPI logs a `500 Internal Server Error`. Restart the service, refresh → the page recovers. This is the check described in `docs/SETUP.md`.

**Full install steps:** see `docs/SETUP.md`.

---

## 5. Design decisions

Two ADRs. Each records options, choice, why, and what would make us change our mind.

### ADR-1 — Authentication via mock SSO instead of local passwords

**Options:** (a) local email + password with bcrypt, (b) mock SSO that returns a signed `id_token`, (c) real university OIDC.

**Chose:** **(b) mock SSO.**

**Why:** BR7 fixes SSO as the auth method, but a real university SSO cannot be exercised by the marker on a fresh machine. A 60-line mock SSO reproduces the exact redirect → callback → identity shape while remaining runnable offline. It also keeps `user.email` as the sole identity key — no password column ever enters the schema, so a database leak cannot leak credentials.

**What would change our mind:** if the university provides a sandbox OIDC tenant reachable from anywhere, we swap the mock for the real IdP in Sprint 4. Only `src/services/auth_service.py` changes.

### ADR-2 — Local PostgreSQL instead of SQLite (no Docker this sprint)

**Options:** (a) SQLite file next to the code, (b) PostgreSQL installed locally, (c) PostgreSQL in a Docker container.

**Chose:** **(b) PostgreSQL installed locally.**

**Why:** we want the *same* engine in development, in the demo, and in the schema, so a bug never appears only on demo day. PostgreSQL gives us partial unique indexes (**BR1**) and a real enum type (**BR4**) rather than SQLite workarounds. Docker would add an extra prerequisite to the fresh-machine setup, and this sprint we prefer the simplest environment that still passes the marker's 15-minute test — a local PostgreSQL service started by the operating system. SQLAlchemy models remain dialect-neutral, so the choice is reversible.

**What would change our mind:** if the instructor's machine cannot host a local PostgreSQL at all, we fall back to SQLite in a single sprint — only `db/schema.sql` changes. If we later need fully isolated dev environments, we move to Docker Compose.

---

## 6. What changed since M1

Four changes, ordered by how much they reshaped the document.

1. **Added the Admin role (US06, US11, US12 at P0).** M1 had lecturers managing their own accounts and courses. The reviewer made it clear this overloaded the lecturer's job. Ownership moved to a dedicated administrative role whose scope is roster maintenance only. **BR8** was rewritten to separate *manage* (Admin, write) from *monitor* (Lecturer, read).

2. **Added BR10 — tab-switch cheating signal.** M1 did not model anti-cheating at all. **BR10** now records every tab-switch event on the `attempt` table; more than 3 events in one attempt flags the row, and the flag is visible only to the lecturer in the roster view. No new user story — the flag surfaces inside the existing lecturer monitoring screen.

3. **Added BR7 — authentication delegated to university SSO.** M1's diagrams showed `University SSO` as an actor, but no rule explained what it did. **BR7** closes that gap: Mini-LMS never stores passwords; only the SSO-returned email and the local role are kept.

4. **Added US12 (Admin enrols students) and promoted it to P0.** M1 assumed students self-enrolled or were enrolled by the lecturer. Both were wrong for a course-scoped system. Enrolment is now a first-class admin action, mapped to `POST /api/admin/courses/{id}/students`.