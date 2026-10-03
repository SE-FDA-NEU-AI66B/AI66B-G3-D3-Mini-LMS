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

---

## 3. API design



## 4. Walking skeleton



## 5. Design decisions



## 6. What changed since M1

