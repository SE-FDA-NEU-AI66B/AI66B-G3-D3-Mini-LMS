"""
quiz_service.py — business logic for quiz listings.

The service does not know about HTTP. It does not know about SQL. It
receives a plain argument and returns a plain result. That is what makes
the rules unit-testable without a server and without a database.

This service now enforces a role gate: only an Active *Student* may reach
the student quiz list. A Lecturer or Admin who used to be a Student (and
still has enrollment rows) is rejected — their data stays intact for a
future demotion, but they cannot access the student endpoint.
"""

from __future__ import annotations

from src.models.quiz import QuizListItem
from src.repositories import quiz_repository
import json
from fastapi import HTTPException
from src.config import db as db_config
from src.repositories import quiz_repository
from src.models.quiz import SubmitResponse


class StudentNotFoundError(Exception):
    """Raised when the caller asks for a student the system does not know,
    or when the caller is authenticated but not permitted."""


def list_visible_quizzes(student_email: str) -> list[QuizListItem]:
    """
    Return the quizzes visible to `student_email`.

    BR6 is enforced downstream in the query:
      - the quiz must be Published,
      - the due date must be in the future,
      - the student must be enrolled with status = Active.

    Role gate (defence-in-depth):
      - the account must exist,
      - it must be Active,
      - it must have role = Student.
    """
    if not student_email or "@" not in student_email:
        raise StudentNotFoundError(f"Invalid student email: {student_email!r}")

    row = quiz_repository.get_user_role_status(student_email)
    if row is None:
        raise StudentNotFoundError(f"Unknown account: {student_email!r}")
    _user_id, role, status = row
    if status != "Active":
        raise StudentNotFoundError(f"Account is disabled: {student_email!r}")
    if role != "Student":
        raise StudentNotFoundError(
            f"{student_email} is not a student (role: {role})"
        )

    return quiz_repository.find_visible_quizzes(student_email)

def submit_and_grade(student_email: str, quiz_id: int, answers_payload: dict, auto_submitted: bool) -> SubmitResponse:
    with db_config.connect() as conn:
        # 1. Check User (BR8)
        user = quiz_repository.get_user_role_status(student_email)
        if not user or user[2] != 'Active' or user[1] != 'Student':
            raise HTTPException(403, "Access denied. Must be an active student.")
        student_id = user[0]
        
        # 2. Lấy câu hỏi từ DB
        data = quiz_repository.get_quiz_with_questions_for_taking(conn, quiz_id)
        if not data: 
            raise HTTPException(404, "Quiz not found")
            
        score = 0
        total_questions = len(data[1])
        graded_answers = []

        # 3. Chấm điểm (BR4)
        for q, opts in data[1]:
            q_id_str = str(q[0])
            q_type = q[2]
            points = q[4]
            
            user_ans = answers_payload.get(q_id_str)
            is_correct = False
            chosen_option_id = None
            text_answer = None

            if q_type == 'MCQ':
                if user_ans:
                    chosen_option_id = int(user_ans)
                    with conn.cursor() as cur:
                        cur.execute("SELECT is_correct FROM option WHERE option_id = %s AND question_id = %s", (chosen_option_id, q[0]))
                        opt_row = cur.fetchone()
                        if opt_row and opt_row[0]:
                            is_correct = True
                            score += points
            elif q_type == 'SHORT':
                if user_ans:
                    text_answer = str(user_ans).strip()
                    with conn.cursor() as cur:
                        cur.execute("SELECT accepted_answers FROM question WHERE question_id = %s", (q[0],))
                        ans_row = cur.fetchone()
                        if ans_row and ans_row[0]:
                            try:
                                accepted_list = json.loads(ans_row[0])
                            except:
                                accepted_list = [ans_row[0]]
                            
                            # So sánh (case-insensitive, trim)
                            for accepted in accepted_list:
                                if text_answer.lower() == accepted.strip().lower():
                                    is_correct = True
                                    score += points
                                    break
                                    
            graded_answers.append({
                "question_id": q[0],
                "chosen_option_id": chosen_option_id,
                "text_answer": text_answer,
                "is_correct": is_correct
            })

        # 4. Lưu kết quả
        attempt_id = quiz_repository.create_attempt(conn, quiz_id, student_id)
        quiz_repository.save_graded_answers(conn, attempt_id, graded_answers, score, total_questions, auto_submitted)
        
        # 6. Format điểm (BR5) - Quy đổi ra thang điểm 10
        if total_questions > 0:
            score_10 = (score / total_questions) * 10
            percentage = f"{(score / total_questions * 100):.2f}%"
        else:
            score_10 = 0.0
            percentage = "0.00%"
        
        return SubmitResponse(
            attempt_id=attempt_id, 
            score=score,          # Vẫn trả về số câu đúng (VD: 2) để lưu DB
            total=total_questions,# Tổng số câu (VD: 4)
            percentage=percentage # Phần trăm (VD: 50.00%)
        )