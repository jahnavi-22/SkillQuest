from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ResumeRequest(BaseModel):
    jobId: str
    jobDescription: str = Field(..., min_length=10, description="Job description cannot be empty.")
    resumeTexts: List[str] = Field(..., description="Must provide at least one resume.")
    resumeNames: Optional[List[str]] = None


class ResumeResponse(BaseModel):
    name: str
    score: float
    rank: int
    total: int
    topScores: List[float]

    matchedSkills: List[str]
    missingSkills: List[str]

    summary: str
    education: List[str]
    experiences: List[str]
    skills: List[str]
    certifications: List[str]
    projects: List[str]

    experienceRelevanceScore: float
    seniorityLevel: str
    careerTrajectory: str

    experienceHighlights: List[str]
    impactHighlights: List[str]
    projectHighlights: List[str]

    atsCompatibilityScore: float

    contact: Dict[str, Optional[str]]

    scoreBreakdown: List[Dict[str, Any]] = []

    verification: Dict[str, Any] = {}