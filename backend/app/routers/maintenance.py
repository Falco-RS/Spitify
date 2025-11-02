# app/routers/maintenance.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..auth import get_db, require_roles
from ..models import Job, Node

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

CPU_OVER = 85.0
MEM_OVER = 80.0

def _is_overloaded(n: Node) -> bool:
    return (n.cpu_pct is not None and n.cpu_pct > CPU_OVER) or (n.mem_pct is not None and n.mem_pct > MEM_OVER)

@router.post("/rebalance-queued")
def rebalance_queued(db: Session = Depends(get_db), admin=Depends(require_roles(["admin"]))):
    nodes = db.scalars(select(Node).where(Node.is_active == True)).all()
    overloaded = [n.id for n in nodes if _is_overloaded(n)]
    if not overloaded:
        return {"requeued": 0}
    jobs = db.scalars(
        select(Job).where(Job.status == "queued", Job.assigned_node_id.in_(overloaded))
    ).all()
    for j in jobs:
        j.assigned_node_id = None
    db.commit()
    return {"requeued": len(jobs)}
