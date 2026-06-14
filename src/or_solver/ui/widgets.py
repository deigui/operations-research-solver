"""通用 tkinter 组件工厂函数。"""
from __future__ import annotations

import tkinter as tk

from or_solver.constants import BTN_GREEN, FG_WHITE, FONT_BTN


def make_button(
    parent: tk.Widget,
    text: str,
    cmd,
    bg: str = BTN_GREEN,
    fg: str = FG_WHITE,
    width: int = 14,
) -> tk.Button:
    """创建统一风格的按钮。"""
    return tk.Button(
        parent,
        text=text,
        command=cmd,
        bg=bg,
        fg=fg,
        font=FONT_BTN,
        relief="raised",
        bd=2,
        width=width,
        activebackground=bg,
        cursor="hand2",
    )


# 向后兼容别名
make_btn = make_button
