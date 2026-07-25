import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import SESSIONS_DIR, REPORTS_DIR

USERS_FILE = SESSIONS_DIR / "users.json"

def _ensure_users_file() -> None:
    SESSIONS_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

def load_users() -> list[dict[str, Any]]:
    _ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_users(users: list[dict[str, Any]]) -> None:
    _ensure_users_file()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, default=str)

def sanitize_user(user: dict[str, Any]) -> dict[str, Any]:
    """Return user dict without sensitive hash fields."""
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "department": user.get("department", "Cybersecurity"),
        "role": user.get("role", "candidate"),
        "created_at": user.get("created_at"),
        "last_login": user.get("last_login"),
    }

def seed_default_users() -> None:
    """Seed initial default accounts into local users.json file if empty or missing default accounts."""
    users = load_users()
    existing_emails = {u["email"].lower() for u in users}

    default_accounts = [
        {
            "name": "Alex Morgan",
            "email": "alex.morgan@cyber.io",
            "password": "Cyber@123",
            "department": "Cybersecurity",
            "role": "SOC Analyst",
        },
        {
            "name": "Demo Candidate",
            "email": "demo@test.com",
            "password": "demo123",
            "department": "Cybersecurity",
            "role": "Candidate",
        },
        {
            "name": "System Security Officer",
            "email": "admin@cyber.io",
            "password": "Admin@123",
            "department": "DevOps / Cloud Security",
            "role": "Security Engineer",
        },
    ]

    modified = False
    for acc in default_accounts:
        if acc["email"].lower() not in existing_emails:
            users.append(
                {
                    "id": f"usr_{uuid.uuid4().hex[:12]}",
                    "name": acc["name"],
                    "email": acc["email"].lower(),
                    "password_hash": generate_password_hash(acc["password"]),
                    "department": acc["department"],
                    "role": acc["role"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_login": None,
                }
            )
            modified = True

    if modified:
        save_users(users)

def get_user_by_email(email: str) -> dict[str, Any] | None:
    email_clean = email.strip().lower()
    users = load_users()
    for u in users:
        if u["email"].lower() == email_clean:
            return u
    return None

def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            return u
    return None

def register_user(
    name: str,
    email: str,
    password: str,
    department: str = "Cybersecurity",
    role: str = "Candidate",
) -> tuple[dict[str, Any] | None, str | None]:
    """Register user and store in localhost users.json file."""
    seed_default_users()
    email_clean = email.strip().lower()
    name_clean = name.strip()

    if get_user_by_email(email_clean):
        return None, "An account with this email address already exists."

    if len(password) < 6:
        return None, "Password must be at least 6 characters long."

    users = load_users()
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    new_user = {
        "id": user_id,
        "name": name_clean,
        "email": email_clean,
        "password_hash": generate_password_hash(password),
        "department": department,
        "role": role,
        "created_at": now,
        "last_login": now,
    }

    users.append(new_user)
    save_users(users)
    return sanitize_user(new_user), None

def authenticate_user(email: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
    """Authenticate user credentials against localhost users.json file."""
    seed_default_users()
    email_clean = email.strip().lower()
    user = get_user_by_email(email_clean)

    if not user:
        return None, "Invalid email or password."

    if not check_password_hash(user["password_hash"], password):
        return None, "Invalid email or password."

    # Update last login timestamp in local file
    users = load_users()
    for u in users:
        if u["id"] == user["id"]:
            u["last_login"] = datetime.now(timezone.utc).isoformat()
            break
    save_users(users)

    return sanitize_user(user), None

def get_user_assessment_history(candidate_name: str, candidate_email: str = "") -> list[dict[str, Any]]:
    """Fetch all assessment sessions for this user from local session files."""
    history = []
    if not SESSIONS_DIR.exists():
        return history

    name_lower = candidate_name.strip().lower()
    email_lower = candidate_email.strip().lower()

    for filepath in SESSIONS_DIR.glob("*.json"):
        if filepath.name == "users.json" or filepath.name == "used_questions.json":
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                sess_data = json.load(f)
                c_name = (sess_data.get("candidate_name") or "").strip().lower()
                
                # Match by candidate name or email if recorded
                if name_lower and (c_name == name_lower or (email_lower and email_lower in c_name)):
                    grading = sess_data.get("grading_result") or {}
                    history.append({
                        "session_id": sess_data["session_id"],
                        "job_title": sess_data.get("job_title", "Cyber Role"),
                        "department": sess_data.get("department", "Cybersecurity"),
                        "status": sess_data.get("status", "pending"),
                        "submitted_at": sess_data.get("submitted_at"),
                        "started_at": sess_data.get("started_at"),
                        "score": grading.get("total_score"),
                        "max_score": grading.get("max_score"),
                        "percentage": grading.get("overall_percentage"),
                        "attempts_count": len(sess_data.get("attempts", [])),
                    })
        except Exception:
            continue

    return sorted(history, key=lambda x: x.get("submitted_at") or x.get("started_at") or "", reverse=True)
