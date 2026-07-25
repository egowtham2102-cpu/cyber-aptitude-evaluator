# 🛡️ Cyber Aptitude Evaluator

**BSCDS26-AICR-02** — An automated cybersecurity technical aptitude evaluation platform.

Cyber Aptitude Evaluator ingests a job description (JD), dynamically generates a calibrated cybersecurity aptitude test, administers it under a timer, grades responses using an AI-powered semantic rubric, and produces a structured evaluation report — reducing manual technical screening effort for cybersecurity hiring.

---

## ✨ Features

- **JD-driven test generation** — automatically creates 10 questions (5 MCQ, 3 short answer, 2 scenario-based) tailored to the role and job description
- **Timed assessment** — configurable duration with auto-submit on expiry
- **Semantic grading** — exact-match scoring for MCQs and AI rubric-based scoring for open-ended answers (OpenAI GPT-4o-mini), with a local keyword-based fallback if the API is unavailable
- **Structured evaluation report** — category-wise score breakdown, question-level feedback, and a hiring recommendation
- **User accounts & history** — candidate registration/login with assessment history
- **Admin dashboard** — session management and analytics
- **Resume/JD file upload support** — parses PDF and DOCX files
- **Distraction-free UI** — focused test-taking interface with live progress tracking

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask, Flask-CORS |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| AI / Grading | OpenAI API (`gpt-4o-mini`), with local fallback grading |
| File Parsing | `pypdf`, `python-docx` |
| Storage | JSON files (no database required) |
| Environment | `python-dotenv` |
| Production Server | `gunicorn` |

---

## 📁 Project Structure

```
cyber-aptitude-evaluator/
├── backend/
│   ├── app.py                  # Flask app entry point + API routes
│   ├── config.py                # Environment & app configuration
│   ├── models/
│   │   ├── session.py           # Test session persistence
│   │   └── user.py              # User accounts & authentication
│   └── services/
│       ├── jd_analyzer.py       # Job description analysis
│       ├── test_generator.py    # JD → question generation
│       ├── dynamic_generator.py # Dynamic/randomized question generation
│       ├── randomizer.py        # Question randomization logic
│       ├── grader.py            # Semantic (AI) grading engine
│       ├── report_generator.py  # HTML report generation
│       └── file_parser.py       # PDF/DOCX text extraction
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── sessions/                    # Auto-generated session data (JSON)
├── reports/                     # Auto-generated evaluation reports
├── requirements.txt
├── .env.example
└── run.bat                      # Windows quick-start script
```

---

## ⚙️ Prerequisites

- Python **3.11+**
- An **OpenAI API key** ([get one here](https://platform.openai.com/api-keys))
- pip (comes bundled with Python)

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/cyber-aptitude-evaluator.git
cd cyber-aptitude-evaluator
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

**Windows**
```bash
.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and fill in your own values:

**Windows**
```bash
copy .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

Then edit `.env`:

```env
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
FLASK_SECRET_KEY=change-me-in-production
DEFAULT_TEST_DURATION_MINUTES=45
```

> ⚠️ Never commit your real `.env` file. It is already excluded via `.gitignore`.

### 5. Run the application

From the project root:

```bash
python -m backend.app
```

Windows users can alternatively double-click / run:

```bash
run.bat
```

The app will start at:

```
http://localhost:5000
```

Open that URL in your browser to use the app.

---

## 🔌 API Reference

### Health & JD Analysis
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/analyze-jd` | Analyze a job description |

### Test & Session Management
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/generate-test` | Generate a test from a JD and create a session |
| POST | `/api/sessions/<session_id>/start` | Start the timed session |
| GET | `/api/sessions/<session_id>` | Get session status/details |
| POST | `/api/sessions/<session_id>/submit` | Submit answers for grading |
| GET | `/api/sessions/<session_id>/report` | Get the HTML evaluation report |
| GET | `/api/sessions` | List all sessions |
| DELETE | `/api/sessions/<session_id>` | Delete a session |
| POST | `/api/sessions/<session_id>/live-stats` | Push live progress stats |
| POST | `/api/sessions/<session_id>/retake` | Retake an existing test |
| POST | `/api/sessions/<session_id>/regenerate` | Regenerate test questions |

### User Accounts
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/user/register` | Register a new candidate account |
| POST | `/api/user/login` | Log in |
| POST | `/api/user/logout` | Log out |
| GET | `/api/user/me` | Get current logged-in user |
| GET | `/api/user/history` | Get candidate's assessment history |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/admin/login` | Admin login |
| POST | `/api/admin/logout` | Admin logout |
| GET | `/api/admin/check-auth` | Verify admin session |
| GET | `/api/admin/analytics` | Get platform-wide analytics |

---

## 📝 Example: Generate a Test

```bash
curl -X POST http://localhost:5000/api/generate-test \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_name": "Alex Morgan",
    "job_title": "SOC Analyst L2",
    "job_description": "Monitor SIEM alerts, triage incidents, perform threat hunting..."
  }'
```

This returns a `session_id` you can use to start the timed test, submit answers, and later fetch the report.

---

## 🐞 Debugging

A standalone debug script is included to test question generation without running the full server:

```bash
python run_debug.py
```

---

## 📦 Deployment

For production, use `gunicorn` instead of the Flask development server:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
```

Make sure `FLASK_SECRET_KEY` is set to a strong, unique value in production.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is a prototype developed for academic/demonstration purposes under **BSCDS26-AICR-02**. Add a license of your choice (e.g., MIT) if distributing publicly.

---

## 📬 Contact

For questions or feedback, please open an issue on this repository.
