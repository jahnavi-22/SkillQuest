from fastapi import FastAPI, HTTPException
from typing import List
from model import ResumeRequest, ResumeResponse
import orchestrator
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
    ranked = await orchestrator.rank_resumes(jd, resumes, request.resumeNames)

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
