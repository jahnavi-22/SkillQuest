
# SkillQuest - AI Resume Reviewer + Ranker
<img width="1440" height="900" alt="Screenshot 2026-04-17 at 2 53 40 AM" src="https://github.com/user-attachments/assets/f1d0639c-471e-4225-bacb-b54f90a7e27c" />


## Overview
The AI Resume Ranker is a full-stack application designed to help recruiters and job seekers efficiently evaluate resumes against job descriptions using AI-powered scoring and ranking.

It consists of three main components:

- **Backend (Java Spring Boot):**  
  This REST API service manages core application logic, including receiving resume files and job descriptions, parsing content, communicating with the ML service for scoring, and returning ranked results to the frontend.

- **ML Service (Python FastAPI):**  
  An **orchestrator + specialized sub-agents** pipeline that evaluates each resume against the job
  description. Instead of one large LLM prompt, the work is split into focused, independently testable
  steps, and the scoring math is moved out of the LLM into **deterministic embedding-based matching** so
  scores are reproducible and auditable. See [ML Service Architecture](#ml-service-architecture).

- **Frontend (React.js):**  
  A user-friendly web interface that allows users to upload resumes and job descriptions, view ranked results, and get detailed feedback on skills matched or missing in the resumes.

These components work together by communicating via REST APIs. The separation allows the ML service to evolve independently with new AI models, while the backend handles data processing and security, and the frontend focuses on a smooth user experience.

---

## Prerequisites

- Java 17 installed and configured
- Python 3.11 installed
- Node.js and npm installed (for frontend)  
- Gradle wrapper included in backend (`./gradlew`)

---

## Backend Setup

1. Open a terminal and navigate to the backend directory: cd backend
2. Build the backend: ./gradlew clean build
3. Run the backend service: ./gradlew bootRun


The backend service will start (default port 8080).

---

## ML Service Setup

1. Open a terminal and navigate to the ml-service directory: cd ml-service
2. Create a Python virtual environment: python3 -m venv venv
3. Activate the virtual environment: source venv/bin/activate
4. Install the required Python packages: pip install -r requirements.txt
5. Create a `.env` file in `ml-service/` with your OpenAI credentials (this file is git-ignored):
   ```
   OPENAI_API_KEY=sk-...
   # optional overrides (defaults shown):
   # SKILLQUEST_LLM_MODEL=gpt-5.6-luna
   # SKILLQUEST_EMBED_MODEL=text-embedding-3-small
   # SKILLQUEST_MATCH_THRESHOLD=0.62
   ```
6. Start the ML service: uvicorn main:app --reload

The ML service will start at `http://127.0.0.1:8000`.

---

## Frontend Setup

1. Open a terminal and navigate to the frontend directory: cd frontend
2. Install dependencies: npm install
3. Start the frontend development server: npm start
 
The React app will run at http://localhost:3000.

---



---

## ML Service Architecture

The ML service is an **orchestrator that delegates to specialized sub-agents**, rather than a single
mega-prompt. Each resume flows through four focused steps; the JD is parsed once and reused.

```
Job Description ──► Extractor (JD)  ─────────────► required skills, tagged must-have / nice-to-have
                                                            │
   each resume (run concurrently):                          ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  Extractor (resume)  ─► normalized skills + structured data (LLM)          │
   │  Matcher             ─► embedding cosine similarity → score (NO LLM)       │
   │  Assessor            ─► seniority / trajectory / ATS / highlights (LLM)    │
   │  Verifier            ─► hallucinated-skill check + prompt-injection screen │
   └──────────────────────────────────────────────────────────────────────────┘
                                                            │
                                                            ▼
                                   Orchestrator assembles + ranks by score
```

### Components (`ml-service/`)
- `llm.py` — single model abstraction. Default model **GPT-5.6 Luna** (cheapest/fastest OpenAI tier,
  built for high-volume well-defined work); swappable via `SKILLQUEST_LLM_MODEL`. Uses native JSON mode.
- `embeddings.py` — **`text-embedding-3-small`** + cosine helpers. No local torch/sentence-transformers,
  so the service stays lightweight to deploy.
- `agents/extractor.py` — turns resume/JD text into clean, **normalized** skill lists.
- `agents/matcher.py` — **deterministic** scoring: for each JD skill, best cosine similarity to any
  resume skill; overall score is the importance-weighted mean (must-have = 1.0, nice-to-have = 0.5).
- `agents/assessor.py` — qualitative reads that embeddings can't do.
- `agents/verifier.py` — guardrail: flags skills unsupported by the resume text, and screens resume
  text for prompt-injection attempts (resumes are untrusted input).
- `orchestrator.py` — coordinates the sub-agents, caches per `(jd, resume)`, ranks results.

### Key design decisions
- **Scoring math lives in embeddings, not the LLM.** The score is reproducible, auditable, and not
  manipulable by instructions embedded in a resume. Every score ships with a per-skill `scoreBreakdown`
  (which resume skill matched each JD skill, at what similarity) for explainability.
- **Why not KeyBERT?** An earlier version used KeyBERT + RAKE for unsupervised keyword extraction. It
  surfaced noise, never normalized synonyms (React.js / ReactJS / React), and used a brittle hard
  similarity threshold. The current design lets the LLM do *extraction* (which it's good at) and uses
  soft, importance-weighted embedding similarity for *matching* (reproducible, no arbitrary cutoff).
- **Guardrail by default.** Prompt-injection screening + hallucinated-skill checks run on every resume.

### Eval harness (`ml-service/eval/`)
Because "it feels right" is not a quality bar, the pipeline ships with an eval:

```bash
cd ml-service
python eval/metrics.py     # offline unit tests of the metric math (no API key)
python eval/run_eval.py    # full eval over eval/dataset.json (needs OPENAI_API_KEY)
```

It reports, against a labeled dataset:
- **Ranking quality** — Kendall's tau + NDCG vs. human gold rankings
- **Skill matching** — precision / recall / F1 vs. expected skills
- **Score stability** — std-dev of a resume's score across repeated runs
- **Guardrail** — prompt-injection detection accuracy (runs offline)

Add your own labeled cases to `eval/dataset.json` to calibrate the match threshold and compare models.

> The pre-refactor single-prompt implementation is kept at `ml-service/extractor.py` for reference.
