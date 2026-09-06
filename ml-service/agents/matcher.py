"""Matcher.

Deterministic, embedding-based skill matching. No LLM in the scoring math, so
the score is reproducible and auditable.

Fixes the two things that broke the earlier KeyBERT approach:
  1. It matches clean, LLM-normalized skills (not noisy KeyBERT keywords).
  2. It uses SOFT max-similarity + importance weighting instead of a brittle
     hard 0.75 threshold, so partial matches contribute proportionally.

For each JD skill we take its best (max) cosine similarity to any resume skill.
The overall score is the importance-weighted mean of those similarities,
scaled to 0-100. A JD skill is reported as "matched" (for the human-readable
lists) when its best similarity clears MATCH_THRESHOLD -- but that threshold
only affects the matched/missing lists, not the score. The threshold and
weights are meant to be calibrated by the eval harness.
"""

import os
from typing import Any, Dict, List

from embeddings import embed_texts, cosine

# Calibrated via the eval harness; overridable by env.
MATCH_THRESHOLD = float(os.getenv("SKILLQUEST_MATCH_THRESHOLD", "0.62"))
IMPORTANCE_WEIGHTS = {"must-have": 1.0, "nice-to-have": 0.5}


async def match_skills(
    resume_skills: List[str],
    jd_skills: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Score how well a resume's skills cover a JD's required skills.

    Returns:
        {
          "score": float,              # 0-100, importance-weighted
          "matched": [str],            # JD skills the resume covers
          "missing": [str],            # JD skills it does not
          "breakdown": [ {skill, importance, similarity, bestMatch, matched} ]
        }
    """
    jd_names = [s["skill"] for s in jd_skills]
    if not jd_names:
        return {"score": 0.0, "matched": [], "missing": [], "breakdown": []}

    # Embed JD skills and resume skills in as few calls as possible.
    jd_vecs = await embed_texts(jd_names)
    resume_vecs = await embed_texts(resume_skills) if resume_skills else []

    breakdown: List[Dict[str, Any]] = []
    matched: List[str] = []
    missing: List[str] = []
    weighted_sum = 0.0
    weight_total = 0.0

    for jd_skill, jd_vec in zip(jd_skills, jd_vecs):
        name = jd_skill["skill"]
        importance = jd_skill.get("importance", "must-have")
        weight = IMPORTANCE_WEIGHTS.get(importance, 1.0)

        best_sim = 0.0
        best_match = None
        for r_name, r_vec in zip(resume_skills, resume_vecs):
            sim = cosine(jd_vec, r_vec)
            if sim > best_sim:
                best_sim = sim
                best_match = r_name

        is_matched = best_sim >= MATCH_THRESHOLD
        (matched if is_matched else missing).append(name)

        weighted_sum += weight * best_sim
        weight_total += weight

        breakdown.append({
            "skill": name,
            "importance": importance,
            "similarity": round(best_sim, 4),
            "bestMatch": best_match if is_matched else None,
            "matched": is_matched,
        })

    score = round(100.0 * weighted_sum / weight_total, 2) if weight_total else 0.0
    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "breakdown": breakdown,
    }
