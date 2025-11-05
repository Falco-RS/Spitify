# services/api_client.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
import requests
import mimetypes
from pathlib import Path

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))

@dataclass
class ApiClient:
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    _token: Optional[str] = None

    # ---------- helpers ----------
    def _auth_header(self) -> Dict[str, str]:
        self._ensure_token()
        return {"Authorization": f"Bearer {self._token}"}

    def _ensure_token(self):
        if not self._token:
            raise RuntimeError("No token. Haz login primero.")

    @property
    def token(self) -> Optional[str]:
        return self._token

    def logout(self):
        self._token = None

    # ---------- login ----------
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Intenta primero JSON {email, password}.
        Si el backend usa OAuth2PasswordRequestForm, cae a form {username, password}.
        """
        url = f"{self.base_url}/auth/login"

        # 1) intento JSON con email/password (lo que te funcionaba antes)
        resp = requests.post(url, json={"email": email, "password": password}, timeout=self.timeout)
        if resp.status_code == 200:
            data = resp.json()
            self._token = data.get("access_token")
            return data

        # 2) si el backend usa form (OAuth2PasswordRequestForm)
        if resp.status_code in (415, 422):
            resp2 = requests.post(
                url,
                data={"username": email, "password": password},  # username= email
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
            )
            if resp2.status_code == 200:
                data = resp2.json()
                self._token = data.get("access_token")
                return data
            else:
                try:
                    detail = resp2.json().get("detail", resp2.text)
                except Exception:
                    detail = resp2.text
                raise RuntimeError(f"Login failed (form): {resp2.status_code} {detail}")

        # 3) cualquier otro error del primer intento
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Login failed: {resp.status_code} {detail}")

    # ---------- /me ----------
    def get_me(self) -> Dict[str, Any]:
        url = f"{self.base_url}/me"
        resp = requests.get(url, headers=self._auth_header(), timeout=self.timeout)
        if resp.status_code != 200:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise RuntimeError(f"/me failed: {resp.status_code} {detail}")
        return resp.json()

    # ---------- register ----------
    def register(self, username: str, email: str, password: str, role: str = "user") -> Dict[str, Any]:
        """
        Usa la ruta documentada /auth/register.
        Si da 404, probablemente el path sea otro (p.ej. /users/register).
        """
        url = f"{self.base_url}/auth/register"
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "role": role,
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        if resp.status_code in (200, 201):
            return resp.json()

        # Si no existe la ruta, reporta claro para que corrijamos el prefijo
        if resp.status_code == 404:
            raise RuntimeError(
                "Register 404: Verifica el path real en /docs (¿/register, /users/register o distinto prefijo?)"
            )

        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Register failed: {resp.status_code} {detail}")

    # ---------- upload media ----------

    def upload_media(self, file_path: str) -> dict:
        """
        Sube un archivo al backend (multipart/form-data).
        Requiere self._token (JWT).
        Devuelve JSON del media: { id, rel_path, size, mime, sha256, ... }
        """
        self._ensure_token()

        url = f"{self.base_url}/media/upload"
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise RuntimeError("Archivo no existe.")

        mime, _ = mimetypes.guess_type(str(p))
        mime = mime or "application/octet-stream"

        headers = self._auth_header()  # Authorization: Bearer ...
        # IMPORTANTE: no pongas Content-Type manual aquí; 'requests' lo arma con boundary
        with p.open("rb") as f:
            files = {"file": (p.name, f, mime)}
            resp = requests.post(url, headers=headers, files=files, timeout=self.timeout)

        if resp.status_code not in (200, 201):
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            if resp.status_code in (401, 403):
                raise RuntimeError("No autorizado. Inicia sesión.")
            raise RuntimeError(f"Upload failed: {resp.status_code} {detail}")

        return resp.json()
    
    # ---- STREAM: descarga parcial (bytes start-end, ambos inclusivos) ----
    def stream_range(self, media_id: int, start: int = 0, end: Optional[int] = None) -> Tuple[bytes, Dict[str, str], int]:
        self._ensure_token()
        url = f"{self.base_url}/media/{media_id}/stream"
        rng = f"bytes={start}-" if end is None else f"bytes={start}-{end}"
        headers = self._auth_header() | {"Range": rng}
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        if resp.status_code not in (200, 206):
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise RuntimeError(f"Stream failed: {resp.status_code} {detail}")
        return resp.content, {k.lower(): v for k, v in resp.headers.items()}, resp.status_code

    # ---- DOWNLOAD: streaming por chunks a archivo destino, con progreso opcional ----
    def download_media(self, media_id: int, dest_path: Path, chunk_mb: int = 4, progress_cb=None) -> Path:
        """
        Descarga completo con JWT: GET /media/{id}/stream
        usa stream=True para no cargar todo en RAM.
        progress_cb(total_bytes, downloaded_bytes) si lo deseas para UI.
        """
        self._ensure_token()
        url = f"{self.base_url}/media/{media_id}/stream"
        headers = self._auth_header()
        with requests.get(url, headers=headers, timeout=self.timeout, stream=True) as r:
            if r.status_code not in (200, 206):
                try:
                    detail = r.json().get("detail", r.text)
                except Exception:
                    detail = r.text
                if r.status_code in (401, 403):
                    raise RuntimeError("No autorizado. Inicia sesión.")
                raise RuntimeError(f"Download failed: {r.status_code} {detail}")

            # Tamaño (si está disponible vía Content-Length o Content-Range)
            total = None
            cl = r.headers.get("Content-Length")
            if cl and cl.isdigit():
                total = int(cl)
            else:
                cr = r.headers.get("Content-Range")
                # ej: "bytes 0-1048575/7340032"
                if cr and "/" in cr:
                    try:
                        total = int(cr.split("/")[-1])
                    except:  # no pasa nada
                        pass

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            chunk_size = max(1024, int(chunk_mb * 1024 * 1024))
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        try:
                            progress_cb(total, downloaded)
                        except:
                            pass
        return dest_path
    
    # ----------  compartir ----------
    # --- SHARE: crear token público/expirable ---
    def create_share(self, media_id: int, scope: str = "public", minutes_valid: int = 30) -> Dict[str, Any]:
        """
        POST /media/{id}/share
        Body esperado por tu backend:
        {"scope": "public", "minutes_valid": 30}
        Devuelve (ej.):
        {"id": 1, "media_id": 1, "share_token": "...", "scope": "public",
        "expires_at": "2025-11-04T22:11:49.651803", "created_at": "..."}
        """
        self._ensure_token()
        url = f"{self.base_url}/media/{media_id}/share"
        payload = {"scope": scope, "minutes_valid": minutes_valid}
        resp = requests.post(url, headers=self._auth_header(), json=payload, timeout=self.timeout)
        if resp.status_code not in (200, 201):
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            if resp.status_code in (401, 403):
                raise RuntimeError("No autorizado para compartir este recurso.")
            if resp.status_code == 404:
                raise RuntimeError("Media no encontrado.")
            raise RuntimeError(f"Share failed: {resp.status_code} {detail}")
        return resp.json()


    # --- URL builder: streaming con token por query (?share=TOKEN) ---
    def build_share_stream_url(self, media_id: int, token: str) -> str:
        """
        Construye una URL de streaming que pasa el token por query:
        GET /media/{id}/stream?share=<TOKEN>
        Útil si quieres usar el mismo endpoint de stream con verificación de share.
        """
        return f"{self.base_url}/media/share/{token}"


    # --- URL builder: acceso público por ruta (el de tu backend actual) ---
    def build_public_share_url(self, token: str) -> str:
        """
        Construye la URL pública expuesta por tu backend:
        GET /media/share/<TOKEN>
        """
        return f"{self.base_url}/media/share/{token}"


    # --- Descargar por share público (sin JWT), con soporte de Range opcional ---
    def download_share(self, token: str, dest_path: str | Path, range_bytes: str | None = None) -> Dict[str, Any]:
        """
        Descarga el recurso compartido:
        GET /media/share/<TOKEN>
        - dest_path: ruta de salida (str o Path)
        - range_bytes: ej. 'bytes=0-1048575' para parcial (opcional)
        Retorna: {'ok': True, 'path': Path, 'status': int, 'bytes': int}
        """
        url = self.build_public_share_url(token)
        headers = {}
        if range_bytes:
            headers["Range"] = range_bytes

        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with requests.get(url, headers=headers, stream=True, timeout=self.timeout) as r:
            if r.status_code not in (200, 206):
                try:
                    detail = r.json()
                except Exception:
                    detail = r.text
                raise RuntimeError(f"Share GET failed [{r.status_code}]: {detail}")

            total = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)

        return {"ok": True, "path": dest_path, "status": r.status_code, "bytes": total}

    # services/api_client.py (añadir)
    def create_job(self, job_type: str, payload: dict) -> dict:
        self._ensure_token()
        url = f"{self.base_url}/jobs"
        body = {"type": job_type, "payload": payload}
        r = requests.post(url, json=body, headers=self._auth_header(), timeout=self.timeout)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Create job failed [{r.status_code}]: {r.text}")
        return r.json()

    def get_job_status(self, job_id: int) -> dict:
        self._ensure_token()
        url = f"{self.base_url}/jobs/{job_id}"
        r = requests.get(url, headers=self._auth_header(), timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"Get job failed [{r.status_code}]: {r.text}")
        return r.json()

     # ---------- Monitor/Dashboard ----------
    def monitor_nodes(self) -> dict:
        self._ensure_token()
        url = f"{self.base_url}/monitor/nodes"
        r = requests.get(url, headers=self._auth_header(), timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"/monitor/nodes failed: {r.status_code} {r.text}")
        return r.json()

    def monitor_jobs(self, limit: int | None = None) -> dict:
        self._ensure_token()
        url = f"{self.base_url}/monitor/jobs"
        params = {"limit": limit} if limit else None
        r = requests.get(url, headers=self._auth_header(), params=params, timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"/monitor/jobs failed: {r.status_code} {r.text}")
        return r.json()

    def monitor_sessions(self) -> dict:
        self._ensure_token()
        url = f"{self.base_url}/monitor/sessions"
        r = requests.get(url, headers=self._auth_header(), timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"/monitor/sessions failed: {r.status_code} {r.text}")
        return r.json()

    def monitor_summary(self) -> dict:
        self._ensure_token()
        url = f"{self.base_url}/monitor/summary"
        r = requests.get(url, headers=self._auth_header(), timeout=self.timeout)
        if r.status_code != 200:
            raise RuntimeError(f"/monitor/summary failed: {r.status_code} {r.text}")
        return r.json()
        # ---------- Helpers genéricos ----------
    def _get_json(self, path: str, params: dict | None = None) -> tuple[int, dict | None, str]:
        """GET con JWT. Devuelve (status, json|None, text). No lanza en 404."""
        self._ensure_token()
        url = f"{self.base_url}{path}"
        r = requests.get(url, headers=self._auth_header(), params=params, timeout=self.timeout)
        try:
            data = r.json()
        except Exception:
            data = None
        return r.status_code, data, r.text

    # ---------- Monitor/Dashboard ----------
    def monitor_nodes(self) -> dict | list:
        status, data, txt = self._get_json("/monitor/nodes")
        if status == 200:
            return data
        if status == 404:
            # endpoint no disponible
            return {"_unavailable": True}
        raise RuntimeError(f"/monitor/nodes failed: {status} {txt}")

    def monitor_jobs(self, limit: int | None = None) -> dict | list:
        params = {"limit": limit} if limit else None
        status, data, txt = self._get_json("/monitor/jobs", params=params)
        if status == 200:
            return data
        if status == 404:
            return {"_unavailable": True}
        raise RuntimeError(f"/monitor/jobs failed: {status} {txt}")

    def monitor_sessions(self) -> dict | list:
        status, data, txt = self._get_json("/monitor/sessions")
        if status == 200:
            return data
        if status == 404:
            return {"_unavailable": True}
        raise RuntimeError(f"/monitor/sessions failed: {status} {txt}")

    def monitor_summary(self) -> dict:
        status, data, txt = self._get_json("/monitor/summary")
        if status == 200:
            return data
        if status == 404:
            # No existe en tu API: devolvemos marca para que el UI calcule
            return {"_unavailable": True}
        raise RuntimeError(f"/monitor/summary failed: {status} {txt}")

    def monitor_summary_best_effort(self) -> dict:
        """
        Intenta /monitor/summary; si no existe,
        compone un resumen a partir de /monitor/nodes y /monitor/jobs.
        """
        sm = self.monitor_summary()
        if not isinstance(sm, dict) or sm.get("_unavailable"):
            # Fallback: construimos
            nodes_payload = self.monitor_nodes()
            jobs_payload  = self.monitor_jobs(limit=200)

            # Nodos (acepta lista o {"items":[...]})
            nodes_items = nodes_payload if isinstance(nodes_payload, list) else nodes_payload.get("items", [])
            active = len(nodes_items)
            scores = []
            overloaded = 0
            for n in nodes_items:
                try:
                    scores.append(float(n.get("score", 0.0)))
                except Exception:
                    pass
                if bool(n.get("overloaded", False)):
                    overloaded += 1
            least_score = min(scores) if scores else None

            # Jobs (lista o {"items":[...]})
            jobs_items = jobs_payload if isinstance(jobs_payload, list) else jobs_payload.get("items", [])
            counts = {"queued": 0, "running": 0, "done": 0, "failed": 0}
            for j in jobs_items:
                st = (j.get("status") or "").lower()
                if st in counts:
                    counts[st] += 1
                else:
                    counts.setdefault(st, 0)
                    counts[st] += 1

            return {
                "jobs_by_status": counts,
                "nodes": {
                    "active": active,
                    "least_score": least_score,
                    "overloaded": overloaded
                },
                "_composed": True
            }
        return sm
