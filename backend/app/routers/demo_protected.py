from fastapi import APIRouter, Depends
from ..auth import require_user, require_roles

router = APIRouter(prefix="/demo", tags=["demo"])

@router.get("/ping-auth")
def ping_auth(user=Depends(require_user)):
    return {"ok": True, "msg": f"Hola {user[0].email}, estás autenticado."}

@router.get("/ping-admin")
def ping_admin(user=Depends(require_roles(["admin"]))):
    return {"ok": True, "msg": f"Hola admin {user.email}, tienes acceso."}
