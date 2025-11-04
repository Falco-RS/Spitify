from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy import text
from ..auth import get_db
from ..models import Job, Node, JobLock

router = APIRouter(prefix="/worker", tags=["worker"])

# SELECT ... FOR UPDATE SKIP LOCKED con SQLAlchemy 2.0:
# Usamos texto crudo porque es claro y portatil.
TAKE_ONE_SQL = text("""
WITH cte AS (
  SELECT id FROM jobs
  WHERE status = 'queued'
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE jobs j
SET status = 'running',
    assigned_node_id = :node_id,
    started_at = now()
FROM cte
WHERE j.id = cte.id
RETURNING j.id
""")

@router.post("/next_job")
def next_job(node_name: str, db: Session = Depends(get_db)):
    node = db.scalar(select(Node).where(Node.name == node_name))
    if not node:
        raise HTTPException(404, "Nodo no registrado")
    rid = db.execute(TAKE_ONE_SQL, {"node_id": node.id}).scalar()
    if not rid:
        return {"job": None}
    job = db.scalar(select(Job).where(Job.id == rid))
    # registra lock (opcional)
    jl = JobLock(job_id=job.id, node_id=node.id)
    db.add(jl); db.commit()
    return {"job": {
        "id": job.id, "type": job.type, "payload": job.payload
    }}

@router.post("/jobs/{jid}/progress")
def progress(jid: int, progress: float, db: Session = Depends(get_db)):
    j = db.scalar(select(Job).where(Job.id == jid))
    if not j:
        raise HTTPException(404, "Job no encontrado")
    if j.status != "running":
        raise HTTPException(400, "Job no está en ejecución")
    j.progress = max(0.0, min(100.0, progress))
    db.commit()
    return {"ok": True}

@router.post("/jobs/{jid}/done")
def done(jid: int, db: Session = Depends(get_db)):
    j = db.scalar(select(Job).where(Job.id == jid))
    if not j:
        raise HTTPException(404, "Job no encontrado")
    j.status = "done"
    j.progress = 100.0
    j.finished_at = datetime.utcnow()
    db.commit()
    return {"ok": True}

@router.post("/jobs/{jid}/fail")
def fail(jid: int, error: str, db: Session = Depends(get_db)):
    j = db.scalar(select(Job).where(Job.id == jid))
    if not j:
        raise HTTPException(404, "Job no encontrado")
    j.status = "failed"
    j.error = error[:8000]
    j.finished_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
