import json
import urllib.request
import traceback

base = "http://127.0.0.1:5000"
data = {
    "candidate_name": "Test User",
    "job_title": "Software Engineer",
    "job_description": "Develop and maintain cloud-native microservices using Python, Docker, and REST APIs. Collaborate with security and QA teams to ensure scalable and reliable deployment pipelines.",
    "duration_minutes": 45,
}

try:
    req = urllib.request.Request(
        base + "/api/generate-test",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        gen = json.loads(resp.read().decode("utf-8"))
    print("generate ok", gen["session_id"])

    answers = {}
    for q in gen["questions"]:
        if q["type"] == "mcq":
            answers[q["id"]] = q["options"][0]
        else:
            answers[q["id"]] = "Test response"

    submit = {"answers": answers, "security_violations": 0}
    req2 = urllib.request.Request(
        base + f"/api/sessions/{gen['session_id']}/submit",
        data=json.dumps(submit).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req2, timeout=30) as resp2:
        out = json.loads(resp2.read().decode("utf-8"))
    print("submit ok", out["status"], out["report_url"])

    req3 = urllib.request.Request(base + out["report_url"])
    with urllib.request.urlopen(req3, timeout=30) as resp3:
        html = resp3.read().decode("utf-8")
    print("report len", len(html))
except Exception:
    traceback.print_exc()
