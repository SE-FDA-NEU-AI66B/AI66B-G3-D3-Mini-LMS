# Requirements Document

## 1. Product vision

For students and lecturers at a Vietnamese university who today rely on paper quizzes or spreadsheet-based manual grading, **Mini-LMS** removes the multi-day grading bottleneck and the absence of immediate, per-question feedback by providing a lightweight web platform for quiz authoring, timed delivery, automatic grading, and class-level analytics — unlike generic LMS suites, it is scoped to a single course workflow so it can be deployed and understood within minutes.

## 2. Personas



## 3. Scenarios



## 4. User stories



## 5. Business rules



## 6. Screens and flow

**Access legend:** **G** = Guest (not signed in) · **U** = authenticated student · **A** = authenticated instructor.

| Route | Purpose | Access | Priority |
|-------|---------|--------|----------|
| `/` | Landing page | G | P0 |
| `/login` | Login | G | P0 |
| `/dashboard` | Student's list of available quizzes | U | P0 |
| `/quiz/{id}/take` | Take a quiz with countdown timer | U | P0 |
| `/quiz/{id}/result?attempt={n}` | The result of the attempted quiz | U | P0 |
| `/results` | Student's past attempts | U | P2 |
| `/instructor/quizzes` | Lecturer's quiz list; create, publish, unpublish | A | P1 |
| `/instructor/quizzes/{id}/edit` | Modify a quiz's contents, like questions or timer | A | P0 |
| `/instructor/stats/{id}` | Quiz statistics: average, distribution, per-question difficulty | A | P1 |
| `/instructor/accounts` | Create, edit, and disable student accounts | A | P1 |

### Flow diagram

![Flow diagram](./images/flow.jpg)