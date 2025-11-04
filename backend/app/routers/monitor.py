from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..auth import get_db, require_roles
from ..models import Node
from ..schemas import NodeRegisterIn, HeartbeatIn, NodeOut

router = APIRouter(prefix="/monitor", tags=["monitor"])

@router.post("/nodes/register", response_model=NodeOut)
def register_node(data: NodeRegisterIn, db: Session = Depends(get_db)):
    node = db.scalar(select(Node).where(Node.name == data.name))
    if node:
        node.api_url = data.api_url or node.api_url
        db.commit()
        db.refresh(node)
        return node
    node = Node(name=data.name, api_url=data.api_url, last_seen=datetime.utcnow(), is_active=True)
    db.add(node); db.commit(); db.refresh(node)
    return node

@router.post("/nodes/heartbeat")
def heartbeat(data: HeartbeatIn, db: Session = Depends(get_db)):
    node = db.scalar(select(Node).where(Node.name == data.name))
    if not node:
        raise HTTPException(404, "Nodo no registrado")
    node.last_seen = datetime.utcnow()
    node.cpu_pct = data.cpu_pct
    node.mem_pct = data.mem_pct
    node.net_in = data.net_in
    node.net_out = data.net_out
    db.commit()
    return {"ok": True}

@router.get("/nodes", response_model=list[NodeOut])
def list_nodes(db: Session = Depends(get_db), admin=Depends(require_roles(["admin"]))):
    rows = db.scalars(select(Node).order_by(Node.name)).all()
    return rows
