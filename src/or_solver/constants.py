# ── 颜色主题 ──────────────────────────────────────────
BG_DARK   = "#1a472a"
BG_MID    = "#2d6a3f"
BTN_PINK  = "#f48fb1"
BTN_GREEN = "#4caf50"
BTN_TEAL  = "#26a69a"
BTN_GRAY  = "#78909c"
FG_WHITE  = "#ffffff"
FG_GOLD   = "#ffd700"

# ── 字体 ──────────────────────────────────────────────
FONT_TITLE = ("微软雅黑", 22, "bold")
FONT_SUB   = ("微软雅黑", 13, "bold")
FONT_BTN   = ("微软雅黑", 11)
FONT_SMALL = ("微软雅黑", 10)

# ── 求解器常量 ─────────────────────────────────────────
BIG_M = 1e7   # 大M法禁止路线标记值

# ── Unicode 下标 ───────────────────────────────────────
SUBSCRIPTS = "₁₂₃₄₅₆₇₈₉"


def xname(j: int) -> str:
    """返回变量名，如 x₁、x₂ …"""
    return f"x{SUBSCRIPTS[j]}" if j < len(SUBSCRIPTS) else f"x{j + 1}"
