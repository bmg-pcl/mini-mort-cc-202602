"""FastAPI backend for receiving form submissions."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Form Renderer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store (swap for a database in production)
_submissions: dict[str, dict[str, Any]] = {}

SUBMISSIONS_DIR = Path(__file__).resolve().parent.parent / "submissions"
SUBMISSIONS_DIR.mkdir(exist_ok=True)


class FormSubmission(BaseModel):
    form_id: str = "default"
    responses: dict[str, Any]


class SubmissionResponse(BaseModel):
    id: str
    form_id: str
    submitted_at: str
    responses: dict[str, Any]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/submit", response_model=SubmissionResponse)
def submit_form(submission: FormSubmission):
    sub_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": sub_id,
        "form_id": submission.form_id,
        "submitted_at": now,
        "responses": submission.responses,
    }
    _submissions[sub_id] = record

    # Persist to disk as well
    out_path = SUBMISSIONS_DIR / f"{sub_id}.json"
    out_path.write_text(json.dumps(record, indent=2))

    return record


@app.get("/submissions", response_model=list[SubmissionResponse])
def list_submissions():
    return list(_submissions.values())


@app.get("/submissions/{sub_id}", response_model=SubmissionResponse)
def get_submission(sub_id: str):
    if sub_id not in _submissions:
        raise HTTPException(status_code=404, detail="Submission not found")
    return _submissions[sub_id]


@app.get("/form")
def get_default_form():
    """Serve the default sample survey.js form definition."""
    form_path = Path(__file__).resolve().parent.parent / "forms" / "sample_survey.json"
    if not form_path.exists():
        raise HTTPException(status_code=404, detail="Default form not found")
    return json.loads(form_path.read_text())
