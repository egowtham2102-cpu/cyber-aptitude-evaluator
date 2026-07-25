from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend.config import BASE_DIR, DEFAULT_TEST_DURATION_MINUTES, FLASK_SECRET_KEY
from backend.models.session import (
    create_session,
    get_session,
    public_questions,
    start_session,
    store_grading_result,
    submit_session,
    list_sessions,
    delete_session,
    mark_questions_as_used,
)
from backend.services.file_parser import extract_text_from_upload, sanitize_pasted_text
from backend.services.grader import grade_test
from backend.services.jd_analyzer import analysis_summary, analyze_job_description
from backend.services.report_generator import generate_report_html, save_report
from backend.services.test_generator import generate_test_from_jd
from backend.models.user import (
    authenticate_user,
    get_user_assessment_history,
    get_user_by_email,
    get_user_by_id,
    register_user,
    sanitize_user,
    seed_default_users,
)

FRONTEND_DIR = BASE_DIR / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.secret_key = FLASK_SECRET_KEY
CORS(app)

# Seed default accounts into localhost users.json
seed_default_users()


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


def _parse_positive_int(value, default: int, field_name: str) -> tuple[int | None, tuple[dict, int] | None]:
    if value in (None, ""):
        return default, None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, ({"error": f"{field_name} must be an integer"}, 400)

    if parsed <= 0:
        return None, ({"error": f"{field_name} must be greater than 0"}, 400)

    return parsed, None


def _parse_non_negative_int(value, default: int, field_name: str) -> tuple[int | None, tuple[dict, int] | None]:
    if value in (None, ""):
        return default, None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, ({"error": f"{field_name} must be an integer"}, 400)

    if parsed < 0:
        return None, ({"error": f"{field_name} must be 0 or greater"}, 400)

    return parsed, None


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": error.description or error.name}), error.code
    return error


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    raise error


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "Cyber Aptitude Evaluator"})


@app.post("/api/analyze-jd")
def api_analyze_jd():
    """Extract structured skills and role metadata from pasted or uploaded JD."""
    job_description = ""
    source = "paste"

    if request.content_type and "multipart/form-data" in request.content_type:
        uploaded = request.files.get("file")
        pasted = (request.form.get("job_description") or "").strip()

        if uploaded and uploaded.filename:
            extracted, file_source, file_error = extract_text_from_upload(uploaded)
            if file_error:
                body, status = file_error
                return jsonify(body), status
            job_description = extracted
            source = file_source
            if pasted:
                job_description = f"{job_description}\n\n{pasted}".strip()
        else:
            job_description = sanitize_pasted_text(pasted)
    else:
        payload = request.get_json(silent=True) or {}
        job_description = sanitize_pasted_text(payload.get("job_description"))

    if len(job_description) < 40:
        return jsonify({"error": "job_description must be at least 40 characters"}), 400

    try:
        analysis = analyze_job_description(job_description)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "source": source,
            "job_description": job_description,
            "analysis": analysis,
            "summary": analysis_summary(analysis),
        }
    )


@app.post("/api/generate-test")
def api_generate_test():
    payload = request.get_json(silent=True) or {}
    candidate_name = (payload.get("candidate_name") or "").strip()
    job_title = (payload.get("job_title") or "").strip()
    job_description = (payload.get("job_description") or "").strip()
    department = (payload.get("department") or "Cybersecurity").strip()
    duration_minutes, duration_error = _parse_positive_int(
        payload.get("duration_minutes"),
        DEFAULT_TEST_DURATION_MINUTES,
        "duration_minutes",
    )

    if not candidate_name:
        return jsonify({"error": "candidate_name is required"}), 400
    if not job_title:
        return jsonify({"error": "job_title is required"}), 400
    if len(job_description) < 40:
        return jsonify({"error": "job_description must be at least 40 characters"}), 400
    if duration_error:
        body, status = duration_error
        return jsonify(body), status

    test_data = generate_test_from_jd(job_title, job_description, department=department)
    questions = test_data.get("questions", [])
    duration = int(test_data.get("duration_minutes") or duration_minutes)

    session = create_session(
        candidate_name=candidate_name,
        job_title=job_title or test_data.get("job_title", "Cybersecurity Role"),
        job_description=job_description,
        questions=questions,
        duration_minutes=duration,
        department=department,
    )

    return jsonify(
        {
            "session_id": session["session_id"],
            "candidate_name": session["candidate_name"],
            "job_title": session["job_title"],
            "department": session.get("department", "Cybersecurity"),
            "duration_minutes": session["duration_minutes"],
            "question_count": len(questions),
            "questions": public_questions(questions),
        }
    )


@app.post("/api/sessions/<session_id>/start")
def api_start_session(session_id: str):
    session = start_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    if session["status"] != "in_progress":
        return jsonify({"error": "Session cannot be started"}), 400

    expires_at = None
    if session.get("started_at"):
        started = datetime.fromisoformat(session["started_at"])
        expires_at = started.timestamp() + session["duration_minutes"] * 60

    return jsonify(
        {
            "session_id": session["session_id"],
            "status": session["status"],
            "started_at": session["started_at"],
            "duration_minutes": session["duration_minutes"],
            "expires_at_epoch": expires_at,
            "questions": public_questions(session["questions"]),
        }
    )


@app.get("/api/sessions/<session_id>")
def api_get_session(session_id: str):
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    expires_at = None
    if session.get("started_at") and session["status"] == "in_progress":
        started = datetime.fromisoformat(session["started_at"])
        expires_at = started.timestamp() + session["duration_minutes"] * 60

    return jsonify(
        {
            "session_id": session["session_id"],
            "candidate_name": session["candidate_name"],
            "job_title": session["job_title"],
            "department": session.get("department", "Cybersecurity"),
            "status": session["status"],
            "duration_minutes": session["duration_minutes"],
            "started_at": session.get("started_at"),
            "submitted_at": session.get("submitted_at"),
            "expires_at_epoch": expires_at,
            "questions": public_questions(session["questions"])
            if session["status"] in {"pending", "in_progress"}
            else [],
            "grading_result": session.get("grading_result"),
        }
    )


@app.post("/api/sessions/<session_id>/submit")
def api_submit_session(session_id: str):
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    if session["status"] not in {"in_progress", "pending"}:
        return jsonify({"error": "Session already submitted"}), 400

    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers") or {}
    security_violations, violation_error = _parse_non_negative_int(
        payload.get("security_violations"),
        0,
        "security_violations",
    )

    if violation_error:
        body, status = violation_error
        return jsonify(body), status

    if session["status"] == "pending":
        start_session(session_id)
        session = get_session(session_id)

    submitted_late = False
    late_seconds = 0
    if session.get("started_at"):
        started = datetime.fromisoformat(session["started_at"])
        elapsed_seconds = (datetime.now(timezone.utc) - started).total_seconds()
        allowed_seconds = session["duration_minutes"] * 60
        if elapsed_seconds > allowed_seconds:
            submitted_late = True
            late_seconds = int(elapsed_seconds - allowed_seconds)

    submit_session(
        session_id,
        answers,
        submitted_late=submitted_late,
        late_seconds=late_seconds,
        security_violations=security_violations,
    )
    session = get_session(session_id)
    grading = grade_test(session["questions"], answers)
    store_grading_result(session_id, grading)

    html = generate_report_html(session, grading)
    report_path = save_report(session_id, html)

    return jsonify(
        {
            "session_id": session_id,
            "status": "graded",
            "grading_result": grading,
            "report_url": f"/api/sessions/{session_id}/report",
            "report_path": str(report_path),
        }
    )


@app.get("/api/sessions/<session_id>/report")
def api_get_report(session_id: str):
    session = get_session(session_id)
    if not session or not session.get("grading_result"):
        return jsonify({"error": "Report not available"}), 404

    html = generate_report_html(session, session["grading_result"])
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/api/sessions")
@admin_required
def api_list_sessions():
    sessions = list_sessions()
    return jsonify(sessions)


@app.delete("/api/sessions/<session_id>")
@admin_required
def api_delete_session(session_id: str):
    success = delete_session(session_id)
    if not success:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"status": "deleted"})


@app.post("/api/sessions/<session_id>/live-stats")
def api_live_stats(session_id: str):
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers") or {}
    from backend.services.grader import calculate_live_stats
    stats = calculate_live_stats(session["questions"], answers)
    return jsonify(stats)


@app.post("/api/sessions/<session_id>/retake")
def api_retake_session(session_id: str):
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    from backend.services.randomizer import apply_randomization, generation_seed
    new_seed = generation_seed()
    
    session["status"] = "pending"
    session["answers"] = {}
    session["started_at"] = None
    session["submitted_at"] = None
    session["grading_result"] = None
    session["submitted_late"] = False
    session["late_seconds"] = 0
    session["security_violations"] = 0
    session["questions"] = apply_randomization(session["questions"], new_seed)
    
    from backend.models.session import _save_session_file
    _save_session_file(session)
    
    return jsonify({
        "session_id": session_id,
        "status": "pending",
        "questions": public_questions(session["questions"]),
        "duration_minutes": session["duration_minutes"],
    })


@app.post("/api/sessions/<session_id>/regenerate")
def api_regenerate_session(session_id: str):
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    # Generate a completely new set of questions from the JD
    test_data = generate_test_from_jd(
        session["job_title"],
        session["job_description"],
        department=session.get("department", "Cybersecurity")
    )
    new_questions = test_data.get("questions", [])
    
    session["status"] = "pending"
    session["answers"] = {}
    session["started_at"] = None
    session["submitted_at"] = None
    session["grading_result"] = None
    session["submitted_late"] = False
    session["late_seconds"] = 0
    session["security_violations"] = 0
    session["questions"] = new_questions
    
    from backend.models.session import _save_session_file
    _save_session_file(session)
    mark_questions_as_used(new_questions)
    
    return jsonify({
        "session_id": session_id,
        "status": "pending",
        "questions": public_questions(session["questions"]),
        "duration_minutes": session["duration_minutes"],
    })
# ── User Authentication API Endpoints (Local JSON File Storage) ──

@app.post("/api/user/register")
def api_user_register():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name") or ""
    email = payload.get("email") or ""
    password = payload.get("password") or ""
    department = payload.get("department") or "Cybersecurity"
    role = payload.get("role") or "Candidate"

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400

    user, error = register_user(name, email, password, department=department, role=role)
    if error:
        return jsonify({"error": error}), 400

    session["user_id"] = user["id"]
    return jsonify({
        "status": "success",
        "message": "Account created successfully",
        "user": user,
        "token": f"usr_token_{user['id']}"
    })


@app.post("/api/user/login")
def api_user_login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email") or ""
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user, error = authenticate_user(email, password)
    if error:
        return jsonify({"error": error}), 401

    session["user_id"] = user["id"]
    return jsonify({
        "status": "success",
        "message": "Login successful",
        "user": user,
        "token": f"usr_token_{user['id']}"
    })


@app.post("/api/user/logout")
def api_user_logout():
    session.pop("user_id", None)
    return jsonify({"status": "success", "message": "Logged out"})


@app.get("/api/user/me")
def api_user_me():
    user_id = session.get("user_id")
    
    if not user_id:
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer usr_token_"):
            user_id = auth_hdr.replace("Bearer usr_token_", "").strip()
            
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            return jsonify({
                "authenticated": True,
                "user": sanitize_user(user)
            })

    email_hdr = request.headers.get("X-User-Email")
    if email_hdr:
        user = get_user_by_email(email_hdr)
        if user:
            return jsonify({
                "authenticated": True,
                "user": sanitize_user(user)
            })

    return jsonify({"authenticated": False, "user": None})


@app.get("/api/user/history")
def api_user_history():
    email = request.args.get("email") or ""
    name = request.args.get("name") or ""
    
    if not email and not name and session.get("user_id"):
        user = get_user_by_id(session["user_id"])
        if user:
            email = user.get("email", "")
            name = user.get("name", "")

    history = get_user_assessment_history(candidate_name=name, candidate_email=email)
    return jsonify(history)


@app.post("/api/admin/login")
def api_admin_login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username")
    password = payload.get("password")
    
    if username == "cyber" and password == "Cyber@123":
        session["is_admin"] = True
        return jsonify({"status": "success", "message": "Authenticated"})
    return jsonify({"error": "Invalid credentials"}), 401


@app.post("/api/admin/logout")
def api_admin_logout():
    session.pop("is_admin", None)
    return jsonify({"status": "success", "message": "Logged out"})


@app.get("/api/admin/check-auth")
def api_admin_check_auth():
    return jsonify({"authenticated": session.get("is_admin", False)})


@app.get("/api/admin/analytics")
@admin_required
def api_admin_analytics():
    import json
    from backend.config import SESSIONS_DIR
    
    total = 0
    completed = 0
    total_percentage = 0.0
    graded_count = 0
    
    category_stats = {}
    skill_stats = {}
    
    for filepath in SESSIONS_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                session = json.load(f)
            total += 1
            status = session.get("status")
            if status in {"graded", "submitted"}:
                completed += 1
                
            grading = session.get("grading_result")
            if grading:
                graded_count += 1
                total_percentage += grading.get("overall_percentage", 0.0)
                
                # Category stats
                for cat_item in grading.get("category_breakdown", []):
                    cat = cat_item["category"]
                    score = cat_item["score"]
                    max_score = cat_item["max_score"]
                    bucket = category_stats.setdefault(cat, {"score": 0.0, "max": 0.0})
                    bucket["score"] += score
                    bucket["max"] += max_score
                    
                # Skill stats (question-level missed skills)
                for q_res in grading.get("question_results", []):
                    qid = q_res["id"]
                    q_def = next((q for q in session["questions"] if q["id"] == qid), None)
                    if q_def:
                        skill = q_def.get("skill_tested") or q_def.get("category") or "General"
                        score = q_res["result"].get("score", 0.0)
                        max_score = q_res["result"].get("max_score", 5.0)
                        
                        bucket = skill_stats.setdefault(skill, {"score": 0.0, "max": 0.0, "attempts": 0})
                        bucket["score"] += score
                        bucket["max"] += max_score
                        bucket["attempts"] += 1
        except Exception as e:
            continue
            
    avg_score = round(total_percentage / graded_count, 1) if graded_count > 0 else 0.0
    completion_rate = round((completed / total) * 100, 1) if total > 0 else 0.0
    
    # Calculate average percentage per category
    category_averages = []
    for cat, v in category_stats.items():
        pct = round((v["score"] / v["max"]) * 100, 1) if v["max"] > 0 else 0.0
        category_averages.append({"category": cat, "percentage": pct})
    category_averages.sort(key=lambda x: x["percentage"])
    
    # Calculate average percentage per skill
    skill_averages = []
    for skill, v in skill_stats.items():
        pct = round((v["score"] / v["max"]) * 100, 1) if v["max"] > 0 else 0.0
        skill_averages.append({"skill": skill, "percentage": pct, "attempts": v["attempts"]})
    skill_averages.sort(key=lambda x: x["percentage"])
    
    return jsonify({
        "total_assessments": total,
        "completed_assessments": completed,
        "completion_rate": completion_rate,
        "average_score": avg_score,
        "weak_categories": category_averages[:5],
        "most_missed_skills": skill_averages[:5],
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
