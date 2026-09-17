# Requirements Document

## 1. Product vision

For students and lecturers at a Vietnamese university who today rely on paper quizzes or spreadsheet-based manual grading, **Mini-LMS** removes the multi-day grading bottleneck and the absence of immediate, per-question feedback by providing a lightweight web platform for quiz authoring, timed delivery, automatic grading, and class-level analytics — unlike generic LMS suites, it is scoped to a single course workflow so it can be deployed and understood within minutes.

## 2. Personas



## 3. Scenarios



## 4. User stories



## 5. Business rules

| ID | Rule | Worked example |
|---|---|---|
| **BR1** | A student may have at most **1** active (in-progress) attempt per quiz at a time. | Minh started `"Midterm Quiz"` at 19:00. At 19:10 he opens the same quiz in another tab → the system resumes the existing attempt instead of creating a second one. |
| **BR2** | A quiz's time limit must be between **5 minutes** and **120 minutes** inclusive. | `5 min` accepted. `120 min` accepted. `4 min` rejected. `121 min` rejected. |
| **BR3** | A quiz auto-submits when the timer reaches **00:00**. | Minh starts a 30-minute quiz at 19:00. At 19:30 the timer reaches `00:00` → the quiz auto-submits with whatever answers were saved. |
| **BR4** | Each question is worth **1 point**, no partial credit. MCQ is graded by exact match against the marked correct option. Short-answer is graded by case-insensitive, whitespace-trimmed match against one of the lecturer's accepted answers. | A 10-question quiz has max score **10**. MCQ Q1 correct = `"B"`; Minh picks `"B"` → **1** point, picks `"C"` → **0**. Short-answer Q2 accepted = `"Hà Nội"`; Minh writes `"  hà nội "` → **1** point; he writes `"Hanoi"` → **0** points. |
| **BR5** | Score is displayed as raw score out of total **and** percentage rounded to **2 decimal places**. | **8** correct out of **10** → `"8/10"` and `"80.00%"`. **7** correct out of **9** → `"7/9"` and `"77.78%"`. |
| **BR6** | A quiz is visible to a student only when its status is `Published` **and** the current time is before its due date. | Quiz due `2026-10-10 23:59`, status `Published` → visible on `2026-10-10 22:00`. Same quiz on `2026-10-11 00:01` → not visible, cannot be started. |

## 6. Screens and flow



