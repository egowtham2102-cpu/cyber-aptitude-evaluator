"""Fisher-Yates randomization and dynamic scenario context generation."""

import random
import secrets
import uuid
from copy import deepcopy
from typing import Any

TECHNICAL_TYPES = {
    "mcq",
    "multi_select",
    "true_false",
    "fill_blank",
    "match_following",
    "code_analysis",
    "terminal_analysis",
    "log_analysis",
    "packet_analysis",
}

OPEN_TYPES = {"scenario", "incident_response", "threat_hunting"}
OBJECTIVE_TYPES = TECHNICAL_TYPES | {"aptitude", "true_false"}
OPTION_TYPES = {
    "mcq",
    "multi_select",
    "true_false",
    "aptitude",
    "code_analysis",
    "terminal_analysis",
    "log_analysis",
    "packet_analysis",
}

BUCKET_TARGETS = {"technical": 14, "scenario": 4, "aptitude": 2}
TOTAL_QUESTIONS = sum(BUCKET_TARGETS.values())


def fisher_yates_shuffle(items: list[Any], rng: random.Random | None = None) -> list[Any]:
    """Return a new list with items shuffled using Fisher-Yates."""
    shuffled = list(items)
    rand = rng or random
    for index in range(len(shuffled) - 1, 0, -1):
        swap_index = rand.randint(0, index)
        shuffled[index], shuffled[swap_index] = shuffled[swap_index], shuffled[index]
    return shuffled


def generation_seed() -> str:
    return f"{uuid.uuid4()}-{secrets.token_hex(8)}"


def random_ipv4(rng: random.Random) -> str:
    while True:
        octets = [rng.randint(1, 223) for _ in range(4)]
        if octets[0] == 10:
            return ".".join(str(o) for o in octets)
        if octets[0] == 172 and 16 <= octets[1] <= 31:
            return ".".join(str(o) for o in octets)
        if octets[0] == 192 and octets[1] == 168:
            return ".".join(str(o) for o in octets)
        if octets[0] not in {127, 0}:
            return ".".join(str(o) for o in octets)


def random_cve(rng: random.Random) -> str:
    year = rng.randint(2019, 2026)
    number = rng.randint(1000, 99999)
    return f"CVE-{year}-{number}"


def random_mac(rng: random.Random) -> str:
    return ":".join(f"{rng.randint(0, 255):02x}" for _ in range(6))


def random_context(rng: random.Random | None = None) -> dict[str, str]:
    rand = rng or random.Random()
    source_ip = random_ipv4(rand)
    dest_ip = random_ipv4(rand)
    while dest_ip == source_ip:
        dest_ip = random_ipv4(rand)
    return {
        "source_ip": source_ip,
        "dest_ip": dest_ip,
        "internal_ip": f"10.{rand.randint(0, 255)}.{rand.randint(0, 255)}.{rand.randint(1, 254)}",
        "cve": random_cve(rand),
        "hostname": f"host-{secrets.token_hex(3)}.corp.local",
        "username": rand.choice(["jsmith", "alee", "kpatel", "mchen", "devans"]),
        "session_id": secrets.token_hex(8),
        "mac_address": random_mac(rand),
    }


def _normalize_option(option: Any) -> str:
    return str(option).strip()


def _shuffle_options(question: dict[str, Any], rng: random.Random) -> None:
    options = [_normalize_option(option) for option in question.get("options") or []]
    if len(options) < 2:
        return

    shuffled = fisher_yates_shuffle(options, rng)
    question["options"] = shuffled

    correct = question.get("correct_answer")
    if isinstance(correct, list):
        normalized = {_normalize_option(item) for item in correct}
        question["correct_answer"] = [option for option in shuffled if option in normalized]
    elif correct is not None:
        question["correct_answer"] = _normalize_option(correct)


def _shuffle_match_pairs(question: dict[str, Any], rng: random.Random) -> None:
    pairs = question.get("match_pairs") or []
    if not pairs:
        return

    right_values = [_normalize_option(pair.get("correct_right") or pair.get("right")) for pair in pairs]
    shuffled_rights = fisher_yates_shuffle([value for value in right_values if value], rng)
    question["match_options"] = shuffled_rights

    cleaned_pairs = []
    for index, pair in enumerate(pairs):
        cleaned_pairs.append(
            {
                "id": pair.get("id") or f"m{index + 1}",
                "left": pair.get("left", ""),
                "correct_right": _normalize_option(pair.get("correct_right") or pair.get("right", "")),
            }
        )
    question["match_pairs"] = cleaned_pairs


def apply_randomization(questions: list[dict[str, Any]], seed: str | None = None) -> list[dict[str, Any]]:
    """Shuffle question order, option order, and reassign sequential IDs."""
    rng = random.Random(seed or generation_seed())
    prepared = deepcopy(questions)

    for question in prepared:
        qtype = question.get("type", "mcq")
        if qtype in OPTION_TYPES:
            _shuffle_options(question, rng)
        if qtype == "match_following":
            _shuffle_match_pairs(question, rng)
        if qtype == "true_false" and not question.get("options"):
            question["options"] = ["True", "False"]

    shuffled = fisher_yates_shuffle(prepared, rng)
    for index, question in enumerate(shuffled, start=1):
        question["id"] = f"q{index}"
    return shuffled
