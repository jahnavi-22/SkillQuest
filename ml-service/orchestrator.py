"""Orchestrator.

Coordinates the specialized sub-agents. This is the "orchestrator + sub-agents"
pattern replacing the old single mega-prompt:

    JD --> extract_jd (once)
    each resume (concurrently):
        extract_resume  -> structured data + normalized skills
        match_skills    -> deterministic embedding score + breakdown
        assess          -> seniority / trajectory / ATS / highlights
        verify          -> hallucination + prompt-injection guardrail
    -> assemble, sort by score, assign ranks

Each resume's full result is cached on (jd_text, resume_text) so repeated
requests are cheap. The score is deterministic, so caching is safe.
"""

import asyncio
import hashlib
import logging
import sys
import time
from typing import Any, Dict, List, Optional

from cachetools import LRUCache

from agents import assessor, extractor, matcher, verifier

logger = logging.getLogger("skillquest")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(asctime)s [skillquest] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

_cache: LRUCache = LRUCache(maxsize=500)
_jd_cache: LRUCache = LRUCache(maxsize=100)


def _key(*parts: str) -> str:
    return hashlib.sha256("::".join(p.strip() for p in parts).encode("utf-8")).hexdigest()


async def _timed(label: str, tag: str, coro):
    """Await a coroutine and log how long it took. For latency profiling."""
    t0 = time.time()
    result = await coro
    logger.info("%s timing: %s took %.2fs", tag, label, time.time() - t0)
    return result


async def rank_resumes(
    jd_text: str,
    resume_texts: List[str],
    resume_names: Optional[List[str]] = None,
    job_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Run the full pipeline over all resumes and return them ranked (best first)."""
    resume_names = resume_names or [None] * len(resume_texts)
    started = time.time()
    logger.info("job=%s start: %d resume(s)", job_id, len(resume_texts))

    jd_task = asyncio.create_task(
        _timed("extract_jd", f"job={job_id}", _extract_jd_cached(jd_text))
    )

    tasks = [
        _process_one(jd_text, jd_task, text, resume_names[i] if i < len(resume_names) else None, job_id)
        for i, text in enumerate(resume_texts)
    ]
    results = await asyncio.gather(*tasks)

    jd_skills = await jd_task
    logger.info("job=%s JD parsed: %d required skills", job_id, len(jd_skills))

    ranked = sorted(results, key=lambda r: r["score"], reverse=True)
    total = len(ranked)
    top_scores = [r["score"] for r in ranked[: min(5, total)]]
    for rank, r in enumerate(ranked, start=1):
        r["rank"] = rank
        r["total"] = total
        r["topScores"] = top_scores
        if not r.get("name"):
            r["name"] = f"Resume {rank}"

    logger.info("job=%s done: ranked %d resume(s) in %.2fs", job_id, total, time.time() - started)
    return ranked


async def _extract_jd_cached(jd_text: str) -> List[Dict[str, str]]:
    key = _key("jd", jd_text)
    if key in _jd_cache:
        return _jd_cache[key]
    jd = await extractor.extract_jd(jd_text)
    skills = jd.get("requiredSkills", [])
    _jd_cache[key] = skills
    return skills


async def _process_one(
    jd_text: str,
    jd_task: "asyncio.Task",
    resume_text: str,
    name_hint: Optional[str],
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    label = name_hint or "resume"
    tag = f"job={job_id} resume={label}"
    started = time.time()

    cache_key = _key("resume", jd_text, resume_text)
    if cache_key in _cache:
        result = dict(_cache[cache_key])
        if name_hint and not result.get("name"):
            result["name"] = name_hint
        logger.info("%s cache hit", tag)
        return result

    resume = await _timed("extract_resume", tag, extractor.extract_resume(resume_text))
    resume_skills = resume.get("skills", [])
    logger.info("%s extracted %d skills", tag, len(resume_skills))

    jd_skills = await jd_task

    # Matcher (embeddings) and assessor (LLM) are independent -> run concurrently.
    match_task = asyncio.create_task(_timed("match_skills", tag, matcher.match_skills(resume_skills, jd_skills)))
    assess_task = asyncio.create_task(_timed("assess", tag, assessor.assess(resume, jd_text)))
    match_res, assess_res = await asyncio.gather(match_task, assess_task)
    logger.info("%s matched + assessed (score=%.2f)", tag, match_res["score"])

    _verify_t0 = time.time()
    verification = verifier.verify(resume_skills, resume_text)
    logger.info("%s timing: verify took %.2fs", tag, time.time() - _verify_t0)
    if verification["injectionFlags"]:
        logger.info("%s prompt-injection flagged", tag)

    result: Dict[str, Any] = {
        "name": resume.get("name") or name_hint or "",
        "score": match_res["score"],
        "matched": match_res["matched"],
        "missing": match_res["missing"],
        "scoreBreakdown": match_res["breakdown"],
        "summary": resume.get("summary", ""),
        "education": resume.get("education", []),
        "experiences": resume.get("experiences", []),
        "skills": resume_skills,
        "certifications": resume.get("certifications", []),
        "projects": resume.get("projects", []),
        "contact": resume.get("contact", {"email": None, "phone": None, "linkedin": None}),
        "experienceRelevanceScore": assess_res["experienceRelevanceScore"],
        "seniorityLevel": assess_res["seniorityLevel"],
        "careerTrajectory": assess_res["careerTrajectory"],
        "experienceHighlights": assess_res["experienceHighlights"],
        "impactHighlights": assess_res["impactHighlights"],
        "projectHighlights": assess_res["projectHighlights"],
        "atsCompatibilityScore": assess_res["atsCompatibilityScore"],
        "verification": verification,
    }
    _cache[cache_key] = result
    logger.info("%s done (score=%.2f, %.2fs)", tag, match_res["score"], time.time() - started)
    return result



