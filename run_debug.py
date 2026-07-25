import sys
import traceback
from backend.services.dynamic_generator import generate_test_from_jd

job_title = "Cybersecurity Analyst"
job_description = (
    "Looking for a Cybersecurity Analyst to monitor network traffic, perform incident triage, "
    "analyze firewall logs, and investigate potential security incidents using SIEM tools. "
    "Knowledge of Python and shell scripting is a plus."
)

try:
    print("Calling generate_test_from_jd...")
    test_data = generate_test_from_jd(
        job_title=job_title,
        job_description=job_description,
        department="Cybersecurity"
    )
    print("Result keys:", list(test_data.keys()))
    if "generation_seed" in test_data:
        print("Seed used:", test_data["generation_seed"])
    
    questions = test_data.get("questions", [])
    print("Questions count:", len(questions))
    for i, q in enumerate(questions[:3]):
        print(f"Question {i+1}: Type={q.get('type')}, Bucket={q.get('bucket')}")
        print("Prompt:", q.get("prompt"))
        print("Options:", q.get("options"))
        print("Correct Answer:", q.get("correct_answer"))
        print("-" * 40)

except Exception as e:
    print("Caught error in script:")
    traceback.print_exc()
