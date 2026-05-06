"""
Shared DistroChat dark UI tokens — use for client GUI and admin dashboard
so colors, radii, and paddings stay consistent.
"""

from __future__ import annotations

import json
import os
from typing import Any

# Core palette
BG = "#0f1117"
CARD = "#161b26"
INNER = "#121722"
LIST_SELECT = "#1e3a5f"
BORDER = "#2d3548"
MUTED = "#94a3b8"
TEXT = "#e8edf5"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"
DANGER = "#ef4444"
SUCCESS = "#22c55e"
SUCCESS_HOVER = "#16a34a"
BTN_SECONDARY = "#334155"
BTN_SECONDARY_HOVER = "#475569"
BAN_BG = "#7f1d1d"
BAN_HOVER = "#991b1b"
PROMOTE_BG = "#14532d"
PROMOTE_HOVER = "#166534"

# Layout
TAB_PAD_X = 16
TAB_PAD_Y = 14
CARD_RADIUS = 12
CARD_RADIUS_LARGE = 18
BORDER_WIDTH = 1

ENTRY_HEIGHT = 40
BTN_HEIGHT = 36
BTN_HEIGHT_LG = 44

FONT_LOG = ("Consolas", 10)
FONT_UI = ("Segoe UI", 10)


def resolve_project_path(relative_to_project_root: str, project_root: str) -> str:
    p = relative_to_project_root.replace("\\", "/")
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(project_root, p))


def read_log_path_from_config(project_root: str) -> str:
    cfg = os.path.join(project_root, "config.json")
    default = os.path.join(project_root, "logs", "chat_logs.txt")
    if not os.path.isfile(cfg):
        return default
    try:
        with open(cfg, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        lp = str(data.get("log_path", "logs/chat_logs.txt"))
        return resolve_project_path(lp, project_root)
    except (OSError, json.JSONDecodeError, TypeError):
        return default
