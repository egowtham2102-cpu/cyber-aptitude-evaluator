import json
import re
from typing import Any
from openai import OpenAI

from backend.config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

GRADING_SYSTEM_PROMPT = """You are a cybersecurity assessment grader.
Grade candidate responses using the provided semantic rubric.

Return ONLY valid JSON:
{
  "score": 0,
  "max_score": 5,
  "percentage": 0,
  "feedback": "Concise evaluator feedback.",
  "strengths": ["..."],
  "gaps": ["..."]
}

Rules:
- Score proportionally to rubric coverage, not exact wording.
- Partial credit is allowed.
- Be fair, specific, and professional.
- percentage = round((score / max_score) * 100, 1)"""

def _extract_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)

def _keyword_grade(answer: str, rubric: str, sample_answer: str, max_score: int) -> dict:
    answer_lower = (answer or "").lower()
    keywords = []
    for token in re.findall(r"[a-zA-Z]{4,}", f"{rubric} {sample_answer}"):
        if token.lower() not in {"should", "expect", "award", "partial", "credit", "look", "with"}:
            keywords.append(token.lower())
    unique_keywords = list(dict.fromkeys(keywords))[:12]
    hits = sum(1 for word in unique_keywords if word in answer_lower)
    ratio = hits / max(len(unique_keywords), 1)
    score = round(max_score * min(0.35 + ratio * 0.65, 1.0), 1)
    return {
        "score": score,
        "max_score": max_score,
        "percentage": round((score / max_score) * 100, 1) if max_score else 0,
        "feedback": "Graded locally using rubric keyword coverage (OpenAI unavailable).",
        "strengths": ["Demonstrated relevant concepts"] if score >= max_score * 0.6 else [],
        "gaps": ["Expand on rubric points for fuller credit"] if score < max_score * 0.8 else [],
    }

def grade_mcq(question: dict, answer: str) -> dict:
    max_score = question.get("points", 5)
    correct = question.get("correct_answer", "")
    is_correct = (answer or "").strip() == correct.strip()
    score = max_score if is_correct else 0
    return {
        "score": score,
        "max_score": max_score,
        "percentage": 100.0 if is_correct else 0.0,
        "feedback": "Correct." if is_correct else f"Incorrect. Expected: {correct}",
        "strengths": ["Selected the correct option"] if is_correct else [],
        "gaps": [] if is_correct else ["Review the underlying concept in the rubric."],
        "correct_answer": correct,
    }

def grade_multi_select(question: dict, answer: Any) -> dict:
    max_score = question.get("points", 5)
    correct = question.get("correct_answers") or question.get("correct_answer") or []
    if isinstance(correct, str):
        correct = [correct]
    
    # Parse candidate's answer
    if isinstance(answer, list):
        selected = answer
    elif isinstance(answer, str) and answer.startswith("[") and answer.endswith("]"):
        try:
            selected = json.loads(answer)
        except Exception:
            selected = [item.strip() for item in answer.split(",") if item.strip()]
    elif isinstance(answer, str):
        selected = [item.strip() for item in answer.split(",") if item.strip()]
    else:
        selected = []
    
    selected_set = {str(s).strip().lower() for s in selected}
    correct_set = {str(c).strip().lower() for c in correct}
    
    if not selected_set:
        return {
            "score": 0.0,
            "max_score": max_score,
            "percentage": 0.0,
            "feedback": "Incorrect. No options selected.",
            "strengths": [],
            "gaps": ["Review the topic and select all correct choices."],
            "correct_answer": correct
        }
    
    correct_hits = selected_set.intersection(correct_set)
    wrong_hits = selected_set.difference(correct_set)
    
    if len(correct_set) == 0:
        is_correct = len(selected_set) == 0
        score = float(max_score) if is_correct else 0.0
    else:
        ratio = (len(correct_hits) - len(wrong_hits)) / len(correct_set)
        score = max(0.0, round(max_score * ratio, 1))
    
    is_correct = score == max_score
    pct = round((score / max_score) * 100, 1) if max_score else 0.0
    
    feedback = "Correct." if is_correct else f"Partially Correct. Selected {len(correct_hits)} correct of {len(correct_set)}. Expected: {', '.join(correct)}"
    if score == 0:
        feedback = f"Incorrect. Expected: {', '.join(correct)}"
        
    return {
        "score": score,
        "max_score": max_score,
        "percentage": pct,
        "feedback": feedback,
        "strengths": ["Identified correct elements"] if len(correct_hits) > 0 else [],
        "gaps": ["Incorrect choices selected or correct choices missed"] if not is_correct else [],
        "correct_answer": correct,
    }

def grade_true_false(question: dict, answer: Any) -> dict:
    max_score = question.get("points", 5)
    correct = str(question.get("correct_answer", "")).strip().lower()
    ans_str = str(answer).strip().lower()
    is_correct = ans_str == correct
    score = float(max_score) if is_correct else 0.0
    return {
        "score": score,
        "max_score": max_score,
        "percentage": 100.0 if is_correct else 0.0,
        "feedback": "Correct." if is_correct else f"Incorrect. Expected: {question.get('correct_answer')}",
        "strengths": ["Selected the correct True/False value"] if is_correct else [],
        "gaps": [] if is_correct else ["Review the concepts behind this True/False assertion."],
        "correct_answer": question.get("correct_answer"),
    }

def grade_fill_blank(question: dict, answer: Any) -> dict:
    max_score = question.get("points", 5)
    acceptable = question.get("acceptable_answers") or question.get("correct_answer") or []
    if isinstance(acceptable, str):
        acceptable = [acceptable]
    ans_normalized = re.sub(r"\s+", " ", str(answer).strip().lower())
    is_correct = False
    for acc in acceptable:
        if ans_normalized == re.sub(r"\s+", " ", str(acc).strip().lower()):
            is_correct = True
            break
    score = float(max_score) if is_correct else 0.0
    correct_display = acceptable[0] if acceptable else ""
    return {
        "score": score,
        "max_score": max_score,
        "percentage": 100.0 if is_correct else 0.0,
        "feedback": "Correct." if is_correct else f"Incorrect. Expected: {correct_display}",
        "strengths": ["Correct term identified"] if is_correct else [],
        "gaps": [] if is_correct else [f"Review the required terminology (Expected: {correct_display})."],
        "correct_answer": correct_display,
    }

def grade_match_following(question: dict, answer: Any) -> dict:
    max_score = question.get("points", 5)
    pairs = question.get("match_pairs") or []
    
    if isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except Exception:
            answer = {}
            
    if not isinstance(answer, dict):
        answer = {}
    
    correct_count = 0
    total_pairs = len(pairs)
    explanation_details = []
    
    for pair in pairs:
        pid = pair.get("id")
        left = pair.get("left")
        correct_right = pair.get("correct_right") or pair.get("right") or ""
        candidate_right = answer.get(pid) or ""
        
        is_match = str(candidate_right).strip().lower() == str(correct_right).strip().lower()
        if is_match:
            correct_count += 1
        explanation_details.append(f"{left} -> {correct_right}")
        
    score = round(max_score * (correct_count / total_pairs), 1) if total_pairs > 0 else 0.0
    pct = round((score / max_score) * 100, 1) if max_score else 0.0
    is_correct = correct_count == total_pairs
    
    feedback = "Correct." if is_correct else f"Partially Correct. Matched {correct_count} of {total_pairs} correctly. Correct matches:\n" + "\n".join(explanation_details)
    if score == 0:
        feedback = "Incorrect. Correct matches:\n" + "\n".join(explanation_details)
        
    return {
        "score": score,
        "max_score": max_score,
        "percentage": pct,
        "feedback": feedback,
        "strengths": ["Matched key terms correctly"] if correct_count > 0 else [],
        "gaps": ["Mismatch in term assignments"] if not is_correct else [],
        "correct_answer": explanation_details,
    }

def grade_open_response(question: dict, answer: str) -> dict:
    max_score = question.get("points", 5)
    rubric = question.get("rubric", "")
    sample_answer = question.get("sample_answer", "")

    if not answer or not answer.strip():
        return {
            "score": 0.0,
            "max_score": max_score,
            "percentage": 0.0,
            "feedback": "No answer provided.",
            "strengths": [],
            "gaps": ["Provide an answer to receive credit."],
        }

    if not client:
        return _keyword_grade(answer, rubric, sample_answer, max_score)

    prompt = f"""Question Type: {question.get('type')}
Category: {question.get('category')}
Prompt: {question.get('prompt')}

Rubric:
{rubric}

Sample Ideal Answer:
{sample_answer}

Candidate Answer:
{answer or '[No answer provided]'}

Max Score: {max_score}
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": GRADING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content or "{}"
        result = _extract_json(content)
        result["max_score"] = max_score
        result["score"] = min(float(result.get("score", 0)), max_score)
        result["percentage"] = round((result["score"] / max_score) * 100, 1) if max_score else 0
        return result
    except Exception:
        return _keyword_grade(answer, rubric, sample_answer, max_score)

def grade_question(question: dict, answer: Any) -> dict:
    qtype = question.get("type", "mcq")
    
    # MCQ-like types are graded as MCQ if they have options
    if qtype in {"mcq", "aptitude", "code_analysis", "terminal_analysis", "log_analysis", "packet_analysis"}:
        if question.get("options"):
            return grade_mcq(question, answer)
        else:
            return grade_open_response(question, answer)
            
    elif qtype == "multi_select":
        return grade_multi_select(question, answer)
    elif qtype == "true_false":
        return grade_true_false(question, answer)
    elif qtype == "fill_blank":
        return grade_fill_blank(question, answer)
    elif qtype == "match_following":
        return grade_match_following(question, answer)
    else:
        return grade_open_response(question, answer)

def grade_test(questions: list[dict], answers: dict[str, Any]) -> dict:
    question_results = []
    total_score = 0.0
    total_max = 0.0
    category_scores: dict[str, dict[str, float]] = {}

    for question in questions:
        qid = question["id"]
        answer = answers.get(qid, "")
        max_score = question.get("points", 5)
        total_max += max_score

        result = grade_question(question, answer)

        total_score += result["score"]
        category = question.get("category", "General")
        bucket = category_scores.setdefault(category, {"score": 0.0, "max_score": 0.0})
        bucket["score"] += result["score"]
        bucket["max_score"] += max_score

        question_results.append(
            {
                "id": qid,
                "type": question["type"],
                "category": category,
                "prompt": question["prompt"],
                "answer": answer,
                "result": result,
            }
        )

    overall_percentage = round((total_score / total_max) * 100, 1) if total_max else 0
    recommendation = _recommendation(overall_percentage)

    category_breakdown = []
    for category, values in category_scores.items():
        pct = round((values["score"] / values["max_score"]) * 100, 1) if values["max_score"] else 0
        category_breakdown.append(
            {
                "category": category,
                "score": round(values["score"], 1),
                "max_score": values["max_score"],
                "percentage": pct,
            }
        )

    return {
        "total_score": round(total_score, 1),
        "max_score": total_max,
        "overall_percentage": overall_percentage,
        "recommendation": recommendation,
        "category_breakdown": sorted(category_breakdown, key=lambda x: x["category"]),
        "question_results": question_results,
    }

def _recommendation(percentage: float) -> str:
    if percentage >= 85:
        return "Strong Hire - demonstrates solid role-aligned cybersecurity aptitude."
    if percentage >= 70:
        return "Proceed - good foundation with some areas to probe in interview."
    if percentage >= 55:
        return "Borderline - consider follow-up technical interview on weak domains."
    return "Do Not Proceed - significant gaps relative to role requirements."

def calculate_live_stats(questions: list[dict], answers: dict[str, Any]) -> dict[str, Any]:
    """Calculate real-time score statistics for objective questions and tracking details."""
    total_questions = len(questions)
    attempted = 0
    skipped = 0
    correct = 0
    wrong = 0
    current_score = 0.0
    total_possible_score = 0.0
    
    difficulty_stats = {}
    category_stats = {}
    
    open_types = {"scenario", "incident_response", "threat_hunting", "short_answer"}
    
    for q in questions:
        qid = q["id"]
        val = answers.get(qid)
        
        qtype = q.get("type", "mcq")
        category = q.get("category", "General")
        difficulty = q.get("difficulty", "medium")
        points = q.get("points", 5)
        
        total_possible_score += points
        
        # Initialize stats dictionaries
        diff_bucket = difficulty_stats.setdefault(difficulty, {"score": 0.0, "max": 0.0, "count": 0, "correct": 0})
        cat_bucket = category_stats.setdefault(category, {"score": 0.0, "max": 0.0, "count": 0, "correct": 0})
        
        diff_bucket["max"] += points
        diff_bucket["count"] += 1
        cat_bucket["max"] += points
        cat_bucket["count"] += 1
        
        # Check if answered
        is_answered = False
        if val is not None:
            if isinstance(val, dict) and val:
                is_answered = True
            elif isinstance(val, list) and val:
                is_answered = True
            elif isinstance(val, str) and val.strip():
                is_answered = True
                
        if is_answered:
            attempted += 1
            # Check if objective
            is_objective = True
            if qtype in open_types:
                # Scenarios that don't have options are subjective
                if not q.get("options"):
                    is_objective = False
                    
            if is_objective:
                res = grade_question(q, val)
                score = res.get("score", 0.0)
                current_score += score
                diff_bucket["score"] += score
                cat_bucket["score"] += score
                
                if score == points:
                    correct += 1
                    diff_bucket["correct"] += 1
                    cat_bucket["correct"] += 1
                else:
                    wrong += 1
            else:
                # Subjective: mark as attempted but score is 0 until semantic rubric runs
                pass
        else:
            skipped += 1
            
    remaining = total_questions - attempted
    
    accuracy = round((correct / (correct + wrong)) * 100, 1) if (correct + wrong) > 0 else 0.0
    pct = round((current_score / total_possible_score) * 100, 1) if total_possible_score > 0 else 0.0
    
    return {
        "total_questions": total_questions,
        "attempted": attempted,
        "remaining": remaining,
        "skipped": skipped,
        "correct": correct,
        "wrong": wrong,
        "current_score": round(current_score, 1),
        "max_score": total_possible_score,
        "current_percentage": pct,
        "accuracy": accuracy,
        "difficulty_wise": difficulty_stats,
        "category_wise": category_stats,
    }
