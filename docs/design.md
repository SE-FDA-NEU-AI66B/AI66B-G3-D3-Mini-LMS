# Milestone 2 — Design Document


## 1. Architecture



## 2. Data model

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

## 3. API design

### Auth / session

| Method | Path | Input | Success | Errors |
|---|---|---|---|---|
| GET | `/login` | — | `302` redirect to university SSO | — |
| GET | `/api/auth/sso/callback` | `code` / SSO assertion | `200` `{user_id, email, full_name, role}` + session cookie | `401` invalid SSO assertion <br/> `403` `"Account is disabled"` (US06) |
| GET | `/api/me` | — | `200` current user `{user_id, email, full_name, role}` | `401` not signed in |

### Student — P0

| Method | Path | Input | Success | Errors |
|---|---|---|---|---|
| GET | `/api/quizzes` | — | `200` `{count, quizzes:[{quiz_id,title,course_code,due_at,time_limit_min}]}` visible per BR6 | `401` unauth <br/> `403` not Student <br/> `503` DB down |
| POST | `/api/quizzes/{quizId}/attempts` | — | `200` active attempt `{attempt_id, quiz_id, started_at, remaining_seconds, questions?}` — resumes existing active attempt instead of creating a second one (BR1) | `401` unauth <br/> `403` not enrolled / not Student <br/> `404` quiz not found <br/> `422` quiz not `Published` or due date passed (BR6) |
| GET | `/api/attempts/{attemptId}` | — | `200` attempt state `{attempt_id, remaining_seconds, questions:[...], saved_answers, tab_switch_count}` | `401` unauth <br/> `403` not attempt owner <br/> `404` attempt not found |
| PUT | `/api/attempts/{attemptId}/answers/{questionId}` | `chosen_option_id` or `text_answer` | `200` saved answer | `401` unauth <br/> `403` not attempt owner <br/> `404` attempt/question not found <br/> `409` attempt already submitted <br/> `422` option/question type mismatch |
| POST | `/api/attempts/{attemptId}/tab-switch` | — | `200` `{tab_switch_count}` — used for BR10 flagging | `401` unauth <br/> `403` not attempt owner <br/> `404` attempt not found <br/> `409` attempt already submitted |
| POST | `/api/attempts/{attemptId}/submit` | `{auto_submitted?: boolean}` | `200` `{attempt_id, score, total, percentage:"80.00%", auto_submitted}` within 2s (US04, BR3, BR4, BR5). If timer expired, returns `auto_submitted: true` and message `"Time is up."` | `401` unauth <br/> `403` not attempt owner <br/> `404` attempt not found <br/> `409` already submitted |
| GET | `/api/attempts/{attemptId}/result` | — | `200` `{score,total,percentage,answers_released, questions?}` — per-question detail only if answers released (US10) | `401` unauth <br/> `403` not attempt owner <br/> `404` attempt not found <br/> `409` attempt not submitted |
| GET | `/api/results` | — | `200` past attempts list with quiz title, date, score, percentage | `401` unauth <br/> `403` not Student |

### Lecturer — P0

| Method | Path | Input | Success | Errors |
|---|---|---|---|---|
| POST | `/api/instructor/quizzes` | `course_id, title, time_limit_min, due_at` | `201` `{quiz_id, status:"Draft", ...}` (US01) | `401` unauth <br/> `403` not Lecturer / not owner of course (BR8) <br/> `404` course not found <br/> `422` `"Title is required"` / `time_limit_min` outside 5–120 (BR2) / invalid `due_at` |
| PUT | `/api/instructor/quizzes/{quizId}` | `title, time_limit_min, due_at` | `200` updated quiz | `401` unauth <br/> `403` not owner <br/> `404` quiz not found <br/> `422` validation error |
| POST | `/api/instructor/quizzes/{quizId}/questions` | `{question_type:"MCQ"\|"SHORT", prompt, options?:[{label,text,is_correct}], accepted_answers?}` | `201` created question (US01) | `401` unauth <br/> `403` not owner <br/> `404` quiz not found <br/> `422` MCQ must have exactly 4 options and exactly 1 correct; SHORT missing accepted answer |
| PUT | `/api/instructor/quizzes/{quizId}/questions/{questionId}` | same as POST question | `200` updated question | `401` unauth <br/> `403` not owner <br/> `404` quiz/question not found <br/> `422` validation error |
| DELETE | `/api/instructor/quizzes/{quizId}/questions/{questionId}` | — | `204` deleted | `401` unauth <br/> `403` not owner <br/> `404` quiz/question not found |
| POST | `/api/instructor/quizzes/{quizId}/publish` | — | `200` `{quiz_id, status:"Published"}` (US05) | `401` unauth <br/> `403` not owner <br/> `404` quiz not found <br/> `422` no questions / due date already passed |
| POST | `/api/instructor/quizzes/{quizId}/unpublish` | — | `200` `{quiz_id, status:"Unpublished"}`, existing attempts preserved (US05) | `401` unauth <br/> `403` not owner <br/> `404` quiz not found |
| GET | `/api/instructor/quizzes` | — | `200` lecturer’s quiz list | `401` unauth <br/> `403` not Lecturer |
| GET | `/api/instructor/quizzes/{quizId}/students` | — | `200` roster with attempted/not attempted, score, and `flagged` if `tab_switch_count > 3` (BR10) | `401` unauth <br/> `403` not owner <br/> `404` quiz not found |
| GET | `/api/instructor/stats/{quizId}` | — | `200` average, distribution, per-question difficulty | `401` unauth <br/> `403` not owner <br/> `404` quiz not found |

### Admin — P0

| Method | Path | Input | Success | Errors |
|---|---|---|---|---|
| POST | `/api/admin/accounts` | `email, full_name, role` | `201` created account (US06) | `401` unauth <br/> `403` not Admin <br/> `409` email already exists <br/> `422` invalid role |
| PATCH | `/api/admin/accounts/{userId}/status` | `{status:"Active"\|"Disabled"}` | `200` updated account | `401` unauth <br/> `403` not Admin <br/> `404` user not found <br/> `422` invalid status |
| GET | `/api/admin/accounts` | `role?, status?` | `200` account list | `401` unauth <br/> `403` not Admin |
| POST | `/api/admin/courses` | `code, name, lecturer_email` | `201` created course (US11) | `401` unauth <br/> `403` not Admin <br/> `409` course code already exists <br/> `422` lecturer not found or not Lecturer |
| PATCH | `/api/admin/courses/{courseId}/lecturer` | `{lecturer_email: string \| null}` | `200` updated course | `401` unauth <br/> `403` not Admin <br/> `404` course not found <br/> `409` `"Assign another lecturer first"` when removing without replacement (BR9) <br/> `422` lecturer invalid/not Lecturer |
| GET | `/api/admin/courses` | — | `200` course list | `401` unauth <br/> `403` not Admin |
| POST | `/api/admin/courses/{courseId}/enrollments` | `{student_email}` | `201` enrollment created (US12) | `401` unauth <br/> `403` not Admin <br/> `404` course/student not found <br/> `409` already enrolled <br/> `422` user is not Student |
| DELETE | `/api/admin/courses/{courseId}/enrollments/{studentId}` | — | `204` removed | `401` unauth <br/> `403` not Admin <br/> `404` enrollment not found |
| GET | `/api/admin/courses/{courseId}/students` | — | `200` course roster | `401` unauth <br/> `403` not Admin <br/> `404` course not found |

### P0 coverage check

| P0 story | Endpoints |
|---|---|
| US01 Lecturer creates quiz | `POST /api/instructor/quizzes`, `POST /api/instructor/quizzes/{quizId}/questions` |
| US02 Student sees available quizzes | `GET /api/quizzes` |
| US03 Student takes quiz with timer | `POST /api/quizzes/{quizId}/attempts`, `GET /api/attempts/{attemptId}`, `PUT /api/attempts/{attemptId}/answers/{questionId}`, `POST /api/attempts/{attemptId}/submit` |
| US04 Automatic grading + immediate score | `POST /api/attempts/{attemptId}/submit`, `GET /api/attempts/{attemptId}/result` |
| US05 Lecturer publishes / unpublishes | `POST /api/instructor/quizzes/{quizId}/publish`, `POST /api/instructor/quizzes/{quizId}/unpublish` |
| US06 Admin manages accounts | `POST /api/admin/accounts`, `PATCH /api/admin/accounts/{userId}/status`, `GET /api/auth/sso/callback` |
| US11 Admin creates courses + assigns lecturer | `POST /api/admin/courses`, `PATCH /api/admin/courses/{courseId}/lecturer` |
| US12 Admin enrolls students | `POST /api/admin/courses/{courseId}/enrollments`, `DELETE /api/admin/courses/{courseId}/enrollments/{studentId}` |

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
