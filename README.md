# Cyber Aptitude Evaluator

**BSCDS26-AICR-02** — Automated Cybersecurity Technical Aptitude Evaluator

A self-contained prototype that ingests a job description (JD), dynamically generates a calibrated cybersecurity aptitude test, enforces a time limit, grades responses with a semantic rubric, and produces a structured HTML evaluation report.

## Features

- **JD-driven test generation** — 10 questions (5 MCQ, 3 short answer, 2 scenario) tailored to the role
- **Timed assessment** — configurable duration with auto-submit on expiry
- **Semantic grading** — MCQ exact match + OpenAI rubric-based scoring for open responses
- **Structured report** — category breakdown, question-level feedback, hiring recommendation
- **Distraction-free UI** — focused test-taking environment with progress tracking

## Tech Stack

- **Backend:** Flask API
- **Frontend:** HTML / CSS / Vanilla JS
- **AI:** OpenAI API (gpt-4o-mini) — falls back to local rubric keyword grading if unavailable
- **Storage:** JSON session files (prototype-friendly, no database required)

## Quick Start

### 1. Prerequisites

- Python 3.11+
- OpenAI API key

### 2. Setup

```bash
cd cyber-aptitude-evaluator
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and set your `OPENAI_API_KEY`.

### 3. Run

From the project root:

```bash
python -m backend.app
```

Open **http://localhost:5000**

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/generate-test` | Generate test from JD and create session |
| POST | `/api/sessions/{id}/start` | Start timed session |
| GET | `/api/sessions/{id}` | Get session status |
| POST | `/api/sessions/{id}/submit` | Submit answers and grade |
| GET | `/api/sessions/{id}/report` | HTML evaluation report |

### Example: Generate Test

```json
POST /api/generate-test
{
  "candidate_name": "Alex Morgan",
  "job_title": "SOC Analyst L2",
  "job_description": "Monitor SIEM alerts, triage incidents, perform threat hunting..."
}
```

## Project Structure

```
cyber-aptitude-evaluator/
├── backend/
│   ├── app.py                 # Flask API + static frontend
│   ├── config.py
│   ├── models/session.py      # Session persistence
│   └── services/
│       ├── test_generator.py  # JD → questions
│       ├── grader.py          # Semantic rubric grading
│       └── report_generator.py
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── sessions/                  # Generated at runtime
├── reports/                   # Generated at runtime
├── requirements.txt
└── .env.example
```

## Security Notes

- Never commit `.env` or API keys to version control
- Sessions and reports are stored locally under `sessions/` and `reports/`
- For production, add authentication, HTTPS, and persistent secure storage

## License

Prototype for technical assessment use.
