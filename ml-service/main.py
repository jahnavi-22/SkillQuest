from fastapi import FastAPI, HTTPException
from typing import List
from model import ResumeRequest, ResumeResponse
import orchestrator
import openai
import time

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Resume Ranker ML service is running"}


@app.post("/rank", response_model=List[ResumeResponse])
async def rank_resumes(request: ResumeRequest):
    jd = request.jobDescription
    resumes = request.resumeTexts

    if not jd or not jd.strip():
        raise HTTPException(status_code=400, detail="Job description is empty or invalid.")
    if not resumes:
        raise HTTPException(status_code=400, detail="All resumes are empty or invalid.")

    start_time = time.time()

    # Orchestrator runs extract -> match -> assess -> verify per resume and ranks.
    try:
        ranked = await orchestrator.rank_resumes(jd, resumes, request.resumeNames, request.jobId)
    except openai.APIStatusError as e:
        # OpenAI returned an HTTP error (400 bad param, 429 rate limit, etc.).
        # Surface its real status code + message instead of a blank 500.
        message = str(e)
        try:
            if isinstance(e.body, dict):
                message = e.body.get("error", {}).get("message", message)
        except Exception:
            pass
        raise HTTPException(status_code=e.status_code, detail=f"OpenAI {e.status_code}: {message}")
    except openai.APIError as e:
        # Connection/timeout errors from OpenAI (no HTTP status).
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    responses = [
        ResumeResponse(
            name=r["name"],
            score=r["score"],
            rank=r["rank"],
            total=r["total"],
            topScores=r["topScores"],
            matchedSkills=r["matched"],
            missingSkills=r["missing"],
            summary=r.get("summary", ""),
            education=r.get("education", []),
            experiences=r.get("experiences", []),
            skills=r.get("skills", []),
            certifications=r.get("certifications", []),
            projects=r.get("projects", []),
            experienceRelevanceScore=r.get("experienceRelevanceScore", 0.0),
            seniorityLevel=r.get("seniorityLevel", ""),
            careerTrajectory=r.get("careerTrajectory", ""),
            experienceHighlights=r.get("experienceHighlights", []),
            impactHighlights=r.get("impactHighlights", []),
            projectHighlights=r.get("projectHighlights", []),
            atsCompatibilityScore=r.get("atsCompatibilityScore", 0.0),
            contact=r.get("contact", {}),
            scoreBreakdown=r.get("scoreBreakdown", []),
            verification=r.get("verification", {}),
        )
        for r in ranked
    ]

    print(f"Processed {len(resumes)} resumes in {time.time() - start_time:.2f}s")
    return responses
