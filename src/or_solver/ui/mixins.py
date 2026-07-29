"""通用表格选区编辑混入（TableEditMixin）。

提供：拖拽多选、Ctrl+A 全选、Ctrl+C/X/V、Delete/BackSpace 清空。
子类需实现四个抽象方法，并在 __init__ 中调用 _tbl_init_sel()。
"""
from __future__ import annotations

import tkinter as tk


class TableEditMixin:
    """表格选区编辑混入：拖拽选区、Ctrl+A/C/X/V、Delete。

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

    def _entry_position(self, entry: tk.Entry) -> tuple[int, int] | None:
        for r, c, e in self._all_entries():
            if e is entry:
                return (r, c)
        return None

    def _selection_bounds(self) -> tuple[int, int, int, int] | None:
        if not (self._sel_start and self._sel_end):
            return None
        r1 = min(self._sel_start[0], self._sel_end[0])
        r2 = max(self._sel_start[0], self._sel_end[0])
        c1 = min(self._sel_start[1], self._sel_end[1])
        c2 = max(self._sel_start[1], self._sel_end[1])
        return r1, r2, c1, c2

    def _selected_cell(self) -> tuple[int, int] | None:
        bounds = self._selection_bounds()
        if bounds is None:
            return None
        return bounds[0], bounds[2]

    def _show_cell_context_menu(self, event: tk.Event, r: int, c: int) -> str:
        self._sel_click(r, c, False)
        menu = tk.Menu(event.widget, tearoff=0)
        commands = [
            ("在下方增加行", getattr(self, "_insert_selected_row", None)),
            ("删除当前行", getattr(self, "_delete_selected_row", None)),
            ("在右侧增加列", getattr(self, "_insert_selected_col", None)),
            ("删除当前列", getattr(self, "_delete_selected_col", None)),
        ]
        added = False
        for label, command in commands:
            if callable(command):
                menu.add_command(label=label, command=command)
                added = True
        if not added:
            return "break"
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

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
        bounds = self._selection_bounds()
        if bounds is None:
            return
        r1, r2, c1, c2 = bounds
        if r1 == r2 and c1 == c2:
            return
        SEL = "#b3d9ff"
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                e = self._entry_at(r, c)
                if e:
                    e.config(bg=SEL)

    def _select_all(self, event=None) -> str | None:
        entries = list(self._all_entries())
        if not entries:
            return None
        rows = [r for r, _, _ in entries]
        cols = [c for _, c, _ in entries]
        self._sel_start = (min(rows), min(cols))
        self._sel_end = (max(rows), max(cols))
        self._highlight_sel()
        return "break"

    # ── 剪贴板操作 ───────────────────────────────────────
    def _cell_value_at(self, r: int, c: int) -> str:
        e = self._entry_at(r, c)
        return e.get() if e else ""

    def _copy_selected(self, event=None) -> str | None:
        bounds = self._selection_bounds()
        if bounds is None:
            return None
        r1, r2, c1, c2 = bounds
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
        bounds = self._selection_bounds()
        if bounds is None:
            return None
        r1, r2, c1, c2 = bounds
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

    def _normalize_clipboard_rows(self, text: str) -> list[list[str]]:
        rows = [row.split("\t") for row in text.replace("\r\n", "\n").split("\n")]
        while rows and len(rows[-1]) == 1 and rows[-1][0] == "":
            rows.pop()
        return rows

    def _paste_selected(self, event=None) -> str | None:
        try:
            text = self._entry_frame().clipboard_get()
        except Exception:
            return None
        rows = self._normalize_clipboard_rows(text)
        if not rows:
            return None

        widget = getattr(event, "widget", None)
        start = None
        if self._sel_start and self._sel_end:
            bounds = self._selection_bounds()
            if bounds is not None:
                start = (bounds[0], bounds[2])
        elif isinstance(widget, tk.Entry):
            start = self._entry_position(widget)

        if start is None:
            return None

        start_r, start_c = start
        for r_off, row in enumerate(rows):
            for c_off, value in enumerate(row):
                e = self._entry_at(start_r + r_off, start_c + c_off)
                if e is None:
                    continue
                try:
                    e.delete(0, "end")
                    if value != "":
                        e.insert(0, value)
                except Exception:
                    continue

        end_r = start_r + len(rows) - 1
        end_c = start_c + max(len(row) for row in rows) - 1
        self._sel_start = (start_r, start_c)
        self._sel_end = (end_r, end_c)
        self._highlight_sel()
        return "break"

    # ── 绑定单元格 ───────────────────────────────────────
    def _bind_cell(self, entry: tk.Entry, r: int, c: int) -> None:
        """给一个 Entry 绑定选区快捷键。"""
        entry.bind("<ButtonPress-1>",  lambda ev, r=r, c=c: self._sel_click(r, c, False))
        entry.bind("<Shift-Button-1>", lambda ev, r=r, c=c: self._sel_click(r, c, True) or "break")
        entry.bind("<Button-3>",       lambda ev, r=r, c=c: self._show_cell_context_menu(ev, r, c))
        entry.bind("<B1-Motion>",      self._sel_drag)
        entry.bind("<Control-a>",      self._select_all)
        entry.bind("<Control-A>",      self._select_all)
        entry.bind("<Control-c>",      self._copy_selected)
        entry.bind("<Control-C>",      self._copy_selected)
        entry.bind("<Control-x>",      self._cut_selected)
        entry.bind("<Control-X>",      self._cut_selected)
        entry.bind("<Control-v>",      self._paste_selected)
        entry.bind("<Control-V>",      self._paste_selected)
        entry.bind("<Delete>",         self._delete_selected)
        entry.bind("<BackSpace>",      self._delete_selected)
