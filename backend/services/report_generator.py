from datetime import datetime, timezone
from html import escape
from pathlib import Path

from backend.config import REPORTS_DIR


def _score_class(percentage: float) -> str:
    if percentage >= 85:
        return "excellent"
    if percentage >= 70:
        return "good"
    if percentage >= 55:
        return "borderline"
    return "weak"


def generate_report_html(session: dict, grading: dict) -> str:
    candidate = escape(session.get("candidate_name", "Candidate"))
    job_title = escape(session.get("job_title", "Cybersecurity Role"))
    submitted_at = session.get("submitted_at") or datetime.now(timezone.utc).isoformat()
    overall = grading["overall_percentage"]
    score_class = _score_class(overall)

    submitted_late = session.get("submitted_late", False)
    late_seconds = session.get("late_seconds", 0)
    security_violations = session.get("security_violations", 0)

    proctor_blocks = []
    if submitted_late:
        minutes = late_seconds // 60
        seconds = late_seconds % 60
        proctor_blocks.append(
            f"""
        <div class="proctor-alert warning">
          <span class="proctor-icon">Warning</span>
          <div>
            <strong>Late Submission:</strong>
            This assessment exceeded the allowed duration by <strong>{minutes}m {seconds}s</strong>.
          </div>
        </div>
        """
        )

    if security_violations > 0:
        is_critical = security_violations >= 3
        badge_class = "critical" if is_critical else "warning"
        icon = "Critical" if is_critical else "Warning"
        message = (
            f"Test auto-submitted after exceeding the maximum focus-loss limit ({security_violations} tab switches or focus losses)."
            if is_critical
            else f"Candidate lost focus or switched tabs <strong>{security_violations} times</strong> during this assessment."
        )
        proctor_blocks.append(
            f"""
        <div class="proctor-alert {badge_class}">
          <span class="proctor-icon">{icon}</span>
          <div>
            <strong>Security Violation:</strong> {message}
          </div>
        </div>
        """
        )

    proctor_html = ""
    if proctor_blocks:
        proctor_html = f"""
        <div class="proctor-audit-section">
          <h3>Proctoring and Security Audit</h3>
          {"".join(proctor_blocks)}
        </div>
        """

    category_rows = ""
    for item in grading["category_breakdown"]:
        category_rows += f"""
        <tr>
          <td>{escape(item['category'])}</td>
          <td>{item['score']} / {item['max_score']}</td>
          <td><span class="pill {_score_class(item['percentage'])}">{item['percentage']}%</span></td>
        </tr>"""

    question_blocks = ""
    for idx, item in enumerate(grading["question_results"], start=1):
        result = item["result"]
        question_blocks += f"""
        <article class="question-card">
          <header>
            <span class="q-index">Q{idx}</span>
            <span class="q-type">{escape(item['type'].replace('_', ' ').title())}</span>
            <span class="q-category">{escape(item['category'])}</span>
            <span class="q-score">{result['score']} / {result['max_score']}</span>
          </header>
          <p class="prompt">{escape(item['prompt'])}</p>
          <div class="answer-block">
            <h4>Candidate Response</h4>
            <p>{escape(item['answer'] or 'No response provided.')}</p>
          </div>
          <div class="feedback-block">
            <h4>Evaluator Feedback</h4>
            <p>{escape(result.get('feedback', ''))}</p>
            <div class="tags">
              {' '.join(f'<span class="tag strength">{escape(s)}</span>' for s in result.get('strengths', []))}
              {' '.join(f'<span class="tag gap">{escape(g)}</span>' for g in result.get('gaps', []))}
            </div>
          </div>
        </article>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Assessment Report - {candidate}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #080c14;
      --panel: rgba(17, 25, 40, 0.75);
      --text: #f1f5f9;
      --muted: #94a3b8;
      --accent: #3b82f6;
      --excellent: #10b981;
      --good: #84cc16;
      --borderline: #f59e0b;
      --weak: #ef4444;
      --border: rgba(255, 255, 255, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Outfit", "Inter", system-ui, sans-serif;
      background: radial-gradient(circle at 50% 0%, #151e33 0%, var(--bg) 100%);
      color: var(--text);
      line-height: 1.6;
      min-height: 100vh;
    }}
    .wrap {{ max-width: 980px; margin: 0 auto; padding: 40px 24px 64px; }}
    .hero {{
      background: var(--panel);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 32px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
    }}
    .eyebrow {{
      color: #38bdf8;
      text-transform: uppercase;
      letter-spacing: 0.15em;
      font-size: 11px;
      font-weight: 700;
    }}
    h1 {{ margin: 12px 0 6px; font-size: 36px; font-weight: 800; letter-spacing: -0.02em; }}
    .subtitle {{ color: var(--muted); margin: 0 0 28px; font-size: 15px; }}
    .score-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-top: 24px;
    }}
    .metric {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      transition: all 0.2s ease;
    }}
    .metric:hover {{
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.12);
    }}
    .metric label {{ display: block; color: var(--muted); font-size: 13px; margin-bottom: 8px; font-weight: 500; }}
    .metric strong {{ font-size: 26px; font-weight: 700; color: #fff; }}
    .pill {{
      display: inline-block;
      padding: 4px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .pill.excellent {{ background: rgba(16, 185, 129, 0.15); color: var(--excellent); border: 1px solid rgba(16, 185, 129, 0.25); }}
    .pill.good {{ background: rgba(132, 204, 22, 0.15); color: var(--good); border: 1px solid rgba(132, 204, 22, 0.25); }}
    .pill.borderline {{ background: rgba(245, 158, 11, 0.15); color: var(--borderline); border: 1px solid rgba(245, 158, 11, 0.25); }}
    .pill.weak {{ background: rgba(239, 68, 68, 0.15); color: var(--weak); border: 1px solid rgba(239, 68, 68, 0.25); }}
    .proctor-audit-section {{
      margin-top: 24px;
      padding: 20px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 16px;
    }}
    .proctor-audit-section h3 {{
      margin: 0 0 14px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--muted);
      font-weight: 600;
    }}
    .proctor-alert {{
      display: flex;
      gap: 14px;
      align-items: center;
      padding: 14px 16px;
      border-radius: 12px;
      border: 1px solid var(--border);
      font-size: 14px;
      margin-bottom: 10px;
      line-height: 1.5;
    }}
    .proctor-alert:last-child {{ margin-bottom: 0; }}
    .proctor-alert.warning {{
      background: rgba(245, 158, 11, 0.08);
      border-color: rgba(245, 158, 11, 0.2);
      color: #fde047;
    }}
    .proctor-alert.critical {{
      background: rgba(239, 68, 68, 0.08);
      border-color: rgba(239, 68, 68, 0.2);
      color: #fca5a5;
    }}
    .proctor-icon {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; flex-shrink: 0; }}
    .section {{ margin-top: 36px; }}
    .section h2 {{ font-size: 22px; margin-bottom: 16px; font-weight: 700; letter-spacing: -0.01em; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
    }}
    th, td {{ padding: 14px 18px; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ color: var(--muted); font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; }}
    td {{ font-size: 15px; }}
    .question-card {{
      background: var(--panel);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 24px;
      margin-bottom: 20px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }}
    .question-card header {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-bottom: 16px;
    }}
    .q-index {{
      font-weight: 800;
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.25);
    }}
    .q-type, .q-category, .q-score, .q-index {{
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 999px;
      font-weight: 600;
    }}
    .q-type {{ background: rgba(255,255,255,0.06); color: #fff; }}
    .q-category {{ background: rgba(255,255,255,0.03); color: var(--muted); border: 1px solid var(--border); }}
    .q-score {{ margin-left: auto; background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.2); font-size: 13px; font-weight: 700; }}
    .prompt {{ margin: 0 0 20px; font-size: 16px; font-weight: 500; color: #f8fafc; }}
    .answer-block, .feedback-block {{
      background: rgba(255, 255, 255, 0.015);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px 18px;
      margin-top: 14px;
    }}
    .answer-block p {{ margin: 0; color: #cbd5e1; font-size: 14.5px; white-space: pre-line; }}
    .feedback-block p {{ margin: 0 0 12px; color: #cbd5e1; font-size: 14.5px; }}
    h4 {{ margin: 0 0 10px; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 700; }}
    .tags {{ margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }}
    .tag {{ font-size: 12px; padding: 4px 10px; border-radius: 999px; font-weight: 600; }}
    .tag.strength {{ background: rgba(16, 185, 129, 0.1); color: var(--excellent); border: 1px solid rgba(16, 185, 129, 0.18); }}
    .tag.gap {{ background: rgba(239, 68, 68, 0.1); color: var(--weak); border: 1px solid rgba(239, 68, 68, 0.18); }}
    .recommendation {{
      margin-top: 20px;
      padding: 16px 20px;
      border-radius: 14px;
      border: 1px solid rgba(59, 130, 246, 0.25);
      background: rgba(59, 130, 246, 0.08);
      font-size: 15.5px;
      color: #93c5fd;
    }}
    .recommendation strong {{ color: #fff; }}
    @media print {{
      body {{ background: white; color: #111; }}
      .hero, .question-card, table {{ box-shadow: none; background: white; border-color: #ddd; }}
      .metric, .answer-block, .feedback-block {{ background: #fafafa; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">Cyber Aptitude Evaluator</div>
      <h1>{candidate}</h1>
      <p class="subtitle">{job_title} - Submitted {escape(submitted_at)}</p>
      <div class="score-grid">
        <div class="metric">
          <label>Overall Score</label>
          <strong>{grading['total_score']} / {grading['max_score']}</strong>
        </div>
        <div class="metric">
          <label>Percentage</label>
          <strong><span class="pill {score_class}">{overall}%</span></strong>
        </div>
        <div class="metric">
          <label>Questions</label>
          <strong>{len(grading['question_results'])}</strong>
        </div>
      </div>
      <div class="recommendation">
        <strong>Recommendation:</strong> {escape(grading['recommendation'])}
      </div>
      {proctor_html}
    </section>

    <section class="section">
      <h2>Category Breakdown</h2>
      <table>
        <thead>
          <tr><th>Category</th><th>Score</th><th>Percentage</th></tr>
        </thead>
        <tbody>{category_rows}</tbody>
      </table>
    </section>

    <section class="section">
      <h2>Question-Level Evaluation</h2>
      {question_blocks}
    </section>
  </div>
</body>
</html>"""
    return html


def save_report(session_id: str, html: str) -> Path:
    path = REPORTS_DIR / f"{session_id}.html"
    path.write_text(html, encoding="utf-8")
    return path
