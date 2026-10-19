"""
attempt_service.py — student attempt business logic (US03).

Enforced here:
  * BR1 — one active attempt per (student, quiz); resume instead of restarting.
  * BR3 — auto-submit at 00:00; server flags the row regardless of what
          the client claimed.
  * BR4 — MCQ exact match; SHORT case-insensitive + trimmed.
  * BR5 — percentage rounded to 2 decimals.
  * BR6 — quiz must be Published, due date future, student enrolled.
  * BR10 — tab_switch_count is recorded; > 3 flags the attempt.
"""

from __future__ import annotations

import json

from src.config import db as db_config
from src.models.attempt import (
    AttemptQuestion,
    AttemptQuestionOption,
    AttemptResult,
    AttemptState,
    SavedAnswer,
    SaveAnswerRequest,
    SubmitRequest,
    SubmitResponse,
    TabSwitchResponse,
)
from src.repositories import attempt_repository as repo


# ----------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------

class AttemptServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnauthorizedError(AttemptServiceError):
    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, 401)


class ForbiddenError(AttemptServiceError):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message, 403)


class NotFoundError(AttemptServiceError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, 404)


class ConflictError(AttemptServiceError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, 409)


class ValidationError(AttemptServiceError):
    def __init__(self, message: str = "Invalid input") -> None:
        super().__init__(message, 422)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _require_student(conn, email: str) -> int:
    if not email or "@" not in email:
        raise UnauthorizedError()
    row = repo.get_user_role_status(conn, email)
    if row is None:
        raise UnauthorizedError(f"Unknown account: {email!r}")
    user_id, role, status = row
    if status != "Active":
        raise ForbiddenError("Account is disabled")
    if role != "Student":
        raise ForbiddenError("Only students may take quizzes")
    return user_id


def _parse_accepted_answers(raw: str | None) -> list[str]:
    """Support both JSON list (new rows) and plain string (seeded rows)."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return [raw]
    if isinstance(parsed, list):
        return [str(x) for x in parsed]
    return [str(parsed)]


def _check_short_answer(user_text: str | None, accepted_raw: str | None) -> bool:
    if not user_text or not user_text.strip():
        return False
    user_norm = user_text.strip().lower()
    for acc in _parse_accepted_answers(accepted_raw):
        if acc.strip().lower() == user_norm:
            return True
    return False


def _build_attempt_state(
    conn, attempt_id: int, request_user_id: int
) -> AttemptState:
    row = repo.get_attempt_full(conn, attempt_id)
    if row is None:
        raise NotFoundError(f"Attempt {attempt_id} not found")

    (aid, quiz_id, student_id, started_at, submitted_at, _auto,
     _score, _total, tab_count, title, code, time_limit, elapsed,
     _answers_released) = row

    if student_id != request_user_id:
        raise ForbiddenError("This attempt belongs to another user")

    remaining = max(0, time_limit * 60 - elapsed)

    questions: list[AttemptQuestion] = []
    for qid, pos, qtype, prompt, points in repo.list_questions_for_attempt(conn, quiz_id):
        options: list[AttemptQuestionOption] = []
        if qtype == "MCQ":
            for oid, label, text in repo.list_options_for_attempt(conn, qid):
                options.append(AttemptQuestionOption(
                    option_id=oid, label=label, text=text))
        questions.append(AttemptQuestion(
            question_id=qid, position=pos, question_type=qtype,
            prompt=prompt, points=points, options=options,
        ))

    saved = [
        SavedAnswer(question_id=qid, chosen_option_id=cid, text_answer=txt)
        for qid, cid, txt in repo.list_answers_for_attempt(conn, attempt_id)
    ]

    return AttemptState(
        attempt_id=aid,
        quiz_id=quiz_id,
        quiz_title=title,
        course_code=code,
        time_limit_min=time_limit,
        started_at=started_at,
        submitted_at=submitted_at,
        remaining_seconds=remaining,
        tab_switch_count=tab_count,
        flagged=tab_count > 3,
        questions=questions,
        saved_answers=saved,
    )


def _percentage(score: int, total: int) -> float:
    return round((score / total * 100.0) if total else 0.0, 2)


# ----------------------------------------------------------------------
# Public functions
# ----------------------------------------------------------------------

def start_attempt(student_email: str, quiz_id: int) -> AttemptState:
    with db_config.connect() as conn:
        student_id = _require_student(conn, student_email)

        header = repo.get_quiz_header(conn, quiz_id)
        if header is None:
            raise NotFoundError(f"Quiz {quiz_id} not found")
        (_qid, course_id, _code, _title, _limit, _due, status,
         _ar, _takeable) = header

        # BR1: resume if an active attempt exists — regardless of the quiz
        # state now (they were mid-attempt when it went Unpublished).
        existing_id = repo.get_active_attempt_id(conn, student_id, quiz_id)
        if existing_id is not None:
            return _build_attempt_state(conn, existing_id, student_id)

        # No active attempt — new attempts require Published + future due.
        if status != "Published":
            raise ConflictError("Quiz is not published")
        # is_takeable already encodes (Published AND due_at > NOW()),
        # but we already checked status explicitly for a clearer message.
        # Re-check due date here:
        if not _takeable:  # type: ignore[misc]
            raise ConflictError("Quiz due date has passed")

        if not repo.is_active_enrolled(conn, student_id, course_id):
            raise ForbiddenError("You are not enrolled in this course")

        if not repo.list_questions_for_attempt(conn, quiz_id):
            raise ConflictError("Quiz has no questions")

        attempt_id = repo.insert_attempt(conn, quiz_id, student_id)
        return _build_attempt_state(conn, attempt_id, student_id)


def get_attempt(student_email: str, attempt_id: int) -> AttemptState:
    with db_config.connect() as conn:
        student_id = _require_student(conn, student_email)
        row = repo.get_attempt_full(conn, attempt_id)
        if row is None:
            raise NotFoundError(f"Attempt {attempt_id} not found")
        if row[2] != student_id:
            raise ForbiddenError("This attempt belongs to another user")
        if row[4] is not None:
            raise ConflictError("This attempt is already submitted")
        return _build_attempt_state(conn, attempt_id, student_id)


def save_answer(
    student_email: str, attempt_id: int, question_id: int,
    payload: SaveAnswerRequest,
):
    with db_config.connect() as conn:
        student_id = _require_student(conn, student_email)
        row = repo.get_attempt_full(conn, attempt_id)
        if row is None:
            raise NotFoundError(f"Attempt {attempt_id} not found")
        if row[2] != student_id:
            raise ForbiddenError("This attempt belongs to another user")
        if row[4] is not None:
            raise ConflictError("Attempt already submitted")

        quiz_id = row[1]
        time_limit = row[11]
        elapsed = row[12]
        if elapsed >= time_limit * 60:
            raise ConflictError("Time has expired. Submitting now.")

        question = repo.get_question_in_quiz(conn, question_id, quiz_id)
        if question is None:
            raise NotFoundError(f"Question {question_id} not found in this quiz")
        qtype = question[3]

        if qtype == "MCQ":
            if payload.chosen_option_id is None:
                raise ValidationError("MCQ requires chosen_option_id")
            if payload.text_answer is not None:
                raise ValidationError("MCQ answer must not include text_answer")
            if repo.get_option_in_question(
                conn, payload.chosen_option_id, question_id
            ) is None:
                raise ValidationError("Option does not belong to this question")
            repo.upsert_answer(
                conn, attempt_id, question_id, payload.chosen_option_id, None
            )
        else:  # SHORT
            if payload.chosen_option_id is not None:
                raise ValidationError(
                    "SHORT answer must not include chosen_option_id")
            if payload.text_answer is None:
                raise ValidationError("SHORT requires text_answer")
            repo.upsert_answer(
                conn, attempt_id, question_id, None, payload.text_answer
            )
        return {"ok": True}


def record_tab_switch(student_email: str, attempt_id: int) -> TabSwitchResponse:
    with db_config.connect() as conn:
        student_id = _require_student(conn, student_email)
        row = repo.get_attempt_full(conn, attempt_id)
        if row is None:
            raise NotFoundError(f"Attempt {attempt_id} not found")
        if row[2] != student_id:
            raise ForbiddenError("This attempt belongs to another user")
        if row[4] is not None:
            raise ConflictError("Attempt already submitted")

        count = repo.increment_tab_switch(conn, attempt_id)
        return TabSwitchResponse(tab_switch_count=count, flagged=count > 3)


def submit_attempt(
    student_email: str, attempt_id: int, payload: SubmitRequest,
) -> SubmitResponse:
    with db_config.connect() as conn:
        student_id = _require_student(conn, student_email)
        row = repo.get_attempt_full(conn, attempt_id)
        if row is None:
            raise NotFoundError(f"Attempt {attempt_id} not found")
        if row[2] != student_id:
            raise ForbiddenError("This attempt belongs to another user")
        if row[4] is not None:
            raise ConflictError("Attempt already submitted")

        quiz_id = row[1]
        time_limit = row[11]
        elapsed = row[12]
        timed_out = elapsed >= time_limit * 60
        auto_submitted = bool(payload.auto_submitted) or timed_out

        questions = repo.list_questions_for_attempt(conn, quiz_id)
        grading_data = repo.get_grading_data(conn, quiz_id)
        correct_map = repo.get_correct_option_map(conn, quiz_id)
        answer_id_map = repo.get_answer_id_map(conn, attempt_id)
        answers = {
            qid: (cid, txt)
            for qid, cid, txt in repo.list_answers_for_attempt(conn, attempt_id)
        }

        score = 0
        total = len(questions)
        for qid, _pos, qtype, _prompt, points in questions:
            if qid not in answers:
                continue  # unanswered = 0
            cid, txt = answers[qid]
            if qtype == "MCQ":
                is_correct = cid is not None and correct_map.get(qid) == cid
            else:
                _qt, raw = grading_data.get(qid, (qtype, None))
                is_correct = _check_short_answer(txt, raw)
            if is_correct:
                score += points
            aid = answer_id_map.get(qid)
            if aid is not None:
                repo.update_answer_correctness(conn, aid, is_correct)

        repo.finalize_attempt(conn, attempt_id, score, total, auto_submitted)

        return SubmitResponse(
            attempt_id=attempt_id,
            score=score,
            total=total,
            percentage=_percentage(score, total),
            auto_submitted=auto_submitted,
        )


def get_result(student_email: str, attempt_id: int) -> AttemptResult:
    with db_config.connect() as conn:
        student_id = _require_student(conn, student_email)
        row = repo.get_attempt_result_row(conn, attempt_id)
        if row is None:
            raise NotFoundError(f"Attempt {attempt_id} not found")

        full = repo.get_attempt_full(conn, attempt_id)
        if full is None or full[2] != student_id:
            raise ForbiddenError("This attempt belongs to another user")
        if row[7] is None:  # submitted_at
            raise ConflictError("Attempt not yet submitted")

        score = row[4] if row[4] is not None else 0
        total = row[5] if row[5] is not None else 0
        return AttemptResult(
            attempt_id=row[0],
            quiz_id=row[1],
            quiz_title=row[2],
            course_code=row[3],
            score=score,
            total=total,
            percentage=_percentage(score, total),
            auto_submitted=row[6],
            submitted_at=row[7],
            answers_released=row[8],
        )