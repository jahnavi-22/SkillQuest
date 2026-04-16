
# AI Resume Ranker
<img width="1440" height="900" alt="Screenshot 2026-04-17 at 2 53 40 AM" src="https://github.com/user-attachments/assets/f1d0639c-471e-4225-bacb-b54f90a7e27c" />


## Overview
The AI Resume Ranker is a full-stack application designed to help recruiters and job seekers efficiently evaluate resumes against job descriptions using AI-powered scoring and ranking.

It consists of three main components:

- **Backend (Java Spring Boot):**  
  This REST API service manages core application logic, including receiving resume files and job descriptions, parsing content, communicating with the ML service for scoring, and returning ranked results to the frontend.

- **ML Service (Python FastAPI):**  
  This microservice leverages advanced natural language processing and machine learning techniques to analyze the textual content of resumes and job descriptions. It extracts relevant keywords, computes similarity scores, and ranks the resumes based on their match to the job requirements.

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
5. Start the ML service: uvicorn app.main:app --reload

The ML service will start at `http://127.0.0.1:8000`.

---

## Frontend Setup

1. Open a terminal and navigate to the frontend directory: cd frontend
2. Install dependencies: npm install
3. Start the frontend development server: npm start
 
The React app will run at http://localhost:3000.

---


