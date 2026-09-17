# Traceability

Every screen traces back to a feature and forward to the issue that built it.
This table is the single source of truth for Milestone 1 section 6 and for the
Milestone 4 report. Keep it current - a PR that adds a route and does not
update this file should not be approved.

| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
|-------|---------|--------|----------|---------|-------------|-----|--------|
| `/` | Landing page | G | P0 | - | #- | - | Not Started |
| `/login` | Login | G | P0 | - | #- | - | Not Started |
| `/dashboard` | Student's list of available quizzes | U | P0 | - | #- | - | Not Started |
| `/quiz/{id}/take` | Take a quiz with countdown timer | U | P0 | - | #- | - | Not Started |
| `/quiz/{id}/result?attempt={n}` | The result of the attempted quiz | U | P0 | - | #- | - | Not Started |
| `/results` | Student's past attempts | U | P2 | - | #- | - | Not Started |
| `/instructor/quizzes` | Lecturer's quiz list; create, publish, unpublish | A | P1 | - | #- | - | Not Started |
| `/instructor/quizzes/{id}/edit` | Modify a quiz's contents, like questions or timer | A | P0 | - | #- | - | Not Started |
| `/instructor/stats/{id}` | Quiz statistics: average, distribution, per-question difficulty | A | P1 | - | #- | - | Not Started |
| `/instructor/accounts` | Create, edit, and disable student accounts | A | P1 | - | #- | - | Not Started |

**Access codes:** G = guest (not logged in) · U = authenticated user · A = admin

**Status:** Not started / In progress / Done

## Business rules

Numbered, so issues and tests can cite them.

| # | Rule | Enforced where | Tested by |
|---|------|----------------|-----------|
| BR1 | | | |
| BR2 | | | |
| BR3 | | | |
| BR4 | | | |
| BR5 | | | |
| BR6 | | | |