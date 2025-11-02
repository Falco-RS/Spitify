# app/routers/monitor_jobs.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..auth import get_db, require_roles
from ..models import Job, Node

router = APIRouter(prefix="/monitor", tags=["monitor"])

@router.get("/summary")
def summary(db: Session = Depends(get_db), admin=Depends(require_roles(["admin"]))):
    # Jobs por estado
    stats = db.execute(select(Job.status, func.count()).group_by(Job.status)).all()
    jobs_by_status = {k: v for k, v in stats}
    total_jobs = sum(jobs_by_status.values()) if jobs_by_status else 0

    # Nodos activos y sobrecargados
    nodes = db.scalars(select(Node).where(Node.is_active == True)).all()
    def score(n: Node):
        cpu = n.cpu_pct if n.cpu_pct is not None else 0.0
        mem = n.mem_pct if n.mem_pct is not None else 0.0
        return 0.6*cpu + 0.4*mem
    nodes_out = [
        {
            "id": n.id, "name": n.name, "last_seen": n.last_seen,
            "cpu_pct": n.cpu_pct, "mem_pct": n.mem_pct,
            "net_in": n.net_in, "net_out": n.net_out,
            "score": score(n),
            "overloaded": (n.cpu_pct and n.cpu_pct > 85) or (n.mem_pct and n.mem_pct > 80)
        }
        for n in nodes
    ]
    least = min((x["score"] for x in nodes_out), default=None)
    overloaded_count = sum(1 for x in nodes_out if x["overloaded"])

    return {
        "jobs": {"total": total_jobs, "by_status": jobs_by_status},
        "nodes": {"count": len(nodes_out), "least_score": least, "overloaded": overloaded_count, "items": nodes_out}
    }

@router.get("/jobs")
def list_jobs(limit: int = 50, db: Session = Depends(get_db), admin=Depends(require_roles(["admin"]))):
    rows = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(min(200, max(1, limit)))).all()
    return [
        {
            "id": j.id, "type": j.type, "status": j.status,
            "progress": j.progress, "assigned_node_id": j.assigned_node_id,
            "created_at": j.created_at, "started_at": j.started_at,
            "finished_at": j.finished_at, "error": j.error
        }
        for j in rows
    ]
