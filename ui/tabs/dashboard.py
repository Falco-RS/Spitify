import tkinter as tk
from tkinter import ttk, messagebox
from ..theme import FONT_H2, PAD

REFRESH_SECS = 3      # auto-refresh
_COOLDOWN_MS = 15000  # si el summary no existe, pausamos 15s solo ese bloque
SHOW_SUMMARY = False

def _mk_tree(parent, cols, widths):
    tv = ttk.Treeview(parent, columns=cols, show="headings", height=8)
    for c, w in zip(cols, widths):
        tv.heading(c, text=c.upper())
        tv.column(c, width=w, anchor="w")
    tv.pack(fill="both", expand=True)
    return tv

def build_dashboard_tab(app, notebook):
    tab = ttk.Frame(notebook, style="TFrame")
    notebook.add(tab, text="Dashboard")
    wrap = ttk.Frame(tab); wrap.pack(fill="both", expand=True, padx=PAD, pady=PAD)

    # --- Resumen ---
    if SHOW_SUMMARY:
        card_sum = ttk.Frame(wrap, style="Card.TFrame"); card_sum.pack(fill="x")
        inner_sum = ttk.Frame(card_sum); inner_sum.pack(fill="x", padx=PAD, pady=PAD)
        ttk.Label(inner_sum, text="Resumen global", font=FONT_H2).pack(anchor="w")
        app.lbl_summary = ttk.Label(inner_sum, text="—", style="Muted.TLabel")
        app.lbl_summary.pack(anchor="w", pady=(4,0))
    else:
        # Para que el resto del código no falle por atributo inexistente
        app.lbl_summary = None

    # --- Nodos ---
    card_nodes = ttk.Frame(wrap, style="Card.TFrame"); card_nodes.pack(fill="x", pady=(8,0))
    inner_nodes = ttk.Frame(card_nodes); inner_nodes.pack(fill="x", padx=PAD, pady=PAD)
    ttk.Label(inner_nodes, text="Nodos", font=FONT_H2).pack(anchor="w")
    app.tv_nodes = _mk_tree(inner_nodes,
        cols=("name","cpu%","mem%","score","last_hb","overloaded"),
        widths=(160,70,70,80,220,100)
    )

    # --- Jobs ---
    card_jobs = ttk.Frame(wrap, style="Card.TFrame"); card_jobs.pack(fill="x", pady=(8,0))
    inner_jobs = ttk.Frame(card_jobs); inner_jobs.pack(fill="x", padx=PAD, pady=PAD)
    ttk.Label(inner_jobs, text="Últimos jobs", font=FONT_H2).pack(anchor="w")
    app.tv_jobs = _mk_tree(inner_jobs,
        cols=("id","type","status","progress","error","created","started","finished"),
        widths=(60,100,100,90,220,160,160,160)
    )

    # --- Sesiones ---
    card_sess = ttk.Frame(wrap, style="Card.TFrame"); card_sess.pack(fill="both", expand=True, pady=(8,0))
    inner_sess = ttk.Frame(card_sess); inner_sess.pack(fill="both", expand=True, padx=PAD, pady=PAD)
    ttk.Label(inner_sess, text="Sesiones", font=FONT_H2).pack(anchor="w")
    app.tv_sessions = _mk_tree(inner_sess,
        cols=("session_id","user","state","since","last_event"),
        widths=(160,200,120,160,220)
    )

    # Botonera
    btns = ttk.Frame(wrap); btns.pack(fill="x", pady=(8,0))
    ttk.Button(btns, text="Refrescar ahora", command=lambda: _safe_refresh(app)).pack(side="left")
    app.lbl_hint = ttk.Label(btns, text="(auto cada 3s — requiere JWT con permisos)", style="Muted.TLabel")
    app.lbl_hint.pack(side="left", padx=10)

    # Estado interno para cooldown del summary
    app._dash_summary_paused_until = 0

    def _loop():
        _safe_refresh(app)
        app.root.after(REFRESH_SECS * 1000, _loop)
    app.root.after(REFRESH_SECS * 1000, _loop)

    return tab

def _safe_refresh(app):
    if not app.auth_token:
        if app.lbl_summary is not None:
            app.lbl_summary.config(text="No autenticado.")
        return

    try:
        if app.lbl_summary is not None:  # <-- solo si existe el widget
            _refresh_summary(app)
    except Exception as e:
        if app.lbl_summary is not None:
            app.lbl_summary.config(text=f"Resumen: {e}")

    # el resto queda igual
    try: _refresh_nodes(app)
    except Exception: pass
    try: _refresh_jobs(app)
    except Exception: pass
    try: _refresh_sessions(app)
    except Exception: pass


def _refresh_summary(app):
    # cooldown si ya sabemos que no hay endpoint
    import time
    now_ms = int(time.time() * 1000)
    if now_ms < getattr(app, "_dash_summary_paused_until", 0):
        return

    data = app.api.monitor_summary_best_effort()
    if data.get("_composed"):
        # construido por el cliente
        app.lbl_summary.config(text=_format_summary(data) + "  (composed)")
    elif data.get("_unavailable"):
        app.lbl_summary.config(text="Resumen: endpoint no disponible (/monitor/summary).")
        app._dash_summary_paused_until = now_ms + _COOLDOWN_MS
    else:
        app.lbl_summary.config(text=_format_summary(data))

def _format_summary(data: dict) -> str:
    jobs = data.get("jobs_by_status", {})
    nodes = data.get("nodes", {})
    ls = nodes.get("least_score")
    if ls is None:
        ls = "—"
    else:
        try:
            ls = f"{float(ls):.2f}"
        except Exception:
            pass
    return (
        f"Jobs → queued:{jobs.get('queued',0)} · running:{jobs.get('running',0)} · "
        f"done:{jobs.get('done',0)} · failed:{jobs.get('failed',0)}   "
        f"| Nodos → activos:{nodes.get('active',0)} · least_score:{ls} · "
        f"overloaded:{nodes.get('overloaded',0)}"
    )

def _refresh_nodes(app):
    app.tv_nodes.delete(*app.tv_nodes.get_children())
    payload = app.api.monitor_nodes()
    if isinstance(payload, dict) and payload.get("_unavailable"):
        app.tv_nodes.insert("", "end", values=("—","—","—","—","—","—"))
        return
    items = payload if isinstance(payload, list) else payload.get("items", [])
    for n in items:
        app.tv_nodes.insert(
            "", "end",
            values=(
                n.get("name","?"),
                f"{n.get('cpu_pct',0):.1f}",
                f"{n.get('mem_pct',0):.1f}",
                f"{n.get('score',0):.2f}",
                n.get("last_heartbeat","—"),
                str(n.get("overloaded", False))
            )
        )

def _refresh_jobs(app):
    app.tv_jobs.delete(*app.tv_jobs.get_children())
    payload = app.api.monitor_jobs(limit=50)
    if isinstance(payload, dict) and payload.get("_unavailable"):
        app.tv_jobs.insert("", "end", values=("—","—","—","—","—","—","—","—"))
        return
    items = payload if isinstance(payload, list) else payload.get("items", [])
    for j in items:
        app.tv_jobs.insert(
            "", "end",
            values=(
                j.get("id","?"),
                j.get("type","?"),
                j.get("status","?"),
                f"{j.get('progress',0):.1f}%",
                (j.get("error") or "")[:60],
                j.get("created_at","—"),
                j.get("started_at","—"),
                j.get("finished_at","—"),
            )
        )

def _refresh_sessions(app):
    from datetime import datetime

    def _pick(items):
        # Acepta: lista directa, {"items":[...]}, o {"recent":[...]}
        if isinstance(items, list):
            return items
        if isinstance(items, dict):
            if "items" in items and isinstance(items["items"], list):
                return items["items"]
            if "recent" in items and isinstance(items["recent"], list):
                return items["recent"]
        return []

    def _norm(s: dict) -> tuple[str, str, str, str, str]:
        # nombre de columnas esperadas por el Treeview
        sid = s.get("session_id") or s.get("id") or s.get("sid") or "—"
        usr = s.get("user") or s.get("user_email") or s.get("email") or s.get("username") or "—"

        # estado: intenta derivarlo si tu API expone is_active / expires_at
        state = s.get("state")
        if not state:
            if s.get("is_active") is True:
                state = "active"
            elif s.get("expires_at"):
                try:
                    exp = datetime.fromisoformat(str(s["expires_at"]).replace("Z", "+00:00"))
                    state = "expired" if exp < datetime.now(exp.tzinfo) else "active"
                except Exception:
                    state = "—"
            else:
                state = "—"

        since = s.get("since") or s.get("created_at") or s.get("created") or "—"
        last  = s.get("last_event") or s.get("expires_at") or s.get("updated_at") or "—"
        return str(sid), str(usr), str(state), str(since), str(last)

    app.tv_sessions.delete(*app.tv_sessions.get_children())
    payload = app.api.monitor_sessions()
    if isinstance(payload, dict) and payload.get("_unavailable"):
        app.tv_sessions.insert("", "end", values=("—","—","—","—","—"))
        return

    for s in _pick(payload):
        app.tv_sessions.insert("", "end", values=_norm(s))

