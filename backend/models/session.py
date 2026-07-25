import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from backend.config import SESSIONS_DIR

def _save_session_file(session: dict[str, Any]) -> None:
    session_id = session["session_id"]
    filepath = SESSIONS_DIR / f"{session_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, default=str)

USED_QUESTIONS_FILE = SESSIONS_DIR / "used_questions.json"

def get_used_questions() -> list[str]:
    if not USED_QUESTIONS_FILE.exists():
        return []
    try:
        with open(USED_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def mark_questions_as_used(questions: list[dict[str, Any]]) -> None:
    used = get_used_questions()
    for q in questions:
        prompt = q.get("prompt")
        if prompt and prompt not in used:
            used.append(prompt)
    try:
        with open(USED_QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(used, f, indent=2)
    except Exception:
        pass

def public_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip grading metadata before sending questions to the candidate."""
    public = []
    option_types = {
        "mcq",
        "multi_select",
        "true_false",
        "aptitude",
        "code_analysis",
        "terminal_analysis",
        "log_analysis",
        "packet_analysis",
    }
    open_types = {"scenario", "incident_response", "threat_hunting", "short_answer"}

    for question in questions:
        qtype = question.get("type", "mcq")
        item: dict[str, Any] = {
            "id": question["id"],
            "type": qtype,
            "bucket": question.get("bucket", "technical"),
            "prompt": question["prompt"],
            "category": question.get("category", "General"),
            "difficulty": question.get("difficulty", "medium"),
            "skill_tested": question.get("skill_tested", question.get("category", "General")),
            "points": question.get("points", 5),
        }

        if question.get("artifact"):
            item["artifact"] = question["artifact"]

        if qtype in option_types:
            item["options"] = question.get("options", [])
        elif qtype == "fill_blank":
            item["input_type"] = "text"
        elif qtype == "match_following":
            item["match_pairs"] = [
                {"id": pair.get("id"), "left": pair.get("left", "")}
                for pair in question.get("match_pairs", [])
            ]
            item["match_options"] = question.get("match_options") or [
                pair.get("correct_right", "") for pair in question.get("match_pairs", [])
            ]
        elif qtype in open_types:
            item["response_format"] = "long_text"

        public.append(item)
    return public

def create_session(
    candidate_name: str,
    job_title: str,
    job_description: str,
    questions: list[dict[str, Any]],
    duration_minutes: int,
    department: str = "Cybersecurity",
) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    session: dict[str, Any] = {
        "session_id": session_id,
        "candidate_name": candidate_name,
        "job_title": job_title,
        "job_description": job_description,
        "department": department,
        "status": "pending",
        "duration_minutes": duration_minutes,
        "started_at": None,
        "submitted_at": None,
        "questions": questions,
        "answers": {},
        "submitted_late": False,
        "late_seconds": 0,
        "security_violations": 0,
        "grading_result": None,
        "attempts": [],
    }
    _save_session_file(session)
    mark_questions_as_used(questions)
    return session

def get_session(session_id: str) -> dict[str, Any] | None:
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if not filepath.exists():
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def start_session(session_id: str) -> dict[str, Any] | None:
    session = get_session(session_id)
    if not session:
        return None
    if session["status"] == "pending":
        session["status"] = "in_progress"
        session["started_at"] = datetime.now(timezone.utc).isoformat()
        _save_session_file(session)
    return session

def submit_session(
    session_id: str,
    answers: dict[str, Any],
    submitted_late: bool = False,
    late_seconds: int = 0,
    security_violations: int = 0,
) -> dict[str, Any] | None:
    session = get_session(session_id)
    if not session:
        return None
    
    session["answers"] = answers
    session["status"] = "submitted"
    session["submitted_at"] = datetime.now(timezone.utc).isoformat()
    session["submitted_late"] = submitted_late
    session["late_seconds"] = late_seconds
    session["security_violations"] = security_violations
    
    _save_session_file(session)
    return session

def store_grading_result(session_id: str, grading: dict[str, Any]) -> dict[str, Any] | None:
    session = get_session(session_id)
    if not session:
        return None
    
    session["grading_result"] = grading
    session["status"] = "graded"
    
    # Store attempt in attempt history list
    attempt_num = len(session.get("attempts", [])) + 1
    attempt_record = {
        "attempt_number": attempt_num,
        "date": session.get("submitted_at") or datetime.now(timezone.utc).isoformat(),
        "score": grading.get("total_score", 0),
        "max_score": grading.get("max_score", 100),
        "percentage": grading.get("overall_percentage", 0),
        "answers": session.get("answers", {}),
        "grading_result": grading,
        "security_violations": session.get("security_violations", 0),
        "submitted_late": session.get("submitted_late", False),
        "late_seconds": session.get("late_seconds", 0)
    }
    
    if "attempts" not in session:
        session["attempts"] = []
    session["attempts"].append(attempt_record)
    
    _save_session_file(session)
    return session

def list_sessions() -> list[dict[str, Any]]:
    sessions = []
    if not SESSIONS_DIR.exists():
        return sessions
    for filepath in SESSIONS_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                sess_data = json.load(f)
                # Return summary metadata to conserve memory/performance
                sessions.append({
                    "session_id": sess_data["session_id"],
                    "candidate_name": sess_data["candidate_name"],
                    "job_title": sess_data["job_title"],
                    "department": sess_data.get("department", "Cybersecurity"),
                    "status": sess_data["status"],
                    "duration_minutes": sess_data["duration_minutes"],
                    "started_at": sess_data.get("started_at"),
                    "submitted_at": sess_data.get("submitted_at"),
                    "score": sess_data["grading_result"].get("total_score") if sess_data.get("grading_result") else None,
                    "max_score": sess_data["grading_result"].get("max_score") if sess_data.get("grading_result") else None,
                    "percentage": sess_data["grading_result"].get("overall_percentage") if sess_data.get("grading_result") else None,
                    "attempts_count": len(sess_data.get("attempts", [])),
                })
        except Exception:
            continue
    return sorted(sessions, key=lambda x: x.get("submitted_at") or x.get("started_at") or "", reverse=True)

def delete_session(session_id: str) -> bool:
    filepath = SESSIONS_DIR / f"{session_id}.json"
    if filepath.exists():
        filepath.unlink()
        return True
    return False
