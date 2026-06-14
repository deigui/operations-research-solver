"""通用表格选区编辑混入（TableEditMixin）。

提供：拖拽多选、Ctrl+C 复制、Ctrl+X 剪切、Delete 清空。
子类需实现四个抽象方法，并在 __init__ 中调用 _tbl_init_sel()。
"""
from __future__ import annotations

import tkinter as tk


class TableEditMixin:
    """表格选区编辑混入：拖拽选区、Ctrl+C/X/Delete。

    子类必须实现：
        _entry_at(r, c)        -> tk.Entry | None
        _entry_default_bg(r, c) -> str  (颜色字符串)
        _all_entries()         -> Iterable[(r, c, entry)]
        _entry_frame()         -> tk.Widget  (用于剪贴板 / winfo_containing)
    """

    # ── 初始化 ────────────────────────────────────────────
    def _tbl_init_sel(self) -> None:
        self._sel_start: tuple[int, int] | None = None
        self._sel_end: tuple[int, int] | None = None

    # ── 子类接口（默认空实现）────────────────────────────
    def _entry_at(self, r: int, c: int) -> tk.Entry | None:
        return None

    def _entry_default_bg(self, r: int, c: int) -> str:
        return "#ffffff"

    def _all_entries(self):
        return iter([])

    def _entry_frame(self) -> tk.Widget:
        return self.body  # type: ignore[attr-defined]

    # ── 选区操作 ─────────────────────────────────────────
    def _sel_click(self, r: int, c: int, extend: bool) -> None:
        if extend and self._sel_start:
            self._sel_end = (r, c)
        else:
            self._sel_start = (r, c)
            self._sel_end = (r, c)
        self._highlight_sel()

    def _sel_drag(self, event: tk.Event) -> None:
        ax = event.widget.winfo_rootx() + event.x
        ay = event.widget.winfo_rooty() + event.y
        target = self._entry_frame().winfo_containing(ax, ay)
        if target is None:
            return
        for r, c, e in self._all_entries():
            if e is target:
                self._sel_end = (r, c)
                self._highlight_sel()
                return

    def _highlight_sel(self) -> None:
        for r, c, e in self._all_entries():
            e.config(bg=self._entry_default_bg(r, c))
        if not (self._sel_start and self._sel_end):
            return
        r1 = min(self._sel_start[0], self._sel_end[0])
        r2 = max(self._sel_start[0], self._sel_end[0])
        c1 = min(self._sel_start[1], self._sel_end[1])
        c2 = max(self._sel_start[1], self._sel_end[1])
        if r1 == r2 and c1 == c2:
            return
        SEL = "#b3d9ff"
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                e = self._entry_at(r, c)
                if e:
                    e.config(bg=SEL)

    # ── 剪贴板操作 ───────────────────────────────────────
    def _cell_value_at(self, r: int, c: int) -> str:
        e = self._entry_at(r, c)
        return e.get() if e else ""

    def _copy_selected(self, event=None) -> str | None:
        if not (self._sel_start and self._sel_end):
            return None
        r1 = min(self._sel_start[0], self._sel_end[0])
        r2 = max(self._sel_start[0], self._sel_end[0])
        c1 = min(self._sel_start[1], self._sel_end[1])
        c2 = max(self._sel_start[1], self._sel_end[1])
        if r1 == r2 and c1 == c2:
            return None
        lines = [
            "\t".join(self._cell_value_at(r, c) for c in range(c1, c2 + 1))
            for r in range(r1, r2 + 1)
        ]
        self._entry_frame().clipboard_clear()
        self._entry_frame().clipboard_append("\n".join(lines))
        return "break"

    def _cut_selected(self, event=None) -> str | None:
        result = self._copy_selected()
        if result != "break":
            return result
        self._delete_selected()
        return "break"

    def _delete_selected(self, event=None) -> str | None:
        if not (self._sel_start and self._sel_end):
            return None
        r1 = min(self._sel_start[0], self._sel_end[0])
        r2 = max(self._sel_start[0], self._sel_end[0])
        c1 = min(self._sel_start[1], self._sel_end[1])
        c2 = max(self._sel_start[1], self._sel_end[1])
        if r1 == r2 and c1 == c2:
            return None
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                e = self._entry_at(r, c)
                if e:
                    try:
                        e.delete(0, "end")
                    except Exception:
                        pass
        self._sel_start = self._sel_end = None
        self._highlight_sel()
        return "break"

    # ── 绑定单元格 ───────────────────────────────────────
    def _bind_cell(self, entry: tk.Entry, r: int, c: int) -> None:
        """给一个 Entry 绑定选区快捷键。"""
        entry.bind("<ButtonPress-1>",  lambda ev, r=r, c=c: self._sel_click(r, c, False))
        entry.bind("<Shift-Button-1>", lambda ev, r=r, c=c: self._sel_click(r, c, True) or "break")
        entry.bind("<B1-Motion>",      self._sel_drag)
        entry.bind("<Control-c>",      self._copy_selected)
        entry.bind("<Control-x>",      self._cut_selected)
        entry.bind("<Delete>",         self._delete_selected)
