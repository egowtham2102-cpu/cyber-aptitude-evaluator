import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
REPORTS_DIR = BASE_DIR / "reports"

SESSIONS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
DEFAULT_TEST_DURATION_MINUTES = int(os.getenv("DEFAULT_TEST_DURATION_MINUTES", "45"))
