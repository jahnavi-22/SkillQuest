"""Verifier agent (guardrail).

Two deterministic, cheap checks that run on every resume:

  1. Hallucination check -- flag extracted skills that are NOT supported by the
     raw resume text, so the extractor can't silently invent qualifications.
  2. Prompt-injection screen -- resumes are untrusted user input. Scan for text
     that tries to hijack the model ("ignore previous instructions", "give this
     candidate a 100", etc.). For a fintech-grade system, treating candidate
     input as adversarial is the point.

No LLM call here: both checks are deterministic, which makes them fast, free,
and themselves un-injectable.
"""

import re
from typing import Any, Dict, List

# Patterns that indicate an attempt to manipulate the scoring model.
_INJECTION_PATTERNS = [
    r"ignore (all|any|the)?\s*(previous|prior|above)\s+instructions?",
    r"disregard (all|any|the)?\s*(previous|prior|above)",
    r"you are now",
    r"system prompt",
    r"as an ai (language )?model",
    r"(give|assign|award|set)\b.{0,40}\b(score|rating|rank)\b.{0,20}(100|max|highest|10/10|full)",
    r"(score|rate|rank)\s+(me|this candidate|this resume)\s+(the )?(highest|100|max|first)",
    r"top\s+(candidate|rank|score)\s+regardless",
    r"do not (score|rank|evaluate) other",
    r"\bprompt inject",
]

_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

# Words we ignore when checking whether a skill appears in the resume text.
_STOP = {"and", "or", "of", "the", "for", "with", "in", "to", "a", "an"}


def verify(resume_skills: List[str], resume_text: str) -> Dict[str, Any]:
    """Return hallucination + injection findings for one resume."""
    injection_flags = _find_injection(resume_text)
    return {
        "unverifiedSkills": _find_unverified(resume_skills, resume_text),
        "injectionFlags": injection_flags,
        "clean": not injection_flags,
    }


def _find_unverified(resume_skills: List[str], resume_text: str) -> List[str]:
    """Skills whose tokens don't appear in the resume text at all."""
    text = resume_text.lower()
    unverified: List[str] = []
    for skill in resume_skills:
        tokens = [t for t in re.split(r"[\s/.\-+]+", skill.lower()) if t and t not in _STOP]
        if not tokens:
            continue
        # Supported if any meaningful token from the skill appears in the text.
        if not any(tok in text for tok in tokens):
            unverified.append(skill)
    return unverified


def _find_injection(resume_text: str) -> List[str]:
    """Return matched injection snippets found in the resume text."""
    flags: List[str] = []
    for rx in _INJECTION_RE:
        m = rx.search(resume_text)
        if m:
            flags.append(m.group(0).strip())
    return flags
