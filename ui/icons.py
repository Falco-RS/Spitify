# UI/icons.py
import math
from pathlib import Path
import tkinter as tk

def load_icon(path: Path, max_px: int):
    if not path.exists():
        return None
    try:
        img = tk.PhotoImage(file=path)
        w, h = img.width(), img.height()
        factor = math.ceil(max(w, h) / max_px)
        if factor > 1:
            img = img.subsample(factor, factor)
        return img
    except Exception:
        return None

def load_icons(assets_dir: Path, spec: dict[str, int]) -> dict[str, tk.PhotoImage | None]:
    out = {}
    for name, size in spec.items():
        out[name] = load_icon(assets_dir / f"{name}.png", size)
    return out
