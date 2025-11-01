from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..auth import get_db, require_roles, require_user
from ..models import Job
from ..schemas import JobCreateIn, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobOut)
def create_job(data: JobCreateIn, db: Session = Depends(get_db), user=Depends(require_user)):
    j = Job(type=data.type, payload=data.payload, status="queued", progress=0.0)
    db.add(j); db.commit(); db.refresh(j)
    return j

@router.get("/{jid}", response_model=JobOut)
def get_job(jid: int, db: Session = Depends(get_db), user=Depends(require_user)):
    j = db.scalar(select(Job).where(Job.id == jid))
    if not j:
        raise HTTPException(404, "Job no encontrado")
    return j
