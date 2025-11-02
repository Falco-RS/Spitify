from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, text, func
from sqlalchemy import text
from ..auth import get_db
from ..models import Job, Node, JobLock


router = APIRouter(prefix="/worker", tags=["worker"])

CPU_OVER = 85.0
MEM_OVER = 80.0
STALE_SEC = 10 


def _node_load_score(n: Node) -> float:
    """Score simple: menor es mejor. None -> 0 (trato preferente a nodos que aún no reportan)."""
    cpu = n.cpu_pct if n.cpu_pct is not None else 0.0
    mem = n.mem_pct if n.mem_pct is not None else 0.0
    # ponderación: 60% CPU, 40% MEM
    return 0.6*cpu + 0.4*mem

def _is_overloaded(n: Node) -> bool:
    return (n.cpu_pct is not None and n.cpu_pct > CPU_OVER) or (n.mem_pct is not None and n.mem_pct > MEM_OVER)

def _active_nodes(db: Session):
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=STALE_SEC)
    return db.scalars(
        select(Node).where(Node.is_active == True, (Node.last_seen == None) | (Node.last_seen >= cutoff))
    ).all()

def _requeue_queued_from_overloaded(db: Session):
    actives = _active_nodes(db)
    if not actives: 
        return 0
    overloaded_ids = [n.id for n in actives if _is_overloaded(n)]
    if not overloaded_ids:
        return 0
    rows = db.scalars(
        select(Job).where(Job.status == "queued", Job.assigned_node_id.in_(overloaded_ids))
    ).all()
    for j in rows:
        j.assigned_node_id = None
    db.commit()
    return len(rows)

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
    # 0) Nodo existente
    node = db.scalar(select(Node).where(Node.name == node_name))
    if not node:
        raise HTTPException(404, "Nodo no registrado")

    # 1) Si el nodo está sobrecargado, no asignar trabajo
    if _is_overloaded(node):
        return {"job": None, "reason": "overloaded"}

    # 2) Re-enfila jobs 'queued' asignados a nodos sobrecargados
    _requeue_queued_from_overloaded(db)

    # 3) Least-loaded: calcular score y comparar contra el mínimo en nodos activos
    actives = _active_nodes(db)
    if actives:
        scores = [(n.id, _node_load_score(n)) for n in actives]
        min_score = min(s for _, s in scores)
        my_score = _node_load_score(node)
        # margen para evitar vibraciones
        EPS = 1e-3
        if my_score > min_score + EPS:
            # no soy el menor; cedo turno
            return {"job": None, "reason": "not-least-loaded", "my_score": my_score, "min_score": min_score}

    # 4) Tomar un trabajo: si hay 'queued' sin asignación o asignados a mí
    rid = db.execute(TAKE_ONE_SQL, {"node_id": node.id}).scalar()
    if not rid:
        return {"job": None}

    job = db.scalar(select(Job).where(Job.id == rid))
    # Auditoría: lock
    jl = JobLock(job_id=job.id, node_id=node.id)
    db.add(jl); db.commit()

    return {"job": {"id": job.id, "type": job.type, "payload": job.payload}}

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
