# Traceability

Every screen traces back to a feature and forward to the issue that built it.
This table is the single source of truth for Milestone 1 section 6 and for the
Milestone 4 report. Keep it current - a PR that adds a route and does not
update this file should not be approved.

| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
|-------|---------|--------|----------|---------|-------------|-----|--------|
| `/` | Landing page | G | P0 | F1 | #3 | #14 | Done |
| | | | | | | | |

**Access codes:** G = guest (not logged in) · U = authenticated user · A = admin

**Status:** Not started / In progress / Done

## Business rules

Numbered, so issues and tests can cite them.

| # | Rule | Enforced where | Tested by |
|---|------|----------------|-----------|
| BR1 | A student may have at most 1 active (in-progress) attempt per quiz at a time. | | |
| BR2 | A quiz's time limit must be between 5 minutes and 120 minutes inclusive. | | |
| BR3 | A quiz auto-submits when the timer reaches 00:00. | | |
| BR4 | Each question is worth 1 point, no partial credit. MCQ is graded by exact match against the marked correct option. Short-answer is graded by case-insensitive, whitespace-trimmed match against one of the lecturer's accepted answers. | | |
| BR5 | Score is displayed as raw score out of total and percentage rounded to 2 decimal places. | | |
| BR6 | A quiz is visible to a student only when its status is Published and the current time is before its due date. | | |