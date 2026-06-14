"""最小支撑树求解页。"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox

from or_solver.constants import BTN_GRAY, BTN_GREEN, FONT_SMALL
from or_solver.core.network_solver import prim_mst
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button


class MSTPage(tk.Frame, TableEditMixin):
    def __init__(self, master: tk.Widget, controller):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.n_nodes = tk.IntVar(value=6)
        self.entries_built = False
        self._build_header()

    def _build_header(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        tk.Label(hdr, text="运筹学模型求解系统———最小支撑树问题",
                 font=("微软雅黑", 13, "bold"), bg="#d7ccc8").pack(side="left", padx=10, pady=6)
        ctrl = tk.Frame(hdr, bg="#d7ccc8")
        ctrl.pack(side="left", padx=10)
        tk.Label(ctrl, text="节点数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left")
        tk.Spinbox(ctrl, from_=2, to=20, textvariable=self.n_nodes,
                   width=4, font=FONT_SMALL).pack(side="left", padx=4)
        make_button(hdr, "确  定", self._build_table, bg=BTN_GREEN, width=8).pack(side="left", padx=6)
        make_button(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=4)
        make_button(hdr, "返  回", self.controller.show_menu, bg=BTN_GRAY, width=8).pack(side="left", padx=4)

        main = tk.Frame(self, bg="#f5f0e8")
        main.pack(fill="both", expand=True, padx=10, pady=6)

        self.body = tk.Frame(main, bg="#f5f0e8")
        self.body.pack(side="left", fill="both", expand=False)

        right = tk.Frame(main, bg="#f5f5f0", relief="groove", bd=1)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(right, text="── 求解步骤 ──",
                 bg="#f5f5f0", font=("宋体", 10, "bold")).pack(pady=(6, 2))
        step_outer = tk.Frame(right, bg="#f5f5f0")
        step_outer.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        vsb = tk.Scrollbar(step_outer, orient="vertical")
        self.step_text = tk.Text(step_outer, font=("Consolas", 10),
                                 bg="#fffff0", yscrollcommand=vsb.set,
                                 wrap="word", state="disabled")
        vsb.config(command=self.step_text.yview)
        vsb.pack(side="right", fill="y")
        self.step_text.pack(fill="both", expand=True)

        self.chart_frame = tk.Frame(right, bg="#f5f5f0", relief="groove", bd=1, height=300)
        self.chart_frame.pack(fill="x", padx=4, pady=(0, 4))
        self.chart_frame.pack_propagate(False)
        tk.Label(self.chart_frame, text="求解后自动显示最小支撑树图",
                 bg="#f5f5f0", fg="#888", font=("宋体", 9)).pack(expand=True)

        self.after(100, self._load_example)

    # ── TableEditMixin 接口 ──────────────────────────────
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

        tk.Label(self.body, text="权重矩阵（无连接填 inf 或留空，矩阵应对称）",
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

        self.result_text = tk.Text(self.body, height=6, width=46,
                                   font=FONT_SMALL, bg="#fffde7")
        self.result_text.grid(row=n + 3, column=1, columnspan=n + 2, pady=8, sticky="w")
        self.entries_built = True

    # ── 剪贴板粘贴 ───────────────────────────────────────
    def _paste_from_clipboard(self, event=None):
        try:
            text = self.body.clipboard_get()
        except Exception:
            return None

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
                return True
            try:
                float(s); return True
            except ValueError:
                return False

        def _cell_val(s: str) -> str:
            s = s.strip()
            if s in ("-", "—", "inf", "∞", "INF", ""):
                return ""
            try:
                float(s); return s
            except ValueError:
                return ""

        raw_rows = [ln.split("\t") for ln in text.strip().splitlines() if ln.strip()]
        if not raw_rows:
            return "break"

        skip_row = 1 if any(not _is_num(c) and c.strip() for c in raw_rows[0]) else 0
        skip_col = 0
        for row in raw_rows[skip_row:]:
            if row and not _is_num(row[0]) and row[0].strip():
                skip_col = 1; break

        data = [[row[c] for c in range(skip_col, len(row))]
                for row in raw_rows[skip_row:]]
        if not data:
            return "break"

        n_data_cols = max(len(r) for r in data)
        cur_n = self.n_nodes.get()
        col_offset = 1 if n_data_cols == cur_n - 1 else 0
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
                if target_j >= cur_n or i == target_j:
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
        matrix: list[list[float]] = []
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
            matrix.append(row)

        # 对称化：取 min(w[i][j], w[j][i])
        for i in range(n):
            for j in range(i + 1, n):
                w = min(matrix[i][j], matrix[j][i])
                matrix[i][j] = matrix[j][i] = w

        result = prim_mst(matrix)

        self.result_text.delete("1.0", "end")
        if result.status != "found":
            self.result_text.insert("end", result.message)
            return

        self.result_text.insert("end", f"最小支撑树总权重: {result.total_weight:g}\n\n")
        self.result_text.insert("end", "选中边：\n")
        for u, v, w in result.edges:
            self.result_text.insert("end", f"  ({u}, {v})  权重 = {w:g}\n")

        # 步骤面板
        self.step_text.config(state="normal")
        self.step_text.delete("1.0", "end")
        self.step_text.tag_config("title",  foreground="#1a5276", font=("宋体", 10, "bold"))
        self.step_text.tag_config("step",   foreground="#196F3D", font=("Consolas", 10))
        self.step_text.tag_config("result", foreground="#922B21", font=("Consolas", 10, "bold"))
        self.step_text.insert("end", "【Prim 算法求解步骤】\n\n", "title")
        for line in result.steps:
            tag = "result" if "总权重" in line else "step"
            self.step_text.insert("end", line + "\n", tag)
        self.step_text.config(state="disabled")
        self.step_text.see("end")

        self._draw_chart(n, matrix, result.edges, result.total_weight)

    # ── 绘图 ────────────────────────────────────────────
    def _draw_chart(self, n, matrix, mst_edges, total_weight):
        import math as _math
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        for w in self.chart_frame.winfo_children():
            w.destroy()

        fig, ax = plt.subplots(figsize=(5.5, 3.8), dpi=90)
        fig.patch.set_facecolor("#f5f5f0")
        ax.set_facecolor("#fafafa")
        ax.set_title(f"最小支撑树  总权重 = {total_weight:g}",
                     fontsize=11, fontweight="bold", fontfamily="SimHei")
        ax.axis("off")

        # 节点坐标：均匀分布在圆上
        angles = [2 * _math.pi * i / n - _math.pi / 2 for i in range(n)]
        pos = {i: (_math.cos(angles[i]), _math.sin(angles[i])) for i in range(n)}

        mst_set = {(u - 1, v - 1) for u, v, _ in mst_edges} | {(v - 1, u - 1) for u, v, _ in mst_edges}
        INF = _math.inf

        # 画非MST边（灰色细线）
        for i in range(n):
            for j in range(i + 1, n):
                if matrix[i][j] < INF and (i, j) not in mst_set:
                    x0, y0 = pos[i]; x1, y1 = pos[j]
                    ax.plot([x0, x1], [y0, y1], color="#cccccc", linewidth=1, zorder=1)
                    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                    ax.text(mx, my, f"{matrix[i][j]:g}", fontsize=7,
                            color="#aaaaaa", ha="center", va="center", zorder=2)

        # 画MST边（红色粗线）
        for u, v, w in mst_edges:
            i, j = u - 1, v - 1
            x0, y0 = pos[i]; x1, y1 = pos[j]
            ax.plot([x0, x1], [y0, y1], color="#e53935", linewidth=2.5, zorder=3)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            ax.text(mx, my, f"{w:g}", fontsize=9, fontweight="bold",
                    color="#b71c1c", ha="center", va="center",
                    bbox=dict(fc="white", ec="none", pad=1), zorder=4)

        # 画节点
        for i in range(n):
            x, y = pos[i]
            ax.plot(x, y, "o", markersize=18, color="#1565c0", zorder=5)
            ax.text(x, y, str(i + 1), fontsize=9, fontweight="bold",
                    color="white", ha="center", va="center", zorder=6)

        ax.set_xlim(-1.35, 1.35)
        ax.set_ylim(-1.35, 1.35)
        plt.tight_layout(pad=0.3)

        canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas_widget.draw()
        canvas_widget.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    # ── 示例数据 ─────────────────────────────────────────
    def _load_example(self):
        self.n_nodes.set(6)
        self._build_table()
        # 经典6节点MST示例
        INF = ""
        data = [
            [INF, "6",  "1",  "5",  INF,  INF ],
            ["6", INF,  "5",  INF,  "3",  INF ],
            ["1", "5",  INF,  "5",  "6",  "4" ],
            ["5", INF,  "5",  INF,  INF,  "2" ],
            [INF, "3",  "6",  INF,  INF,  "6" ],
            [INF, INF,  "4",  "2",  "6",  INF ],
        ]
        n = 6
        for i in range(n):
            for j in range(n):
                if i != j:
                    self.dist_entries[i][j].delete(0, "end")
                    self.dist_entries[i][j].insert(0, data[i][j])
