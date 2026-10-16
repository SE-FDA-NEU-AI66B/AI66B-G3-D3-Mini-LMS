"""
instructor_quiz_service.py — business logic for lecturer quiz CRUD (US01).

This module knows nothing about HTTP. It receives plain Python arguments,
returns plain Python objects, and raises `InstructorServiceError`
subclasses whose `status_code` and `message` the route layer translates
into HTTP responses.

Business rules enforced here:
  BR2 — time_limit_min must be 5..120 inclusive.
  BR4 — MCQ exactly 4 options and exactly 1 correct.
        SHORT needs at least one non-empty accepted answer.
  BR8 — only a Lecturer may call these operations, and only for their
        own courses / quizzes.

Additional safety guards (not in the BR table but required to avoid FK
violations and mid-attempt surprises):
  * Deleting a quiz requires zero student attempts.
  * Question mutation is blocked once any attempt exists on the quiz,
    because `answer` rows point at `question` and `option` rows.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import psycopg

from src.config import db as db_config
from src.models.quiz import (
    OptionResponse,
    QuestionCreateRequest,
    QuestionResponse,
    QuestionUpdateRequest,
    QuizCreateRequest,
    QuizDetail,
    QuizSummary,
    QuizUpdateRequest,
)
from src.repositories import instructor_quiz_repository as repo


# ----------------------------------------------------------------------
# Errors — the route layer maps status_code + message to HTTP
# ----------------------------------------------------------------------

class InstructorServiceError(Exception):
    """Base class for every error the instructor service can raise."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnauthorizedError(InstructorServiceError):
    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message, 401)


class ForbiddenError(InstructorServiceError):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message, 403)


class NotFoundError(InstructorServiceError):
    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message, 404)


class ConflictError(InstructorServiceError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, 409)


class ValidationError(InstructorServiceError):
    def __init__(self, message: str = "Invalid input") -> None:
        super().__init__(message, 422)


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------

def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalise_dt(dt: datetime) -> datetime:
    """Store naive UTC — matches the TIMESTAMP (no tz) column in schema.sql."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _validate_title(raw: str | None) -> str:
    if raw is None or not raw.strip():
        raise ValidationError("Title is required")
    return raw.strip()


def _validate_time_limit(value: int | None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError("time_limit_min must be an integer")
    if value < 5 or value > 120:
        raise ValidationError("time_limit_min must be between 5 and 120 (BR2)")
    return value


def _validate_due_at(raw: datetime, *, must_be_future: bool) -> datetime:
    dt = _normalise_dt(raw)
    if must_be_future and dt <= _now_utc_naive():
        raise ValidationError("Due date must be in the future")
    return dt


def _validate_mcq_options(options) -> None:
    if not options or len(options) != 4:
        raise ValidationError("MCQ must have exactly 4 options (BR4)")
    correct = [o for o in options if o.is_correct]
    if len(correct) != 1:
        raise ValidationError("MCQ must have exactly 1 correct option (BR4)")
    labels = [o.label for o in options]
    if len(set(labels)) != len(labels):
        raise ValidationError("MCQ option labels must be unique")
    for o in options:
        if not o.text or not o.text.strip():
            raise ValidationError("MCQ option text cannot be empty")


def _validate_short_answers(answers) -> list[str]:
    if not answers:
        raise ValidationError("SHORT question needs at least one accepted answer (BR4)")
    cleaned = [a.strip() for a in answers if a and a.strip()]
    if not cleaned:
        raise ValidationError("SHORT question needs a non-empty accepted answer (BR4)")
    return cleaned


def _parse_accepted_answers(raw: str | None) -> list[str]:
    """
    Read the `accepted_answers` TEXT column.

    New rows store a JSON list (e.g. '["Hà Nội","Ha Noi"]'). The seed file
    stores a plain string. Support both so seeded data does not break.
    """
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return [raw]
    if isinstance(parsed, list):
        return [str(x) for x in parsed]
    return [str(parsed)]


# ----------------------------------------------------------------------
# Ownership helpers
# ----------------------------------------------------------------------

def _require_lecturer(conn: psycopg.Connection, email: str) -> int:
    if not email or "@" not in email:
        raise UnauthorizedError("Not authenticated")
    row = repo.get_user_by_email(conn, email)
    if row is None:
        raise UnauthorizedError(f"Unknown account: {email!r}")
    user_id, role, status = row
    if status != "Active":
        raise ForbiddenError("Account is disabled")
    if role != "Lecturer":
        raise ForbiddenError("Only lecturers may manage quizzes")
    return user_id


def _require_course_owner(conn, course_id: int, lecturer_id: int) -> tuple:
    course = repo.get_course(conn, course_id)
    if course is None:
        raise NotFoundError(f"Course {course_id} not found")
    if course[3] != lecturer_id:
        raise ForbiddenError("You do not own this course")
    return course


def _require_quiz_owner(conn, quiz_id: int, lecturer_id: int) -> tuple:
    """Return the quiz row (with course_code and lecturer_id at the end)."""
    quiz = repo.get_quiz(conn, quiz_id)
    if quiz is None:
        raise NotFoundError(f"Quiz {quiz_id} not found")
    # tuple layout: (quiz_id, course_id, code, created_by, title,
    #                time_limit_min, due_at, status, answers_released,
    #                created_at, lecturer_id)
    if quiz[10] != lecturer_id:
        raise ForbiddenError("You do not own this quiz")
    return quiz


# ----------------------------------------------------------------------
# Row → model
# ----------------------------------------------------------------------

def _row_to_summary(row: tuple) -> QuizSummary:
    return QuizSummary(
        quiz_id=row[0],
        course_id=row[1],
        course_code=row[2],
        title=row[3],
        time_limit_min=row[4],
        due_at=row[5],
        status=row[6],
        created_at=row[7],
        question_count=row[8],
    )


def _row_to_question(qrow: tuple, orows: list[tuple]) -> QuestionResponse:
    return QuestionResponse(
        question_id=qrow[0],
        quiz_id=qrow[1],
        position=qrow[2],
        question_type=qrow[3],
        prompt=qrow[4],
        accepted_answers=_parse_accepted_answers(qrow[5]),
        points=qrow[6],
        options=[
            OptionResponse(option_id=o[0], label=o[1], text=o[2], is_correct=o[3])
            for o in orows
        ],
    )


def _row_to_detail(quiz_row: tuple, conn: psycopg.Connection) -> QuizDetail:
    question_rows = repo.list_questions(conn, quiz_row[0])
    questions = [
        _row_to_question(qr, repo.list_options(conn, qr[0])) for qr in question_rows
    ]
    return QuizDetail(
        quiz_id=quiz_row[0],
        course_id=quiz_row[1],
        course_code=quiz_row[2],
        created_by=quiz_row[3],
        title=quiz_row[4],
        time_limit_min=quiz_row[5],
        due_at=quiz_row[6],
        status=quiz_row[7],
        answers_released=quiz_row[8],
        created_at=quiz_row[9],
        questions=questions,
    )


# ----------------------------------------------------------------------
# Public service functions
# ----------------------------------------------------------------------

def list_quizzes(lecturer_email: str) -> list[QuizSummary]:
    with db_config.connect() as conn:
        lecturer_id = _require_lecturer(conn, lecturer_email)
        rows = repo.list_quizzes_for_lecturer(conn, lecturer_id)
    return [_row_to_summary(r) for r in rows]


def get_quiz(lecturer_email: str, quiz_id: int) -> QuizDetail:
    with db_config.connect() as conn:
        lecturer_id = _require_lecturer(conn, lecturer_email)
        quiz_row = _require_quiz_owner(conn, quiz_id, lecturer_id)
        return _row_to_detail(quiz_row, conn)


def create_quiz(lecturer_email: str, payload: QuizCreateRequest) -> QuizDetail:
    # Validate before touching the DB so pure-input errors never open a txn.
    title = _validate_title(payload.title)
    time_limit = _validate_time_limit(payload.time_limit_min)
    due_at = _validate_due_at(payload.due_at, must_be_future=True)

    with db_config.connect() as conn:
        lecturer_id = _require_lecturer(conn, lecturer_email)
        _require_course_owner(conn, payload.course_id, lecturer_id)
        quiz_id = repo.insert_quiz(
            conn, payload.course_id, lecturer_id, title, time_limit, due_at
        )
        quiz_row = repo.get_quiz(conn, quiz_id)
        return _row_to_detail(quiz_row, conn)


def update_quiz(
    lecturer_email: str, quiz_id: int, payload: QuizUpdateRequest
) -> QuizDetail:
    title = _validate_title(payload.title)
    time_limit = _validate_time_limit(payload.time_limit_min)
    # An edit may legitimately move the due date in the past for record-keeping
    # purposes, so we do not force it to stay in the future here.
    due_at = _normalise_dt(payload.due_at)

    with db_config.connect() as conn:
        lecturer_id = _require_lecturer(conn, lecturer_email)
        _require_quiz_owner(conn, quiz_id, lecturer_id)
        repo.update_quiz(conn, quiz_id, title, time_limit, due_at)
        quiz_row = repo.get_quiz(conn, quiz_id)
        return _row_to_detail(quiz_row, conn)


def delete_quiz(lecturer_email: str, quiz_id: int) -> None:
    with db_config.connect() as conn:
        lecturer_id = _require_lecturer(conn, lecturer_email)
        _require_quiz_owner(conn, quiz_id, lecturer_id)
        attempts = repo.count_attempts(conn, quiz_id)
        if attempts > 0:
            raise ConflictError(
                f"Quiz has {attempts} student attempt(s) and cannot be deleted"
            )
        repo.delete_quiz_cascade(conn, quiz_id)


# ------------------------------ questions -----------------------------

def _assert_quiz_is_editable(conn, quiz_id: int) -> None:
    """Blocks question mutations after the first student attempt exists."""
    if repo.count_attempts(conn, quiz_id) > 0:
        raise ConflictError(
            "Questions cannot be modified after students have attempted this quiz"
        )


def _write_question_body(conn, question_id: int, payload) -> None:
    """Insert options for MCQ. Assumes payload has already been validated."""
    if payload.question_type == "MCQ":
        for opt in payload.options:  # type: ignore[union-attr]
            repo.insert_option(conn, question_id, opt.label, opt.text, opt.is_correct)


def create_question(
    lecturer_email: str, quiz_id: int, payload: QuestionCreateRequest
) -> QuestionResponse:
    prompt = (payload.prompt or "").strip()
    if not prompt:
        raise ValidationError("Question prompt is required")

    if payload.question_type == "MCQ":
        _validate_mcq_options(payload.options)
        accepted_json: str | None = None
    else:
        cleaned = _validate_short_answers(payload.accepted_answers)
        accepted_json = json.dumps(cleaned, ensure_ascii=False)

    with db_config.connect() as conn:
        lecturer_id = _require_lecturer(conn, lecturer_email)
        _require_quiz_owner(conn, quiz_id, lecturer_id)
        _assert_quiz_is_editable(conn, quiz_id)

        position = payload.position
        if position is None:
            position = repo.next_position(conn, quiz_id)
        else:
            if position <= 0:
                raise ValidationError("position must be a positive integer")
            if repo.position_exists(conn, quiz_id, position):
                raise ConflictError(
                    f"Position {position} is already used in this quiz"
                )

        question_id = repo.insert_question(
            conn, quiz_id, position, payload.question_type, prompt, accepted_json
        )
        _write_question_body(conn, question_id, payload)

        qrow = repo.get_question(conn, quiz_id, question_id)
        orows = repo.list_options(conn, question_id)
        return _row_to_question(qrow, orows)  # type: ignore[arg-type]


def update_question(
    lecturer_email: str,
    quiz_id: int,
    question_id: int,
    payload: QuestionUpdateRequest,
) -> QuestionResponse:
    prompt = (payload.prompt or "").strip()
    if not prompt:
        raise ValidationError("Question prompt is required")

    with db_config.connect() as conn:
        lecturer_id = _require_lecturer(conn, lecturer_email)
        _require_quiz_owner(conn, quiz_id, lecturer_id)
        _assert_quiz_is_editable(conn, quiz_id)

        existing = repo.get_question(conn, quiz_id, question_id)
        if existing is None:
            raise NotFoundError(f"Question {question_id} not found in quiz {quiz_id}")
        if existing[3] != payload.question_type:
            raise ValidationError(
                "question_type cannot be changed; delete the question and recreate it"
            )

        if payload.question_type == "MCQ":
            _validate_mcq_options(payload.options)
            accepted_json: str | None = None
        else:
            cleaned = _validate_short_answers(payload.accepted_answers)
            accepted_json = json.dumps(cleaned, ensure_ascii=False)

        repo.update_question(
            conn, question_id, payload.question_type, prompt, accepted_json
        )
        # Replace options wholesale — this is simpler and matches the
        # "PUT replaces the resource" semantics declared in design.md.
        repo.delete_options_for_question(conn, question_id)
        _write_question_body(conn, question_id, payload)

        qrow = repo.get_question(conn, quiz_id, question_id)
        orows = repo.list_options(conn, question_id)
        return _row_to_question(qrow, orows)  # type: ignore[arg-type]


def delete_question(lecturer_email: str, quiz_id: int, question_id: int) -> None:
    with db_config.connect() as conn:
        lecturer_id = _require_lecturer(conn, lecturer_email)
        _require_quiz_owner(conn, quiz_id, lecturer_id)
        _assert_quiz_is_editable(conn, quiz_id)

        existing = repo.get_question(conn, quiz_id, question_id)
        if existing is None:
            raise NotFoundError(f"Question {question_id} not found in quiz {quiz_id}")

        repo.delete_options_for_question(conn, question_id)
        repo.delete_question(conn, question_id)