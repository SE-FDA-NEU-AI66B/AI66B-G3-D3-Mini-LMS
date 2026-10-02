# Mini-LMS — Setup Guide

This guide takes a **brand-new machine** from zero to a running Mini-LMS API that returns real data from PostgreSQL. Follow it top to bottom; do not skip steps.

**Time to complete:** about 10-15 minutes on a fresh machine.

---

## 1. Prerequisites

Install these before continuing. Versions matter.

| Tool | Minimum version | Check |
|---|---|---|
| Git | 2.40 | `git --version` |
| Python | 3.11 | `python --version` |
| PostgreSQL | 18 | `psql --version` |

### Installing PostgreSQL 18

- **Windows:** download the installer from <https://www.postgresql.org/download/windows/> and run the wizard.
  - Set the `postgres` superuser password to `postgres` for this course.
  - Keep the default port `5432`.
  - The Windows service is created as `postgresql-x64-18`.

  
- **macOS (Homebrew):**
  ```bash
  brew install postgresql@18
  brew services start postgresql@18
  ```
  Homebrew creates a superuser matching your macOS username with no password.

- **Linux (Ubuntu / Debian):**
  ```bash
  sudo sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
  sudo apt update
  sudo apt install -y postgresql-18
  sudo systemctl start postgresql
  sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
  ```

Confirm the database server is reachable:

```bash
psql -U postgres -h localhost -c "SELECT version();"
```

---

## 2. Clone and install

```bash
git https://github.com/SE-FDA-NEU-AI66B/AI66B-G3-D3-Mini-LMS.git
cd AI66B-G3-D3-Mini-LMS
```

Create and activate a virtual environment.

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies.

```bash
pip install -r requirements.txt
```

You should now see `(.venv)` at the start of your shell prompt.

---

## 3. Configure the environment

Copy the example env file.

**macOS / Linux:**
```bash
cp .env.example .env
```

**Windows:**
```powershell
copy .env.example .env
```

Open `.env` and adjust the database credentials to match your machine.

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=minilms
DB_USER=postgres
DB_PASSWORD=postgres
```

| OS | `DB_USER` | `DB_PASSWORD` |
|---|---|---|
| Windows | `postgres` | the password you set during install |
| macOS (Homebrew) | *your macOS username* | *(leave blank)* |
| Linux (apt) | `postgres` | `postgres` |

Never commit `.env`. The repository holds only `.env.example`.

---

## 4. Create and seed the database

One command creates the `minilms` database (if missing), applies `db/schema.sql`, and loads `db/seed.sql`.

```bash
python db/init_db.py
```

Expected output:

```
Target: postgres@localhost:5432/minilms

Running schema and seed ...
  → db/schema.sql
  → db/seed.sql

Database initialised.
  users       : 13
  courses     : 3
  enrollments : 20
  quizzes     : 12
  questions   : 48
  options     : 96
  attempts    : 2
  answers     : 8
```

The script is safe to run more than once. It drops and recreates every table, then reseeds.

---

## 5. Verify the database from the terminal

Run the verification script. It executes the **same SQL** as the walking-skeleton API route and prints the result to the terminal.

```bash
python db/verify_db.py
```

Expected output:

```
Target:  postgres@localhost:5432/minilms
Student: minhhd@univ.edu
Query:   walking skeleton (visible quizzes for this student)

ID    Course    Title                       Due                Limit
--------------------------------------------------------------------------
2     ACC101    ACC101 Weekly Quiz 1        2026-11-01 23:59    15 min
3     ACC101    ACC101 Weekly Quiz 2        2026-11-08 23:59    15 min
1     ACC101    ACC101 Midterm Quiz         2026-11-15 23:59    30 min
6     ACC201    ACC201 Weekly Quiz 1        2026-11-03 23:59    15 min
7     ACC201    ACC201 Weekly Quiz 2        2026-11-10 23:59    15 min
5     ACC201    ACC201 Midterm Quiz         2026-11-18 23:59    30 min

6 quiz(zes) fetched from the database. Walking skeleton OK.
```

If you see this table, PostgreSQL holds the data and Python can read it.

> **Note on dates.** The query filters by `q.due_at > NOW()`. If your system clock is past `2026-12-14`, adjust the dates in `db/seed.sql` and re-run `python db/init_db.py`.

---

## 6. Start the API server

```bash
python src/app.py
```

The terminal prints a banner, then uvicorn's own startup lines:

```
Mini-LMS is starting. Open one of these in your browser:
  http://localhost:8000/
  http://127.0.0.1:8000/
  API docs: http://localhost:8000/docs

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Leave this terminal running. Open a **new** terminal for the next step.

> **Why not open `0.0.0.0:8000`?** That is the bind address, not a browsable host. Always use `localhost` or `127.0.0.1` in your browser.

---

## 7. View the API in your browser

Open **<http://localhost:8000/docs>**.

You will see **Swagger UI** — the interactive API documentation generated by FastAPI. Three endpoints are listed:

| Endpoint | What it does |
|---|---|
| `GET /health` | Liveness probe — the process is running |
| `GET /health/db` | Readiness probe — the database is reachable |
| `GET /api/quizzes` | **The walking skeleton** — lists visible quizzes for a student |

### Exercise the walking skeleton from the browser

1. Click **`GET /api/quizzes`** to expand it.
2. Click **Try it out**.
3. Leave the `email` field as `minhhd@univ.edu`.
4. Click **Execute**.

The **Response body** panel shows JSON with **6 quizzes**, sourced from PostgreSQL:

```json
{
  "student_email": "minhhd@univ.edu",
  "count": 6,
  "quizzes": [
    {"quiz_id": 2, "title": "ACC101 Weekly Quiz 1", "course_code": "ACC101", "due_at": "2026-11-01T23:59:00", "time_limit_min": 15},
    ...
  ]
}
```

The **curl** panel under it shows the equivalent command if you prefer the terminal:

```bash
curl -X 'GET' 'http://localhost:8000/api/quizzes?email=minhhd@univ.edu' -H 'accept: application/json'
```

---

## 8. Troubleshooting

**`psql: command not found`.**
PostgreSQL is not installed or not on PATH. Reinstall from step 1. On Windows, open a **new** terminal after installation.

**`could not connect to server: Connection refused` when running `db/init_db.py`.**
The PostgreSQL service is not running.

- **Windows:** *Services* → `postgresql-x64-18` → Start.
- **macOS:** `brew services start postgresql@18`
- **Linux:** `sudo systemctl start postgresql`

**`password authentication failed for user "postgres"`.**
The `DB_PASSWORD` in `.env` does not match PostgreSQL. On Linux, reset it:

```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
```

On macOS Homebrew, leave `DB_PASSWORD=` blank and set `DB_USER` to your macOS username.

**`ModuleNotFoundError: psycopg` or `ModuleNotFoundError: fastapi`.**
The virtual environment is not active, or dependencies were not installed:

```bash
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**`No visible quizzes for this student.`**
The seed ran, but the query's `q.due_at > NOW()` filter excludes every quiz. Your clock is past `2026-12-14`. Either adjust the dates in `db/seed.sql` and re-run `python db/init_db.py`, or set your machine's date earlier.

**`Address already in use: port 8000`.**
Another process uses port 8000. Stop it, or edit `src/app.py` and change `port=8000` to `port=8001`, then visit `http://localhost:8001/docs`.

**Browser shows `ERR_ADDRESS_INVALID` for `http://0.0.0.0:8000/`.**
`0.0.0.0` is a bind address, not a hostname. Use `http://localhost:8000/docs` instead.

---

## 9. Tested by

| Tester | Machine | Date | Time |
|---|---|---|---|
| *(to be filled in by the reviewer)* | | | |

---

## 10. What is in the repository

```
root/
├── db/
│   ├── schema.sql        
│   ├── seed.sql         
│   ├── init_db.py       
│   └── verify_db.py      
├── src/
│   ├── app.py            
│   ├── config/
│   │   ├── settings.py  
│   │   └── db.py        
│   ├── models/
│   │   └── quiz.py      
│   ├── repositories/
│   │   └── quiz_repository.py
│   ├── routes/
│   │   ├── health_routes.py
│   │   └── quiz_routes.py
│   ├── services/
│   │   └── quiz_service.py  
│   └── utils/
├── tests/
│   └── test_example.py
├── docs/
│   ├── design.md       
│   ├── SETUP.md       
│   ├── diagrams/       
│   └── images/     
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```