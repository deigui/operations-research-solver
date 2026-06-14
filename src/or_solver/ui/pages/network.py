"""最短路求解页。"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox

from or_solver.constants import BTN_GRAY, BTN_GREEN, FONT_SMALL
from or_solver.core.network_solver import dijkstra
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button


class ShortestPathPage(tk.Frame, TableEditMixin):
    def __init__(self, master: tk.Widget, controller):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.n_nodes = tk.IntVar(value=5)
        self.entries_built = False
        self._build_header()

    def _build_header(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        tk.Label(hdr, text="运筹学模型求解系统———最短路问题",
                 font=("微软雅黑", 13, "bold"), bg="#d7ccc8").pack(side="left", padx=10, pady=6)
        ctrl = tk.Frame(hdr, bg="#d7ccc8")
        ctrl.pack(side="left", padx=10)
        tk.Label(ctrl, text="节点数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left")
        tk.Spinbox(ctrl, from_=2, to=20, textvariable=self.n_nodes,
                   width=4, font=FONT_SMALL).pack(side="left", padx=4)
        make_button(hdr, "确  定", self._build_table, bg=BTN_GREEN, width=8).pack(side="left", padx=6)
        make_button(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=4)
        make_button(hdr, "返  回", self.controller.show_menu, bg=BTN_GRAY, width=8).pack(side="left", padx=4)
        self.body = tk.Frame(self, bg="#f5f0e8")
        self.body.pack(fill="both", expand=True, padx=10, pady=6)

    # ── TableEditMixin 接口 ───────────────────────────────
    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            if hasattr(self, "dist_entries") and r < len(self.dist_entries) and c < len(self.dist_entries[r]):
                return self.dist_entries[r][c]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        return "#eeeeee" if r == c else "#e8f5e9"

    def _all_entries(self):
        try:
            if hasattr(self, "dist_entries"):
                for i, row in enumerate(self.dist_entries):
                    for j, e in enumerate(row):
                        if i != j:
                            yield (i, j, e)
        except AttributeError:
            return

    # ── 建表 ────────────────────────────────────────────
    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        n = self.n_nodes.get()
        tk.Label(self.body, text="距离矩阵（无连接填 inf 或留空）",
                 bg="#f5f0e8", font=("微软雅黑", 10, "bold")
                 ).grid(row=0, column=0, columnspan=n + 2, sticky="w")
        for j in range(n):
            tk.Label(self.body, text=f"节点{j+1}", bg="#ffe0b2",
                     font=FONT_SMALL, relief="ridge", width=7).grid(row=1, column=j + 2, padx=2)
        self.dist_entries: list[list[tk.Entry]] = []
        for i in range(n):
            tk.Label(self.body, text=f"节点{i+1}", bg="#f5f0e8",
                     font=FONT_SMALL).grid(row=i + 2, column=1, padx=4)
            row_e = []
            for j in range(n):
                e = tk.Entry(self.body, width=7, font=FONT_SMALL,
                             bg="#eeeeee" if i == j else "#e8f5e9")
                if i == j:
                    e.insert(0, "0")
                    e.config(state="readonly")
                else:
                    self._bind_cell(e, i, j)
                    e.bind("<Control-v>", self._paste_from_clipboard)
                    e.bind("<Control-V>", self._paste_from_clipboard)
                e.grid(row=i + 2, column=j + 2, padx=2, pady=1)
                row_e.append(e)
            self.dist_entries.append(row_e)

        tk.Label(self.body, text="起点节点:", bg="#f5f0e8", font=FONT_SMALL).grid(row=n + 3, column=1, pady=8)
        self.src_var = tk.IntVar(value=1)
        tk.Spinbox(self.body, from_=1, to=n, textvariable=self.src_var,
                   width=4, font=FONT_SMALL).grid(row=n + 3, column=2)
        tk.Label(self.body, text="终点节点:", bg="#f5f0e8", font=FONT_SMALL).grid(row=n + 3, column=3, pady=8)
        self.dst_var = tk.IntVar(value=n)
        tk.Spinbox(self.body, from_=1, to=n, textvariable=self.dst_var,
                   width=4, font=FONT_SMALL).grid(row=n + 3, column=4)
        self.result_text = tk.Text(self.body, height=5, width=50, font=FONT_SMALL, bg="#fffde7")
        self.result_text.grid(row=n + 4, column=1, columnspan=n + 2, pady=4, sticky="w")
        self.entries_built = True

    # ── 剪贴板粘贴 ───────────────────────────────────────
    def _paste_from_clipboard(self, event=None):
        """Ctrl+V 从剪贴板粘贴 TSV 距离矩阵。

        兼容 Excel 直接复制的表格：
        - 自动跳过非数字标题行 / 标题列
        - '-' / '—' 识别为无连接（inf / 留空）
        - 若粘贴数据维度与当前节点数不符，自动扩展节点数并重建表格
        """
        try:
            text = self.body.clipboard_get()
        except Exception:
            return None

        # 单值：走正常粘贴
        if "\t" not in text and "\n" not in text.strip():
            w = event.widget if event else None
            if w:
                try:
                    if w.selection_present():
                        w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except Exception:
                    pass
                w.insert(tk.INSERT, text.strip())
            return "break"

        def _is_num(s: str) -> bool:
            s = s.strip()
            if s in ("", "-", "—", "inf", "∞", "INF"):
                return True          # 视为有效（表示 inf 或空）
            try:
                float(s); return True
            except ValueError:
                return False

        raw_rows = [ln.split("\t") for ln in text.strip().splitlines() if ln.strip()]
        if not raw_rows:
            return "break"

        # 跳过标题行（首行存在非数字非空单元格）
        skip_row = 1 if any(not _is_num(c) and c.strip() for c in raw_rows[0]) else 0
        # 跳过标签列（各数据行首列存在非数字非空）
        skip_col = 0
        for row in raw_rows[skip_row:]:
            if row and not _is_num(row[0]) and row[0].strip():
                skip_col = 1; break

        data = [[row[c] for c in range(skip_col, len(row))]
                for row in raw_rows[skip_row:]]
        if not data:
            return "break"

        new_n = max(len(r) for r in data)
        cur_n = self.n_nodes.get()

        # 自动扩展：数据维度大于当前节点数时重建
        if new_n > cur_n:
            self.n_nodes.set(new_n)
            self._build_table()
            cur_n = new_n

        def _cell_val(s: str) -> str:
            """将单元格文字转换为距离矩阵条目（inf→留空，数字→原样）。"""
            s = s.strip()
            if s in ("-", "—", "inf", "∞", "INF", ""):
                return ""        # 留空表示无连接
            try:
                float(s)
                return s
            except ValueError:
                return ""

        # 计算列偏移：若粘贴列数 = 矩阵阶数-1，说明用户复制时
        # 遗漏了第一列（全为"-"的对角列），数据从矩阵第1列开始。
        n_data_cols = max(len(r) for r in data)
        col_offset = 1 if n_data_cols == cur_n - 1 else 0

        # 若数据实际覆盖的最大列索引超出当前矩阵，扩展节点数
        effective_n = n_data_cols + col_offset
        if effective_n > cur_n:
            self.n_nodes.set(effective_n)
            self._build_table()
            cur_n = effective_n

        for i, row in enumerate(data):
            if i >= cur_n:
                break
            for j, cell in enumerate(row):
                target_j = j + col_offset
                if target_j >= cur_n or i == target_j:   # 跳过对角线
                    continue
                val = _cell_val(cell)
                e = self.dist_entries[i][target_j]
                e.delete(0, "end")
                if val:
                    e.insert(0, val)
        return "break"

    # ── 求解 ────────────────────────────────────────────
    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】")
            return
        n = self.n_nodes.get()
        INF = math.inf
        dist_matrix: list[list[float]] = []
        for i in range(n):
            row = []
            for j in range(n):
                v = self.dist_entries[i][j].get().strip()
                if i == j:
                    row.append(0.0)
                elif v in ("", "inf", "∞"):
                    row.append(INF)
                else:
                    try:
                        row.append(float(v))
                    except ValueError:
                        row.append(INF)
            dist_matrix.append(row)

        src = self.src_var.get() - 1
        dst = self.dst_var.get() - 1
        result = dijkstra(dist_matrix, src, dst)

        self.result_text.delete("1.0", "end")
        if result.status == "no_path":
            self.result_text.insert("end", result.message)
        else:
            self.result_text.insert("end", f"最短路长度: {result.distance}\n")
            self.result_text.insert("end", f"最短路径: {' → '.join(map(str, result.path))}")
