"""AI-powered job description analysis and structured skill extraction."""

import json
import re
from typing import Any

from openai import OpenAI

from backend.config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

ANALYSIS_SYSTEM_PROMPT = """You are an expert technical recruiter and cybersecurity hiring analyst.
Analyze the job description and extract structured hiring intelligence.

Return ONLY valid JSON with this exact shape:
{
  "job_title": "string",
  "experience": "string summarizing years/level required",
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1", "skill2"],
  "responsibilities": ["responsibility1", "responsibility2"],
  "programming_languages": ["Python", "..."],
  "databases": ["PostgreSQL", "..."],
  "cloud_platforms": ["AWS", "..."],
  "devops": ["Docker", "CI/CD", "..."],
  "security_domains": ["SOC", "Incident Response", "..."],
  "networking": ["TCP/IP", "Firewalls", "..."],
  "operating_systems": ["Linux", "Windows", "..."],
  "frameworks": ["React", "Flask", "..."],
  "certifications": ["CISSP", "Security+", "..."]
}

Rules:
- Extract only what is stated or strongly implied in the JD.
- Use concise, interview-relevant skill names.
- Return empty arrays when a category is not mentioned.
- Do not include markdown fences or commentary outside JSON."""

SKILL_CATEGORIES = [
    "required_skills",
    "preferred_skills",
    "responsibilities",
    "programming_languages",
    "databases",
    "cloud_platforms",
    "devops",
    "security_domains",
    "networking",
    "operating_systems",
    "frameworks",
    "certifications",
]

KEYWORD_MAP: dict[str, list[str]] = {
    "programming_languages": [
        "python", "java", "javascript", "typescript", "go", "golang", "c++", "c#",
        "ruby", "rust", "bash", "powershell", "sql", "kotlin", "swift", "php",
    ],
    "databases": [
        "postgresql", "mysql", "mongodb", "redis", "oracle", "sql server", "dynamodb",
        "elasticsearch", "sqlite", "mariadb", "cassandra",
    ],
    "cloud_platforms": [
        "aws", "azure", "gcp", "google cloud", "kubernetes", "eks", "aks", "cloudflare",
    ],
    "devops": [
        "docker", "kubernetes", "jenkins", "gitlab ci", "github actions", "terraform",
        "ansible", "ci/cd", "devops", "helm", "argocd",
    ],
    "security_domains": [
        "soc", "siem", "incident response", "threat hunting", "vulnerability management",
        "penetration testing", "malware analysis", "digital forensics", "grc", "iam",
        "cloud security", "application security", "zero trust",
    ],
    "networking": [
        "tcp/ip", "dns", "firewall", "vpn", "routing", "switching", "wireshark",
        "network security", "load balancer", "proxy",
    ],
    "operating_systems": [
        "linux", "windows", "macos", "ubuntu", "centos", "active directory", "unix",
    ],
    "frameworks": [
        "react", "angular", "vue", "flask", "django", "fastapi", "spring", "node.js",
        "express", ".net", "selenium", "pytest",
    ],
    "certifications": [
        "cissp", "cism", "ceh", "security+", "comptia", "oscp", "gcih", "gsec",
        "aws certified", "azure certified", "ccna", "ccnp",
    ],
}


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


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned and cleaned not in items:
                items.append(cleaned)
    return items


def _normalize_analysis(data: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "job_title": str(data.get("job_title") or "Technical Role").strip() or "Technical Role",
        "experience": str(data.get("experience") or "Not specified").strip() or "Not specified",
    }
    for key in SKILL_CATEGORIES:
        normalized[key] = _normalize_list(data.get(key))
    return normalized


def _find_keywords(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    found = []
    for keyword in keywords:
        if keyword in lower:
            label = keyword.upper() if len(keyword) <= 4 else keyword.title()
            if label not in found:
                found.append(label)
    return found


def _extract_responsibilities(text: str) -> list[str]:
    lines = [line.strip(" •-\t") for line in text.splitlines() if line.strip()]
    responsibilities = []
    for line in lines:
        lower = line.lower()
        if any(
            marker in lower
            for marker in (
                "responsible",
                "manage",
                "monitor",
                "develop",
                "implement",
                "lead",
                "design",
                "analyze",
                "support",
                "maintain",
                "investigate",
            )
        ):
            if 20 <= len(line) <= 220 and line not in responsibilities:
                responsibilities.append(line)
        if len(responsibilities) >= 8:
            break
    return responsibilities


def _extract_experience(text: str) -> str:
    patterns = [
        r"(\d+\+?\s*(?:to|-)\s*\d+\+?\s*years?[^.\n]*)",
        r"(\d+\+?\s*years?\s+of\s+[^.\n]{5,80})",
        r"((?:entry|mid|senior|lead|principal|junior)[-\s]level[^.\n]*)",
    ]
    lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower, re.IGNORECASE)
        if match:
            return match.group(1).strip().capitalize()
    return "Not specified"


def _extract_job_title(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "Technical Role"

    title_patterns = [
        r"^(?:job title|position|role)\s*[:\-]\s*(.+)$",
        r"^([A-Za-z][A-Za-z0-9 /&,\-]{4,80}(?:analyst|engineer|architect|manager|specialist|consultant|developer|administrator|lead))$",
    ]
    for line in lines[:8]:
        for pattern in title_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return lines[0][:80]


def _fallback_analysis(job_description: str) -> dict[str, Any]:
    text = job_description.strip()
    lower = text.lower()

    required = _find_keywords(text, sum(KEYWORD_MAP.values(), []))[:12]
    preferred = []
    if "preferred" in lower or "nice to have" in lower:
        preferred = _find_keywords(text.split("preferred")[-1], sum(KEYWORD_MAP.values(), []))[:6]

    analysis = {
        "job_title": _extract_job_title(text),
        "experience": _extract_experience(text),
        "required_skills": required,
        "preferred_skills": preferred,
        "responsibilities": _extract_responsibilities(text),
    }
    for category, keywords in KEYWORD_MAP.items():
        analysis[category] = _find_keywords(text, keywords)

    return _normalize_analysis(analysis)


def analyze_job_description(job_description: str) -> dict[str, Any]:
    """Extract structured JD intelligence using OpenAI with heuristic fallback."""
    cleaned = job_description.strip()
    if len(cleaned) < 40:
        raise ValueError("Job description must be at least 40 characters")

    if not client:
        return _fallback_analysis(cleaned)

    user_prompt = f"""Analyze this job description and extract structured hiring intelligence.

Job Description:
{cleaned}
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        data = _extract_json(content)
        return _normalize_analysis(data)
    except Exception:
        return _fallback_analysis(cleaned)


def analysis_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    """Compact summary counts for UI display."""
    skill_groups = {key: analysis.get(key, []) for key in SKILL_CATEGORIES}
    total_skills = sum(len(values) for values in skill_groups.values())
    return {
        "total_extracted_items": total_skills + len(analysis.get("responsibilities", [])),
        "category_counts": {key: len(values) for key, values in skill_groups.items()},
    }
