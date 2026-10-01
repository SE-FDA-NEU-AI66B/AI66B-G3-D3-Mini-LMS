# Requirements Document — Mini-LMS

## 1. Product vision

For students and lecturers at a Vietnamese university who today rely on paper quizzes or spreadsheet-based manual grading, **Mini-LMS** removes the multi-day grading bottleneck by providing a lightweight web platform where **lecturers create quizzes**, **students take them under a timer**, and **both see results immediately**. An **administrative staff** maintains the roster of who teaches and who is enrolled in each course so the quiz workflow keeps working — nothing else. Unlike generic LMS suites, Mini-LMS does quizzes only, and is small enough to deploy and understand in minutes.

## 2. Personas

### Persona 1 — Ha Duc Minh, the student

- **Role:** 20-year-old second-year undergraduate at a Vietnamese university, taking 4 courses this semester.
- **Goal:** keep track of upcoming quizzes in one place, and get his score immediately after submitting so he knows whether he is ready for the final exam.
- **What blocks him:** quizzes are announced verbally in class or scattered across group chats with no central list; results come back days or weeks later after manual grading; he cannot see which topics he is weak on.
- **In his words:** *"I just want to know my score now, not next week."*
- **Technical skill:** comfortable with both phone and laptop; uses the university portal, Google Classroom, and Zalo daily. Signs in through the university SSO without creating a new password.
- **Interview note:** interviewed on 10-09-2026 for 30 minutes, in person.

### Persona 2 — Dr. Pham Thi Lan, the lecturer

- **Role:** 45-year-old lecturer at a Vietnamese university, teaching 3 courses with roughly 120 students in total.
- **Goal:** assess students frequently without spending hours grading, and identify which topics the class is struggling with. She manages quizzes inside the courses assigned to her — nothing else.
- **What blocks her:** grading MCQ and short-answer quizzes by hand in Excel takes 4–6 hours per quiz; she has no reliable way to see per-question difficulty. In the past she also had to chase the administrative office for account lists and course codes — that is not her job and should not be.
- **In her words:** *"I stopped giving weekly quizzes because grading them ate my weekends."*
- **Technical skill:** confident with Excel and the university's existing LMS; not a programmer. Signs in through the university SSO.
- **Interview note:** interviewed on 12-09-2026 for 25 minutes, online call.

### Persona 3 — Nguyen Thi Mai, the administrative staff

- **Role:** 35-year-old staff member of the Educational Management Department. Her job inside Mini-LMS is narrow: keep the **lecturer ↔ course ↔ student** roster correct so the quiz workflow works.
- **Goal:** when a lecturer is assigned to a course, or a student drops it, the change is made once and the quiz system immediately respects it.
- **What blocks her:** today this lives in Excel files and email threads. A lecturer cannot create quizzes for a course until the roster says they own it; a student cannot take quizzes for a course they are no longer in — but nobody has a single source of truth.
- **In her words:** *"I only need two things: put the right lecturer on each course, and put the right students in it. The rest is the lecturer's job."*
- **Technical skill:** office software only; not a programmer. Signs in via the university SSO.
- **Interview note:** formalised after the review discussion on 28-09-2026, where the reviewer argued that lecturers should not be doing account or course setup.

## 3. Scenarios

### Scenario 1 — Dr. Lan prepares and reviews a weekly quiz

1. On Monday evening Dr. Lan decides to assess her *Introduction to Accounting* class on the week's material.
2. She opens the platform on her laptop and signs in through the university SSO.
3. She opens her course `"ACC101"` — already assigned to her by the administrative office — and creates a new quiz inside it, setting a title, a 30-minute time limit, and a due date of Friday 23:59.
4. She adds 10 questions — 7 multiple-choice and 3 short-answer — each with a correct answer.
5. She saves the quiz as a draft and reads through it once more.
6. She publishes the quiz, and it becomes visible to all 120 enrolled students.
7. On Friday night she checks the class statistics and sees that Question 4 was answered correctly by only 25% of students.
8. The following Monday she spends 10 minutes reviewing Question 4 in class instead of spending the weekend grading.

### Scenario 2 — Minh takes a quiz and reviews his result

1. On Thursday evening Minh is in his dormitory and remembers a quiz is due Friday night.
2. He opens the platform on his laptop and signs in through the university SSO.
3. He sees the quiz listed with a 30-minute limit and the Friday due date.
4. He starts the quiz and answers the multiple-choice and short-answer questions one at a time.
5. Halfway through, his phone rings; he briefly switches tabs but returns within the time limit.
6. At 28 minutes he submits; the timer still shows 02:00.
7. He immediately sees his raw score and percentage.
8. Two days later, after Dr. Lan releases the answers, he reviews exactly which questions he got wrong.

### Scenario 3 — Mai assigns a lecturer to a course

1. Mai signs in through the university SSO.
2. She creates a course `"ACC101 — Introduction to Accounting"`.
3. She assigns Dr. Pham Thi Lan as the lecturer for that course.
4. Dr. Lan opens the platform the next day and sees `"ACC101"` ready for her to create quizzes.

## 4. User stories

**Summary table**

| ID | Story | Priority | Points |
|---|---|---|---|
| US01 | Lecturer creates a quiz (MCQ + short answer) | P0 | 8 |
| US02 | Student sees available quizzes | P0 | 3 |
| US03 | Student takes a quiz with countdown timer | P0 | 5 |
| US04 | Automatic grading + immediate score | P0 | 5 |
| US05 | Lecturer publishes / unpublishes a quiz | P0 | 3 |
| US06 | Admin manages user accounts | P0 | 5 |
| US07 | Student views past attempts | P1 | 3 |
| US08 | Lecturer sees class statistics | P1 | 5 |
| US09 | Lecturer sees per-question difficulty | P1 | 5 |
| US10 | Student reviews answers after release | P2 | 3 |
| US11 | Admin creates courses and assigns lecturers | P0 | 5 |
| US12 | Admin enrolls students into a course | P0 | 3 |

### US01 — Lecturer creates a quiz · P0 · 8 points · Screen: `/instructor/quizzes/{id}/edit`

> As a **lecturer**, I want to **create a quiz with multiple-choice and short-answer questions** so that **I can assess my class online**.

**Acceptance criteria**
- Given the lecturer enters the title `"Midterm Quiz"`, a time limit of `"30 minutes"`, and a due date of `"2026-10-10 23:59"`, When the lecturer saves, Then the quiz is created with status `Draft`.
- Given the lecturer adds a question `"What is 2+2?"` with options `3, 4, 5, 6` and marks `4` as correct, When the lecturer saves, Then the question appears with exactly **4** options and exactly **1** marked correct.
- Given the title field is empty, When the lecturer saves, Then the system shows `"Title is required"` and the quiz is not saved.

**Tasks**
- Quiz form UI (title, time limit, due date) — @Altimary
- Question editor for MCQ + short-answer — @BuiDut
- Persist quiz, questions, and accepted answers — @thangkaka26
- Validation tests (empty title, no correct option, out-of-range limit) — @VizAnh

### US02 — Student sees available quizzes · P0 · 3 points · Screen: `/dashboard`

> As a **student**, I want to **see the quizzes available to me with their due dates and time limits** so that **I know what to take and by when**.

**Acceptance criteria**
- Given Minh has signed in via the university SSO and is enrolled in **2** courses with **3** published quizzes, When Minh opens his dashboard, Then all **3** quizzes appear with title, due date, and time limit.
- Given quiz `"Midterm Quiz"` is due on `"2026-10-10 23:59"` and has a **30-minute** limit, When the list is shown, Then the row displays exactly `"2026-10-10 23:59"` and `"30 min"`.
- Given Minh is not enrolled in a course, When he opens his dashboard, Then no quiz from that course appears in the list.

**Tasks**
- Availability query (Published + before due date + enrolled) — @thangkaka26
- Dashboard quiz list UI — @Altimary
- Visibility tests (draft hidden, due-date, not-enrolled) — @VizAnh

### US03 — Student takes a quiz with countdown timer · P0 · 5 points · Screen: `/quiz/{id}/take`

> As a **student**, I want to **take a quiz with a visible countdown timer** so that **I can manage my time and submit within the limit**.

**Acceptance criteria**
- Given a quiz has **10** questions and a **30-minute** limit, When Minh starts the quiz, Then the timer displays `"30:00"` and counts down every second.
- Given the timer reaches `"00:00"`, When time expires, Then the quiz auto-submits and Minh sees `"Time is up."`
- Given Minh has answered **4** of **10** questions, When he clicks Submit, Then the system asks for confirmation before submitting.

**Tasks**
- Quiz-taking UI (one question at a time) — @Altimary
- Countdown timer + auto-submit at `00:00` — @VizAnh
- Per-question answer persistence (resume support) — @thangkaka26
- Timer, auto-submit, and resume tests — @BuiDut

### US04 — Automatic grading and immediate score · P0 · 5 points · Screen: `/quiz/{id}/result?attempt={n}`

> As a **student**, I want **my quiz to be graded automatically the moment I submit** so that **I get my score without waiting**.

**Acceptance criteria**
- Given a quiz has **10** questions and Minh answers **8** correctly, When Minh submits, Then the system shows raw score `"8/10"` and percentage `"80.00%"`.
- Given Minh submits, When grading finishes, Then the result appears within **2 seconds**.
- Given Minh's short-answer is `"  Hà Nội "` with surrounding whitespace, and the accepted answer is `"Hà Nội"`, When grading runs, Then it is marked correct.

**Tasks**
- MCQ grader (exact match against marked option) — @Altimary
- Short-answer normalizer (case-insensitive, whitespace-trimmed) — @BuiDut
- Score + percentage renderer (2 decimal places) — @VizAnh
- Grading unit tests (case, whitespace, wrong answer) — @thangkaka26

### US05 — Lecturer publishes / unpublishes a quiz · P0 · 3 points · Screen: `/instructor/quizzes`

> As a **lecturer**, I want to **publish or unpublish a quiz** so that **I control exactly when students can access it**.

**Acceptance criteria**
- Given a `Draft` quiz, When Dr. Lan clicks Publish, Then the status changes to `Published` and the quiz appears in Minh's dashboard.
- Given a `Published` quiz with **5** existing student attempts, When Dr. Lan unpublishes it, Then students can no longer start new attempts, but the **5** existing attempts remain accessible.

**Tasks**
- Publish / unpublish endpoint — @thangkaka26
- Status badge and toggle UI — @Altimary
- Tests for the "existing attempts preserved" rule — @BuiDut

### US06 — Admin manages user accounts · P0 · 5 points · Screen: `/admin/accounts`

> As an **admin**, I want to **create and disable student and lecturer accounts** so that **only authorized people can reach the quizzes**.

**Acceptance criteria**
- Given the admin enters email `"sinhvien01@univ.edu"` with role `Student`, When the admin saves, Then the account is created and the student can sign in via the university SSO.
- Given a student account is `Disabled`, When the student tries to sign in, Then the system shows `"Account is disabled"` and denies access.
- Given a lecturer account is `Disabled`, When that lecturer tries to sign in, Then access is denied; their existing quizzes remain stored for the admin to reassign or archive.

**Tasks**
- Account create / disable API — @thangkaka26
- Accounts management UI (student + lecturer lists) — @Altimary
- Role-based access tests — @BuiDut

### US07 — Student views past attempts · P1 · 3 points · Screen: `/results`

> As a **student**, I want to **see my past quiz attempts and scores** so that **I can track my progress over the semester**.

**Acceptance criteria**
- Given Minh has completed **4** quizzes, When he opens `My Results`, Then **4** rows appear with quiz title, date, and score.
- Given Minh scored **8/10** on `"Midterm Quiz"`, When the row is shown, Then it displays `"8/10"` and `"80.00%"`.

**Tasks**
- Attempt history query (grouped by quiz) — @BuiDut
- Results list UI — @Altimary
- Formatting and empty-state tests — @thangkaka26

### US08 — Lecturer sees class statistics · P1 · 5 points · Screen: `/instructor/stats/{quizId}`

> As a **lecturer**, I want to **see class statistics — average score and score distribution** so that **I can judge how the class performed overall**.

**Acceptance criteria**
- Given **20** students submitted `"Midterm Quiz"`, When Dr. Lan opens Statistics, Then the average score is displayed as `"7.25/10"`.
- Given the submitted scores are `5, 6, 7, 8, 9, 10`, When the distribution chart is shown, Then it displays counts for each score value from **0 to 10**.

**Tasks**
- Aggregation query (average, min, max, count) — @BuiDut
- Distribution chart component — @Altimary
- Average-formatting test (2 decimal places) — @VizAnh

### US09 — Lecturer sees per-question difficulty · P1 · 5 points · Screen: `/instructor/stats/{quizId}`

> As a **lecturer**, I want to **see per-question difficulty as a percentage of correct answers** so that **I can identify which questions were too hard**.

**Acceptance criteria**
- Given **20** students answered Question 1 and **5** answered correctly, When Dr. Lan opens Difficulty Analysis, Then Question 1 shows `"25.00% correct"`.
- Given a question was answered correctly by **18** of **20** students, When the analysis is displayed, Then it shows `"90.00% correct"`.

**Tasks**
- Per-question correctness aggregation — @thangkaka26
- Difficulty table UI — @Altimary
- Edge-case tests (0 answers, 100% correct) — @BuiDut

### US10 — Student reviews answers after release · P2 · 3 points · Screen: `/results`

> As a **student**, I want to **review my answers against the correct answers after the lecturer releases them** so that **I can learn from my mistakes**.

**Acceptance criteria**
- Given Dr. Lan has released answers for `"Midterm Quiz"`, When Minh opens his attempt, Then each question shows his answer, the correct answer, and whether it was correct.
- Given Dr. Lan has **not** released answers, When Minh opens his attempt, Then only the total score is shown and no per-question detail appears.

**Tasks**
- Answer-release flag on quiz — @BuiDut
- Per-question review view — @Altimary
- Access-gating tests (before / after release) — @thangkaka26

### US11 — Admin creates courses and assigns lecturers · P0 · 5 points · Screen: `/admin/courses`

> As an **admin**, I want to **create a course and assign exactly one lecturer to it** so that **the lecturer can create quizzes for that course**.

**Acceptance criteria**
- Given the admin enters course code `"ACC101"` and name `"Introduction to Accounting"`, When the admin saves, Then the course is created and appears in the course list.
- Given course `"ACC101"` exists with no lecturer, When the admin assigns lecturer `"lanpt@univ.edu"`, Then Dr. Lan sees `"ACC101"` on her instructor dashboard and can create quizzes for it.
- Given course `"ACC101"` has Dr. Lan assigned, When the admin tries to remove her without assigning a replacement, Then the system shows `"Assign another lecturer first"` and blocks the removal (BR9).

**Tasks**
- Course create + assign-lecturer API — @thangkaka26
- Course management UI — @Altimary
- Last-lecturer guard tests — @VizAnh

### US12 — Admin enrolls students into a course · P0 · 3 points · Screen: `/admin/courses/{id}/students`

> As an **admin**, I want to **add or remove students from a course** so that **only enrolled students can take that course's quizzes**.

**Acceptance criteria**
- Given course `"ACC101"` has **120** enrolled students, When the admin adds student `"minhhd@univ.edu"`, Then the student count becomes **121** and Minh can see `"ACC101"` quizzes on his dashboard.
- Given student `"minhhd@univ.edu"` is enrolled in `"ACC101"`, When the admin removes him, Then the student count decreases by **1** and the quizzes for `"ACC101"` no longer appear on his dashboard.

**Tasks**
- Enrollment API (add/remove) — @BuiDut
- Enrollment UI — @Altimary
- Access-control tests (enrolled vs not enrolled) — @thangkaka26

## 5. Business rules

| ID | Rule | Worked example |
|---|---|---|
| **BR1** | A student may have at most **1** active (in-progress) attempt per quiz at a time. | Minh started `"Midterm Quiz"` at 19:00. At 19:10 he opens the same quiz in another tab → the system resumes the existing attempt instead of creating a second one. |
| **BR2** | A quiz's time limit must be between **5 minutes** and **120 minutes** inclusive. | `5 min` accepted. `120 min` accepted. `4 min` rejected. `121 min` rejected. |
| **BR3** | A quiz auto-submits when the timer reaches **00:00**. | Minh starts a 30-minute quiz at 19:00. At 19:30 the timer reaches `00:00` → the quiz auto-submits with whatever answers were saved. |
| **BR4** | Each question is worth **1 point**, no partial credit. MCQ is graded by exact match against the marked correct option. Short-answer is graded by case-insensitive, whitespace-trimmed match against one of the lecturer's accepted answers. | A 10-question quiz has max score **10**. MCQ Q1 correct = `"B"`; Minh picks `"B"` → **1** point, picks `"C"` → **0**. Short-answer Q2 accepted = `"Hà Nội"`; Minh writes `"  hà nội "` → **1** point; he writes `"Hanoi"` → **0** points. |
| **BR5** | Score is displayed as raw score out of total **and** percentage rounded to **2 decimal places**. | **8** correct out of **10** → `"8/10"` and `"80.00%"`. **7** correct out of **9** → `"7/9"` and `"77.78%"`. |
| **BR6** | A quiz is visible to a student only when its status is `Published`, the current time is before its due date, **and** the student is enrolled in the owning course. | Quiz due `2026-10-10 23:59`, status `Published`, course `"ACC101"` → visible to Minh on `2026-10-10 22:00` because he is enrolled. Same quiz on `2026-10-11 00:01` → not visible. |
| **BR7** | Authentication is delegated to the **university SSO**. Mini-LMS never stores passwords; it stores only the SSO-returned identity and the local role (`Student` / `Lecturer` / `Admin`). | Minh signs in via SSO with `minhhd@univ.edu`. Mini-LMS receives a verified identity, looks up the local role, and routes him to `/dashboard`. Dr. Lan signs in via the same SSO and is routed to `/instructor/quizzes`. |
| **BR8** | Role-based access: **Student** sees quizzes + own results; **Lecturer** sees quizzes, statistics, and a read-only monitoring view of students in their own courses (roster + per-student status); **Admin** manages accounts, courses, and enrollment only. No role can reach another role's area. | Dr. Lan is assigned to `"ACC101"` but not `"ACC102"`. She opens `"ACC102"`'s roster → `"Access denied"`. She can view `"ACC101"`'s roster but cannot add or remove students there — only the Admin can (US12). |
| **BR9** | A course must have **exactly 1 assigned lecturer** at a time. Removing the current lecturer without a replacement is blocked. | `"ACC101"` has Dr. Lan. Admin tries to remove her → `"Assign another lecturer first"`. After assigning `"tuanvm@univ.edu"` and confirming the swap, the admin can remove Dr. Lan. |
| **BR10** | Every quiz attempt records tab-switch events (browser visibility change / window blur). If a student leaves the quiz tab **more than 3 times** during a single attempt, the attempt is **flagged**. The student's score is graded normally — the flag appears **only** in the lecturer's monitoring view as a warning icon in that student's row. | Minh's 30-minute attempt records tab-switches at 5:00, 12:10, 18:30, and 25:00 → **4** switches → flagged. His score is graded normally (e.g., `8/10`), and Dr. Lan sees a ⚠ icon next to his name. A student with **3** switches is **not** flagged. |

## 6. Screens and flow

**Access legend:** **G** = Guest (not signed in) · **U** = authenticated student · **A** = authenticated lecturer · **AD** = authenticated admin. All sign-in is via the university SSO (BR7).

| Route | Purpose | Access | Priority |
|-------|---------|--------|----------|
| `/` | Landing page | G | P0 |
| `/login` | Redirect to university SSO | G | P0 |
| `/dashboard` | Student's list of available quizzes | U | P0 |
| `/quiz/{id}/take` | Take a quiz with countdown timer | U | P0 |
| `/quiz/{id}/result?attempt={n}` | The result of the attempted quiz | U | P0 |
| `/results` | Student's past attempts | U | P2 |
| `/instructor/quizzes` | Lecturer's quiz list; create, publish, unpublish | A | P1 |
| `/instructor/quizzes/{id}/edit` | Modify a quiz's contents, like questions or timer | A | P0 |
| `/instructor/quizzes/{id}/students` | Lecturer's read-only monitoring view of a published quiz: roster with per-student status (attempted / not attempted), score, and ⚠ cheat-warning icon (BR10). Default view when the lecturer clicks a published quiz. | A | P1 |
| `/instructor/stats/{id}` | Quiz statistics: average, distribution, per-question difficulty | A | P1 |
| `/admin/courses` | Admin creates courses and assigns one lecturer per course | AD | P0 |
| `/admin/courses/{id}/students` | Admin adds or removes students from a course | AD | P0 |
| `/admin/accounts` | Admin creates or disables user accounts | AD | P0 |

### Flow diagram

![Flow diagram — screen access by role](./images/flow.png)