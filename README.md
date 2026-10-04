# D3 - Educational Platform (Mini LMS)

Instructors create quizzes, students take them, and the system automatically grades the submissions and compiles class results.

## Team
**AI66B - Group 3**:

| Name | GitHub username | Role |
| --- | --- | --- |
| Nguyen Dinh Thang | @thangkaka26 | Leader |
| Bui Tuan Anh | @BuiDut | Member |
| Nguyen Viet Anh | @VizAnh | Member |
| Pham Le Minh Nhat | @Altimary | member |

**Product Owner** (fixed all term): **@thangkaka26**  
|Scrum Master||
|---|---|
|Sprint 1| @thangkaka26 |
|Sprint 2| @Altimary |
|Sprint 3| @BuiDut |
|Sprint 4| |
|Sprint 5| |

## Setup
> Quick setup guide for Windows

### Before testing:
1. The main branch is cloned: https://github.com/SE-FDA-NEU-AI66B/AI66B-G3-D3-Mini-LMS.git
2. Let the connected postgreSQL database (w/ pgAdmin) running in background.
3. Edit `.venv.example` that matches the properties of your local database.

### Sequential commands run in IDE terminal
```bash
# Run once:
python -m venv .venv
pip install -r requirements.txt
# Run when .env.example updates:
copy .env.example .env
# Run tests (terminal + browser).
python db/init_db.py
python db/verify_db.py
python src/app.py
```
### Open these URLs when server is established
→ http://127.0.0.1:8000/  
→ http://localhost:8000/  
→ http://localhost:8000/docs  
→ http://localhost:8000/api/quizzes?email=minhhd@univ.edu  
Not to open `0.0.0.0:8000` because it is the bind address, not a browsable host.

> For detail setup guides for other OSs, see in `docs\SETUP.md`.
