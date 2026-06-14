"""决策分析页（最大最小/最大最大/后悔值/期望值/乐观系数/等可能性）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from or_solver.constants import BTN_GRAY, BTN_GREEN, FONT_SMALL
from or_solver.core.decision_solver import (
    solve_expected_value,
    solve_hurwicz,
    solve_laplace,
    solve_maximax,
    solve_maximin,
    solve_regret,
)
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button

# 引导面板内容（各准则文字说明）保留原始数据结构
_GUIDE_DATA: dict = {
    "最大最小准则": {
        "model_title": "最大最小准则数学表述模型",
        "formula_lines": [
            r"Z = \max_{1 \leq i \leq n} \left[ \min_{1 \leq j \leq m}(a_{ij}) \right]",
        ],
        "body": (
            "悲观决策准则：决策者假设自然状态始终对自己最不利，因此优先保障最坏情况下的收益。\n\n"
            "计算步骤：\n1. 对每个方案，找出其在所有自然状态下的最小收益。\n"
            "2. 将各方案的最小收益汇总比较。\n"
            "3. 选取最小收益中最大的方案作为最优选择。\n\n"
            "适用场景：风险厌恶型决策者，优先保障下限而非追求上限。"
        ),
    },
    "最大最大准则": {
        "model_title": "最大最大准则数学表述模型",
        "formula_lines": [
            r"Z = \max_{1 \leq i \leq n} \left[ \max_{1 \leq j \leq m}(a_{ij}) \right]",
        ],
        "body": (
            "乐观决策准则：决策者假设自然状态始终对自己最有利，专注于最大化可能收益。\n\n"
            "计算步骤：\n1. 对每个方案，找出其在所有自然状态下的最大收益。\n"
            "2. 从各方案最大收益中再取最大值。\n3. 对应方案即为最优选择。\n\n"
            "适用场景：风险偏好型决策者，愿意承担风险以换取更高回报。"
        ),
    },
    "后悔值准则": {
        "model_title": "后悔值准则数学表述模型",
        "formula_lines": [
            r"Z = \min_{1 \leq i \leq n} \left[ \max_{1 \leq j \leq m}(a'_{ij}) \right]",
            r"a'_{ij} = \max_{1 \leq i \leq n}(a_{ij}) - a_{ij}",
        ],
        "body": (
            "通过构造《后悔值矩阵》来衡量《选错方案》的代价，目标是使最坏情况下的后悔程度最小。\n\n"
            "计算步骤：\n1. 每列（每个自然状态）找出最大收益作为参照值。\n"
            "2. 参照值减去当前方案收益，得到该格的后悔值。\n"
            "3. 每个方案取其所有后悔值中的最大值。\n4. 选择最大后悔值最小的方案。"
        ),
    },
    "期望值准则": {
        "model_title": "期望值准则数学表述模型",
        "formula_lines": [
            r"Z = \max_{1 \leq i \leq n} \left[ E(S_i) \right]",
            r"= \max_{1 \leq i \leq n} \left[ \sum_{j=1}^{m} p_j \cdot a_{ij} \right]",
        ],
        "body": (
            "当各自然状态发生的概率已知时，以期望收益最大为目标进行决策。\n\n"
            "计算步骤：\n1. 在首行填入各自然状态的概率，且概率之和应等于 1。\n"
            "2. 对每个方案，将各状态收益与对应概率相乘后求和。\n"
            "3. 比较各方案期望收益，选择最大者。"
        ),
    },
    "乐观系数准则": {
        "model_title": "乐观系数准则数学表述模型",
        "formula_lines": [
            r"Z = \max_{1 \leq i \leq n} H_i",
            r"H_i = \alpha \max_{1 \leq j \leq m}(a_{ij}) + (1-\alpha) \min_{1 \leq j \leq m}(a_{ij})",
        ],
        "formula_fontsize": 12,
        "body": (
            "通过乐观系数 α（0≤α≤1）在乐观与悲观之间取折中，α 越趋近 1 越乐观，越趋近 0 越保守。\n\n"
            "计算步骤：\n1. 对每个方案分别找出最大收益和最小收益。\n"
            "2. 按公式 H_i = α×最大收益 + (1−α)×最小收益 计算综合指标。\n"
            "3. 选择 H_i 最大的方案作为最优决策。"
        ),
    },
    "等可能性准则": {
        "model_title": "等可能性准则数学表述模型",
        "formula_lines": [
            r"Z = \max_{1 \leq i \leq n} \left[ \sum_{j=1}^{m} p_j \cdot a_{ij} \right]",
            r"p_j = \frac{1}{m}",
        ],
        "body": (
            "在缺乏概率信息时，将所有自然状态视为等可能发生，以平均收益最大为决策依据。\n\n"
            "计算步骤：\n1. 对每个方案，将其在各自然状态下的收益相加后除以状态数。\n"
            "2. 比较各方案的平均收益。\n3. 选择平均收益最大的方案。"
        ),
    },
}

_REFS = [
    ("最大最小准则", "Z = max(1<=i<=n)[min(1<=j<=m)(a_ij)]", "看最坏情况里最好的那个方案。"),
    ("最大最大准则", "Z = max(1<=i<=n)[max(1<=j<=m)(a_ij)]", "看最好情况里最好的那个方案。"),
    ("后悔值准则",  "Z = min(1<=i<=n)[max(1<=j<=m)(a'_ij)]", "尽量减少选错后的最大后悔。"),
    ("期望值准则",  "Z = max(1<=i<=n)[Σ(p_j*a_ij)]",         "按给定概率加权，选择期望收益最大方案。"),
    ("乐观系数准则","Z = max_i[α max_j(a_ij)+(1-α) min_j(a_ij)]", "在乐观和保守之间折中。"),
    ("等可能性准则","Z = max(1<=i<=n)[Σ(p_j*a_ij)], p_j=1/m", "把各状态看成等概率事件。"),
]


class DecisionPage(tk.Frame, TableEditMixin):
    def __init__(self, master: tk.Widget, controller, mode: str = "最大最小准则"):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.mode = mode
        self.n_alt = tk.IntVar(value=3)
        self.n_state = tk.IntVar(value=3)
        self.entries_built = False
        self._build_header()

    def _build_header(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"运筹学模型求解系统———{self.mode}",
                 font=("微软雅黑", 13, "bold"), bg="#d7ccc8").pack(side="left", padx=10, pady=6)
        ctrl = tk.Frame(hdr, bg="#d7ccc8")
        ctrl.pack(side="left", padx=10)
        tk.Label(ctrl, text="方案数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left")
        tk.Spinbox(ctrl, from_=2, to=15, textvariable=self.n_alt, width=4, font=FONT_SMALL).pack(side="left", padx=4)
        tk.Label(ctrl, text="自然状态数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left", padx=(8, 0))
        tk.Spinbox(ctrl, from_=2, to=15, textvariable=self.n_state, width=4, font=FONT_SMALL).pack(side="left", padx=4)
        make_button(hdr, "确  定", self._build_table, bg=BTN_GREEN, width=8).pack(side="left", padx=6)
        make_button(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=4)
        make_button(hdr, "返  回", self.controller.show_menu, bg=BTN_GRAY, width=8).pack(side="left", padx=4)
        self.body = tk.Frame(self, bg="#f5f0e8")
        self.body.pack(fill="both", expand=True, padx=10, pady=6)
        self._build_table()

    # ── TableEditMixin 接口 ───────────────────────────────
    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            if r == 0 and hasattr(self, "prob_entries") and c < len(self.prob_entries):
                return self.prob_entries[c]
            if r >= 1 and hasattr(self, "mat_entries") and r - 1 < len(self.mat_entries):
                row = self.mat_entries[r - 1]
                if c < len(row):
                    return row[c]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        return "#fce4ec" if r == 0 else "#e8f5e9"

    def _all_entries(self):
        try:
            if hasattr(self, "prob_entries"):
                for j, e in enumerate(self.prob_entries):
                    yield (0, j, e)
            if hasattr(self, "mat_entries"):
                for i, row in enumerate(self.mat_entries):
                    for j, e in enumerate(row):
                        yield (i + 1, j, e)
        except AttributeError:
            return

    # ── 建表 ────────────────────────────────────────────
    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        m = self.n_alt.get()
        n = self.n_state.get()

        main = tk.PanedWindow(self.body, orient="horizontal", bg="#c8b89a",
                              sashwidth=8, sashrelief="raised", bd=0)
        main.pack(fill="both", expand=True)
        work = tk.Frame(main, bg="#f8f4eb", relief="groove", bd=1)
        guide = tk.Frame(main, bg="#fffaf0", relief="groove", bd=1)
        main.add(work, minsize=520, stretch="always")
        main.add(guide, minsize=520, stretch="always")

        _sash_done = [False]
        def init_sash(_e=None):
            if _sash_done[0]: return
            ww = main.winfo_width()
            if ww > 1040:
                main.sash_place(0, ww // 2, 0)
                _sash_done[0] = True
        main.bind("<Configure>", init_sash)
        main.after_idle(init_sash)

        self._build_guide_panel(guide)
        self.prob_entries: list[tk.Entry] = []

        # ── 乐观系数 slider（置于表格之上）──
        if self.mode == "乐观系数准则":
            af = tk.Frame(work, bg="#f8f4eb")
            af.pack(anchor="w", padx=14, pady=(10, 2))
            tk.Label(af, text="乐观系数 α (0~1，越大越乐观):",
                     bg="#f8f4eb", font=FONT_SMALL).pack(side="left")
            self.alpha_var = tk.DoubleVar(value=0.6)
            tk.Scale(af, variable=self.alpha_var, from_=0, to=1, resolution=0.05,
                     orient="horizontal", length=200, bg="#f8f4eb",
                     font=FONT_SMALL).pack(side="left", padx=8)
            tk.Label(af, textvariable=self.alpha_var,
                     bg="#f8f4eb", font=FONT_SMALL, width=5).pack(side="left")

        # ── 收益矩阵 标题 ──
        tk.Label(work, text="收益矩阵", bg="#f8f4eb",
                 font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=14, pady=(10, 3))

        # ── Canvas 表格（精准 1px 网格线）──
        HDR_H   = 28; ROW_H  = 28
        LBL_W   = 68; COL_W  = 78
        LINE    = "#c8c8c8"
        HDR_BG  = "#ffe0b2"; LBL_BG  = "#fff3e0"
        CELL_BG = "#e8f5e9"; PROB_BG = "#fce4ec"

        has_prob  = self.mode == "期望值准则"
        data_rows = m + (1 if has_prob else 0)
        total_w   = LBL_W + n * COL_W
        total_h   = HDR_H + data_rows * ROW_H

        tbl = tk.Canvas(work, width=total_w + 1, height=total_h + 1,
                        bg="white", highlightthickness=0, bd=0)
        tbl.pack(anchor="w", padx=14, pady=(0, 4))

        # 背景色块
        tbl.create_rectangle(0, 0, total_w, HDR_H, fill=HDR_BG, outline="")
        tbl.create_rectangle(0, HDR_H, LBL_W, total_h, fill=LBL_BG, outline="")
        if has_prob:
            tbl.create_rectangle(LBL_W, HDR_H, total_w,
                                 HDR_H + ROW_H, fill=PROB_BG, outline="")
        start_bg_y = HDR_H + (ROW_H if has_prob else 0)
        tbl.create_rectangle(LBL_W, start_bg_y, total_w, total_h,
                             fill=CELL_BG, outline="")

        # 水平网格线
        for r in range(data_rows + 2):
            y = HDR_H + (r - 1) * ROW_H if r > 0 else 0
            tbl.create_line(0, y, total_w, y, fill=LINE)
        tbl.create_line(0, total_h, total_w, total_h, fill=LINE)

        # 垂直网格线
        for c in range(n + 2):
            x = LBL_W + (c - 1) * COL_W if c > 0 else 0
            tbl.create_line(x, 0, x, total_h, fill=LINE)
        tbl.create_line(total_w, 0, total_w, total_h, fill=LINE)

        # 列标题文字
        for j in range(n):
            cx = LBL_W + j * COL_W + COL_W // 2
            tbl.create_text(cx, HDR_H // 2, text=f"状态{j+1}",
                           font=FONT_SMALL, anchor="center", fill="#333333")

        # 概率行（期望值准则）
        cur_dr = 0
        if has_prob:
            tbl.create_text(LBL_W // 2, HDR_H + ROW_H // 2, text="概率",
                           font=FONT_SMALL, anchor="center", fill="#333333")
            for j in range(n):
                pe = tk.Entry(tbl, font=FONT_SMALL, bg=PROB_BG,
                             relief="flat", bd=0, highlightthickness=0)
                cx = LBL_W + j * COL_W + COL_W // 2
                cy = HDR_H + ROW_H // 2
                tbl.create_window(cx, cy, window=pe, width=COL_W - 6, height=ROW_H - 6)
                pe.insert(0, f"{1/n:.3f}")
                self._bind_cell(pe, 0, j)
                pe.bind("<Control-v>", self._paste_from_clipboard)
                pe.bind("<Control-V>", self._paste_from_clipboard)
                self.prob_entries.append(pe)
            cur_dr = 1

        # 数据行
        self.mat_entries: list[list[tk.Entry]] = []
        for i in range(m):
            cy_row = HDR_H + (cur_dr + i) * ROW_H + ROW_H // 2
            tbl.create_text(LBL_W // 2, cy_row, text=f"方案{i+1}",
                           font=FONT_SMALL, anchor="center", fill="#333333")
            row_e = []
            for j in range(n):
                cx = LBL_W + j * COL_W + COL_W // 2
                e = tk.Entry(tbl, font=FONT_SMALL, bg=CELL_BG,
                            relief="flat", bd=0, highlightthickness=0)
                tbl.create_window(cx, cy_row, window=e,
                                  width=COL_W - 6, height=ROW_H - 6)
                self._bind_cell(e, i + 1, j)
                e.bind("<Control-v>", self._paste_from_clipboard)
                e.bind("<Control-V>", self._paste_from_clipboard)
                row_e.append(e)
            self.mat_entries.append(row_e)

        # 结果区域
        self.result_frame = tk.Frame(work, bg="#f8f4eb")
        self.result_frame.pack(fill="x", padx=14, pady=12, anchor="w")
        self.entries_built = True

    # ── 剪贴板粘贴 ───────────────────────────────────────
    def _paste_from_clipboard(self, event=None):
        """Ctrl+V 从剪贴板粘贴 TSV 收益矩阵，自动跳过标题行列。"""
        try:
            text = self.body.clipboard_get()
        except Exception:
            return None

        # 单值：正常粘贴
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
            if s in ("", "-", "—"):
                return True
            try:
                float(s); return True
            except ValueError:
                return False

        lines = [ln for ln in text.strip().splitlines() if ln.strip()]
        if "\t" in text:
            def _split_mixed(ln):
                cells = []
                for part in ln.split("\t"):
                    ps = part.strip()
                    # 若 tab 切出的格含内部空格且本身非数字，尝试按空格再切
                    if ps and not _is_num(ps) and " " in ps:
                        sub = ps.split()
                        if all(_is_num(s) or s == "" for s in sub):
                            cells.extend(sub)
                            continue
                    cells.append(part)
                return cells
            raw_rows = [_split_mixed(ln) for ln in lines]
        else:
            raw_rows = [ln.split() for ln in lines]
        if not raw_rows:
            return "break"

        # 跳过标题行 / 标签列
        skip_row = 1 if any(not _is_num(c) and c.strip() for c in raw_rows[0]) else 0
        skip_col = 0
        for row in raw_rows[skip_row:]:
            if row and not _is_num(row[0]) and row[0].strip():
                skip_col = 1; break

        data = [[row[c] for c in range(skip_col, len(row))]
                for row in raw_rows[skip_row:]]
        if not data:
            return "break"

        # ── 期望值准则：识别概率首行 ──────────────────────
        data_start = 0
        if (self.mode == "期望值准则"
                and hasattr(self, "prob_entries") and self.prob_entries
                and data):
            try:
                fvals = [float(c.strip()) for c in data[0] if c.strip()]
                if fvals and abs(sum(fvals) - 1.0) < 0.05 and all(0 <= v <= 1 for v in fvals):
                    # 第一行是概率行，直接写入 prob_entries
                    for j, cell in enumerate(data[0]):
                        if j >= len(self.prob_entries):
                            break
                        s = cell.strip()
                        val = s if s not in ("-", "—", "") else ""
                        if val:
                            try:
                                float(val)
                            except ValueError:
                                val = ""
                        self.prob_entries[j].delete(0, "end")
                        if val:
                            self.prob_entries[j].insert(0, val)
                    data_start = 1
            except (ValueError, IndexError):
                pass

        mat_data = data[data_start:]
        new_m = len(mat_data)
        new_n = max(len(r) for r in data)
        cur_m = self.n_alt.get()
        cur_n = self.n_state.get()

        # 自动扩展行列
        changed = False
        if new_m > cur_m:
            self.n_alt.set(new_m); changed = True
        if new_n > cur_n:
            self.n_state.set(new_n); changed = True
        if changed:
            self._build_table()
            # 概率行在重建后已重置，需重填
            if data_start == 1:
                for j, cell in enumerate(data[0]):
                    if j >= len(self.prob_entries):
                        break
                    s = cell.strip()
                    val = s if s not in ("-", "—", "") else ""
                    if val:
                        try:
                            float(val)
                        except ValueError:
                            val = ""
                    self.prob_entries[j].delete(0, "end")
                    if val:
                        self.prob_entries[j].insert(0, val)
            cur_m = self.n_alt.get()
            cur_n = self.n_state.get()

        for i, row in enumerate(mat_data):
            if i >= cur_m:
                break
            for j, cell in enumerate(row):
                if j >= cur_n:
                    break
                s = cell.strip()
                val = "" if s in ("-", "—", "") else s
                try:
                    if val:
                        float(val)
                except ValueError:
                    val = ""
                e = self.mat_entries[i][j]
                e.delete(0, "end")
                if val:
                    e.insert(0, val)
        return "break"

    def _build_guide_panel(self, parent):
        spec = _GUIDE_DATA.get(self.mode, _GUIDE_DATA["最大最小准则"])
        head = tk.Frame(parent, bg="#fffaf0")
        head.pack(fill="x", padx=16, pady=(14, 10))
        tk.Label(head, text="准则定义与计算提示", bg="#fffaf0", fg="#9b1c1c",
                 font=("微软雅黑", 16, "bold")).pack(anchor="w")
        self._create_formula_canvas(head, spec).pack(fill="x")

        body_wrap = tk.Frame(parent, bg="#fffaf0")
        body_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        scrollbar = tk.Scrollbar(body_wrap)
        scrollbar.pack(side="right", fill="y")
        text = tk.Text(body_wrap, yscrollcommand=scrollbar.set, bg="#fffaf0",
                       fg="#1c2328", font=("微软雅黑", 12), relief="flat",
                       wrap="word", spacing1=5, spacing3=8)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)
        text.tag_config("section", foreground="#9b1c1c", font=("微软雅黑", 13, "bold"))
        text.tag_config("subhead", foreground="#0b2a78", font=("微软雅黑", 12, "bold"))
        text.tag_config("formula", foreground="#0a217f", font=("Consolas", 11, "bold"))
        text.tag_config("body",    foreground="#1c2328", font=("微软雅黑", 11))
        text.insert("end", spec["body"] + "\n\n", "body")
        text.insert("end", "相关概念速览\n", "section")
        for name, ref_formula, summary in _REFS:
            text.insert("end", f"{name}\n", "subhead")
            text.insert("end", f"  {ref_formula}\n", "formula")
            text.insert("end", f"  {summary}\n\n", "body")
        text.config(state="disabled")

    def _create_formula_canvas(self, parent, spec):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        container = tk.Frame(parent, bg="#fff2c6",
                             highlightthickness=1, highlightbackground="#b8a97d")

        # 标题用 tkinter Label（中文字体更好）
        tk.Label(container, text=spec["model_title"], bg="#fff2c6", fg="#e21a1a",
                 font=("微软雅黑", 13, "bold")).pack(anchor="w", padx=10, pady=(8, 2))

        lines = spec.get("formula_lines", [])
        n = len(lines)
        fontsize = spec.get("formula_fontsize", 14)

        # 每行约 0.55 英寸高，上下留白 0.15
        fig_h = max(0.55, 0.15 + n * 0.55)
        fig = Figure(figsize=(5.6, fig_h), dpi=96, facecolor="#fff2c6")
        ax = fig.add_axes([0.02, 0.0, 0.96, 1.0], facecolor="#fff2c6")
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        if n == 1:
            ax.text(0.5, 0.52, f"${lines[0]}$",
                    ha="center", va="center", fontsize=fontsize, color="#211486")
        else:
            for idx, line in enumerate(lines):
                y = 1.0 - (idx + 0.5) / n
                ax.text(0.04, y, f"${line}$",
                        ha="left", va="center", fontsize=fontsize, color="#211486")

        mpl_canvas = FigureCanvasTkAgg(fig, container)
        widget = mpl_canvas.get_tk_widget()
        widget.pack(anchor="center", padx=6, pady=(0, 8))
        mpl_canvas.draw()
        # 持有引用，防止 GC 回收
        container._mpl_keep = (mpl_canvas, fig)
        return container

    # ── 求解 ────────────────────────────────────────────
    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        try:
            m = self.n_alt.get()
            n = self.n_state.get()
            mat = [[float(self.mat_entries[i][j].get() or 0) for j in range(n)] for i in range(m)]

            if self.mode == "最大最小准则":
                result = solve_maximin(mat)
                self._draw_maximin_result(mat, result.scores, result.best_value, result.best_index)
                return
            elif self.mode == "最大最大准则":
                result = solve_maximax(mat)
                self._draw_maximax_result(mat, result.scores, result.best_value, result.best_index)
                return
            elif self.mode == "后悔值准则":
                result = solve_regret(mat)
                regret = result.extra["regret_matrix"]
                lines = ["后悔值矩阵："] + [
                    f"  方案{i+1}: {row}  最大后悔值={result.scores[i]}"
                    for i, row in enumerate(regret)
                ]
                lines.append(f"\n最优方案: 方案{result.best_index+1}，最小最大后悔值 = {result.best_value}")
            elif self.mode == "期望值准则":
                probs = [float(self.prob_entries[j].get() or 0) for j in range(n)]
                result = solve_expected_value(mat, probs)
                self._draw_expected_result(mat, result.scores, result.best_value,
                                           result.best_index, probs)
                return
            elif self.mode == "乐观系数准则":
                alpha = self.alpha_var.get()
                result = solve_hurwicz(mat, alpha)
                self._draw_hurwicz_result(mat, result.scores, result.best_value, result.best_index, alpha)
                return
            elif self.mode == "等可能性准则":
                result = solve_laplace(mat)
                self._draw_laplace_result(mat, result.scores, result.best_value, n)
                return
            else:
                return

            self._show_result_text("\n".join(lines))
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))

    def _show_result_text(self, text: str):
        for child in self.result_frame.winfo_children():
            child.destroy()
        rt = tk.Text(self.result_frame, height=8, width=72,
                     font=("微软雅黑", 11), bg="#fffde7", relief="ridge", bd=1)
        rt.pack(anchor="w")
        rt.insert("end", text)
        rt.config(state="disabled")

    def _fmt_num(self, value) -> str:
        return str(int(value)) if float(value).is_integer() else f"{value:g}"

    def _draw_maximin_result(self, mat, scores, best, best_idx):
        for child in self.result_frame.winfo_children():
            child.destroy()
        m = len(mat)
        n = len(mat[0]) if mat else 0
        left_w = 150; cell_w = 92; score_w = 230; header_h = 76; row_h = 46; pad = 18
        table_w = left_w + n * cell_w + score_w
        table_h = header_h + m * row_h
        width = table_w + pad * 2; height = table_h + 96
        canvas = tk.Canvas(self.result_frame, width=width, height=height,
                           bg="#fffdf1", highlightthickness=1, highlightbackground="#b8b0a0")
        canvas.pack(anchor="w")
        navy = "#0b1d72"; red = "#e21a1a"; green = "#1eb34b"; grid = "#333333"
        x0 = pad; y0 = 54
        canvas.create_text(width // 2, 22, text=self.mode, fill=red, font=("微软雅黑", 19, "bold"))
        for x in [x0, x0 + left_w] + [x0 + left_w + j * cell_w for j in range(1, n + 1)] + [x0 + table_w]:
            canvas.create_line(x, y0, x, y0 + table_h, fill=grid, width=1)
        for y in [y0, y0 + header_h] + [y0 + header_h + i * row_h for i in range(1, m + 1)]:
            canvas.create_line(x0, y, x0 + table_w, y, fill=grid, width=1)
        canvas.create_line(x0, y0, x0 + left_w, y0 + header_h, fill=grid, width=1)
        canvas.create_text(x0 + 52, y0 + 18, text="自然状态 Nⱼ", fill=navy, font=("微软雅黑", 12, "bold"))
        canvas.create_text(x0 + 34, y0 + 48, text="aᵢⱼ", fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(x0 + 62, y0 + 66, text="行动方案 Sᵢ", fill=navy, font=("微软雅黑", 12, "bold"))
        for j in range(n):
            cx = x0 + left_w + j * cell_w + cell_w / 2
            canvas.create_text(cx, y0 + 30, text=f"N{j+1}", fill=navy, font=("微软雅黑", 16, "bold"))
            canvas.create_text(cx, y0 + 58, text=f"状态{j+1}", fill=navy, font=("微软雅黑", 10, "bold"))
        score_x = x0 + left_w + n * cell_w
        canvas.create_text(score_x + score_w / 2, y0 + 38,
                           text="Z = max [ min(aij) ]", fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(score_x + score_w / 2, y0 + 61,
                           text="1<=i<=n   1<=j<=m", fill=navy, font=("Cambria Math", 10, "bold"))
        for i, row in enumerate(mat):
            y = y0 + header_h + i * row_h; cy = y + row_h / 2
            canvas.create_text(x0 + 68, cy, text=f"S{i+1}（方案{i+1}）", fill=navy, font=("微软雅黑", 12, "bold"))
            row_min = min(row)
            for j, value in enumerate(row):
                cx = x0 + left_w + j * cell_w + cell_w / 2
                canvas.create_text(cx, cy, text=self._fmt_num(value), fill=navy, font=("微软雅黑", 16, "bold"))
                if value == row_min:
                    canvas.create_oval(cx - 24, cy - 18, cx + 24, cy + 18, outline=red, width=3)
            score_text = self._fmt_num(scores[i])
            if i == best_idx:
                score_text = f"{score_text}（max）"
            canvas.create_text(score_x + score_w / 2 - 18, cy, text=score_text,
                               fill=green, font=("微软雅黑", 14, "bold"))
            if i == best_idx:
                canvas.create_line(score_x + score_w - 24, cy, score_x + score_w - 76, cy,
                                   fill=red, width=5, arrow=tk.LAST, arrowshape=(18, 20, 8))
        canvas.create_text(x0, y0 + table_h + 28, anchor="w",
                           text=f"结论：最优方案为 方案{best_idx+1}，最大最小值 = {self._fmt_num(best)}",
                           fill="#9b1c1c", font=("微软雅黑", 12, "bold"))

    def _draw_maximax_result(self, mat, scores, best, best_idx):
        for child in self.result_frame.winfo_children():
            child.destroy()
        m = len(mat)
        n = len(mat[0]) if mat else 0
        left_w = 150; cell_w = 92; score_w = 230; header_h = 76; row_h = 46; pad = 18
        table_w = left_w + n * cell_w + score_w
        table_h = header_h + m * row_h
        width = table_w + pad * 2; height = table_h + 96
        canvas = tk.Canvas(self.result_frame, width=width, height=height,
                           bg="#fffdf1", highlightthickness=1, highlightbackground="#b8b0a0")
        canvas.pack(anchor="w")
        navy = "#0b1d72"; red = "#e21a1a"; green = "#1eb34b"; grid = "#333333"
        x0 = pad; y0 = 54
        canvas.create_text(width // 2, 22, text=self.mode, fill=red, font=("微软雅黑", 19, "bold"))
        for x in [x0, x0 + left_w] + [x0 + left_w + j * cell_w for j in range(1, n + 1)] + [x0 + table_w]:
            canvas.create_line(x, y0, x, y0 + table_h, fill=grid, width=1)
        for y in [y0, y0 + header_h] + [y0 + header_h + i * row_h for i in range(1, m + 1)]:
            canvas.create_line(x0, y, x0 + table_w, y, fill=grid, width=1)
        canvas.create_line(x0, y0, x0 + left_w, y0 + header_h, fill=grid, width=1)
        canvas.create_text(x0 + 52, y0 + 18, text="自然状态 Nⱼ", fill=navy, font=("微软雅黑", 12, "bold"))
        canvas.create_text(x0 + 34, y0 + 48, text="aᵢⱼ", fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(x0 + 62, y0 + 66, text="行动方案 Sᵢ", fill=navy, font=("微软雅黑", 12, "bold"))
        for j in range(n):
            cx = x0 + left_w + j * cell_w + cell_w / 2
            canvas.create_text(cx, y0 + 30, text=f"N{j+1}", fill=navy, font=("微软雅黑", 16, "bold"))
            canvas.create_text(cx, y0 + 58, text=f"状态{j+1}", fill=navy, font=("微软雅黑", 10, "bold"))
        score_x = x0 + left_w + n * cell_w
        canvas.create_text(score_x + score_w / 2, y0 + 38,
                           text="Z = max [ max(aij) ]", fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(score_x + score_w / 2, y0 + 61,
                           text="1<=i<=n   1<=j<=m", fill=navy, font=("Cambria Math", 10, "bold"))
        for i, row in enumerate(mat):
            y = y0 + header_h + i * row_h; cy = y + row_h / 2
            canvas.create_text(x0 + 68, cy, text=f"S{i+1}（方案{i+1}）", fill=navy, font=("微软雅黑", 12, "bold"))
            row_max = max(row)
            for j, value in enumerate(row):
                cx = x0 + left_w + j * cell_w + cell_w / 2
                canvas.create_text(cx, cy, text=self._fmt_num(value), fill=navy, font=("微软雅黑", 16, "bold"))
                if value == row_max:
                    canvas.create_oval(cx - 24, cy - 18, cx + 24, cy + 18, outline=red, width=3)
            score_text = self._fmt_num(scores[i])
            if i == best_idx:
                score_text = f"{score_text}（max）"
            canvas.create_text(score_x + score_w / 2 - 18, cy, text=score_text,
                               fill=green, font=("微软雅黑", 14, "bold"))
            if i == best_idx:
                canvas.create_line(score_x + score_w - 24, cy, score_x + score_w - 76, cy,
                                   fill=red, width=5, arrow=tk.LAST, arrowshape=(18, 20, 8))
        canvas.create_text(x0, y0 + table_h + 28, anchor="w",
                           text=f"结论：最优方案为 方案{best_idx+1}，最大最大值 = {self._fmt_num(best)}",
                           fill="#9b1c1c", font=("微软雅黑", 12, "bold"))

    def _draw_hurwicz_result(self, mat, scores, best, best_idx, alpha):
        for child in self.result_frame.winfo_children():
            child.destroy()
        m = len(mat)
        n = len(mat[0]) if mat else 0
        left_w = 150; cell_w = 92; score_w = 260; header_h = 96; row_h = 46; pad = 18
        table_w = left_w + n * cell_w + score_w
        table_h = header_h + m * row_h
        width = table_w + pad * 2; height = table_h + 96
        canvas = tk.Canvas(self.result_frame, width=width, height=height,
                           bg="#fffdf1", highlightthickness=1, highlightbackground="#b8b0a0")
        canvas.pack(anchor="w")
        navy = "#0b1d72"; red = "#e21a1a"; blue = "#1565c0"; green = "#1eb34b"; grid = "#333333"
        x0 = pad; y0 = 54
        canvas.create_text(width // 2, 22, text=self.mode, fill=red, font=("微软雅黑", 19, "bold"))
        # grid lines
        for x in [x0, x0 + left_w] + [x0 + left_w + j * cell_w for j in range(1, n + 1)] + [x0 + table_w]:
            canvas.create_line(x, y0, x, y0 + table_h, fill=grid, width=1)
        for y in [y0, y0 + header_h] + [y0 + header_h + i * row_h for i in range(1, m + 1)]:
            canvas.create_line(x0, y, x0 + table_w, y, fill=grid, width=1)
        canvas.create_line(x0, y0, x0 + left_w, y0 + header_h, fill=grid, width=1)
        # header labels
        canvas.create_text(x0 + 52, y0 + 20, text="自然状态 Nⱼ", fill=navy, font=("微软雅黑", 12, "bold"))
        canvas.create_text(x0 + 34, y0 + 54, text="aᵢⱼ", fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(x0 + 62, y0 + 78, text="行动方案 Sᵢ", fill=navy, font=("微软雅黑", 12, "bold"))
        for j in range(n):
            cx = x0 + left_w + j * cell_w + cell_w / 2
            canvas.create_text(cx, y0 + 30, text=f"N{j+1}", fill=navy, font=("微软雅黑", 16, "bold"))
            canvas.create_text(cx, y0 + 62, text=f"状态{j+1}", fill=navy, font=("微软雅黑", 10, "bold"))
        # alpha in header
        canvas.create_text(x0 + left_w + n * cell_w / 2, y0 + header_h / 2 - 4,
                           text=f"α={alpha}", fill=navy, font=("微软雅黑", 10))
        # score column header
        score_x = x0 + left_w + n * cell_w
        canvas.create_text(score_x + score_w / 2, y0 + header_h / 2 - 10,
                           text="折中收益值", fill=navy, font=("微软雅黑", 13, "bold"))
        canvas.create_text(score_x + score_w / 2, y0 + header_h / 2 + 16,
                           text=f"α×max+(1-α)×min", fill=navy, font=("微软雅黑", 9))
        # data rows
        best_indices = {i for i, s in enumerate(scores) if abs(s - best) < 1e-9}
        for i, row in enumerate(mat):
            y = y0 + header_h + i * row_h; cy = y + row_h / 2
            canvas.create_text(x0 + 68, cy, text=f"S{i+1}（方案{i+1}）", fill=navy, font=("微软雅黑", 12, "bold"))
            row_max = max(row); row_min = min(row)
            for j, value in enumerate(row):
                cx = x0 + left_w + j * cell_w + cell_w / 2
                canvas.create_text(cx, cy, text=self._fmt_num(value), fill=navy, font=("微软雅黑", 16, "bold"))
                if value == row_max:
                    canvas.create_oval(cx - 24, cy - 18, cx + 24, cy + 18, outline=red, width=3)
                if value == row_min:
                    canvas.create_oval(cx - 24, cy - 18, cx + 24, cy + 18, outline=blue, width=3)
            score_text = f"{scores[i]:.4f}"
            if i in best_indices:
                score_text += "（max）"
            canvas.create_text(score_x + score_w / 2 - 18, cy, text=score_text,
                               fill=green if i in best_indices else navy,
                               font=("微软雅黑", 14, "bold"))
            if i in best_indices:
                canvas.create_line(score_x + score_w - 24, cy, score_x + score_w - 76, cy,
                                   fill=red, width=5, arrow=tk.LAST, arrowshape=(18, 20, 8))
        # conclusion
        if len(best_indices) > 1:
            best_str = "、".join(f"方案{i+1}" for i in sorted(best_indices))
            conc = f"结论：{best_str} 并列最优，折中收益值 = {best:.4f}"
        else:
            idx = next(iter(best_indices))
            conc = f"结论：最优方案为 方案{idx+1}，折中收益值 = {best:.4f}"
        canvas.create_text(x0, y0 + table_h + 28, anchor="w",
                           text=conc, fill="#9b1c1c", font=("微软雅黑", 12, "bold"))

    def _draw_expected_result(self, mat, scores, best, best_idx, probs):
        for child in self.result_frame.winfo_children():
            child.destroy()
        m = len(mat)
        n = len(mat[0]) if mat else 0
        left_w = 150; cell_w = 92; score_w = 260; header_h = 96; row_h = 46; pad = 18
        table_w = left_w + n * cell_w + score_w
        table_h = header_h + m * row_h
        width = table_w + pad * 2; height = table_h + 96
        canvas = tk.Canvas(self.result_frame, width=width, height=height,
                           bg="#fffdf1", highlightthickness=1, highlightbackground="#b8b0a0")
        canvas.pack(anchor="w")
        navy = "#0b1d72"; red = "#e21a1a"; green = "#1eb34b"; grid = "#333333"
        x0 = pad; y0 = 54
        canvas.create_text(width // 2, 22, text=self.mode,
                           fill=red, font=("微软雅黑", 19, "bold"))
        # 网格线
        for x in [x0, x0 + left_w] + [x0 + left_w + j * cell_w for j in range(1, n + 1)] + [x0 + table_w]:
            canvas.create_line(x, y0, x, y0 + table_h, fill=grid, width=1)
        for y in [y0, y0 + header_h] + [y0 + header_h + i * row_h for i in range(1, m + 1)]:
            canvas.create_line(x0, y, x0 + table_w, y, fill=grid, width=1)
        canvas.create_line(x0, y0, x0 + left_w, y0 + header_h, fill=grid, width=1)
        # 表头
        canvas.create_text(x0 + 52, y0 + 20, text="自然状态 Nⱼ",
                           fill=navy, font=("微软雅黑", 12, "bold"))
        canvas.create_text(x0 + 34, y0 + 54, text="aᵢⱼ",
                           fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(x0 + 62, y0 + 78, text="行动方案 Sᵢ",
                           fill=navy, font=("微软雅黑", 12, "bold"))
        for j in range(n):
            cx = x0 + left_w + j * cell_w + cell_w / 2
            canvas.create_text(cx, y0 + 22, text=f"N{j+1}",
                               fill=navy, font=("微软雅黑", 16, "bold"))
            p_str = f"p={self._fmt_num(probs[j])}" if j < len(probs) else ""
            canvas.create_text(cx, y0 + 48, text=p_str,
                               fill=navy, font=("微软雅黑", 9))
            canvas.create_text(cx, y0 + 68, text=f"状态{j+1}",
                               fill=navy, font=("微软雅黑", 10, "bold"))
        # 分数列表头
        score_x = x0 + left_w + n * cell_w
        canvas.create_text(score_x + score_w / 2, y0 + header_h / 2 - 8,
                           text="Z = max [ E(Si) ]",
                           fill=navy, font=("Cambria Math", 14, "bold"))
        canvas.create_text(score_x + score_w / 2, y0 + header_h / 2 + 16,
                           text="1<=i<=n", fill=navy, font=("Cambria Math", 10))
        # 数据行
        best_indices = {i for i, s in enumerate(scores) if abs(s - best) < 1e-9}
        for i, row in enumerate(mat):
            y = y0 + header_h + i * row_h; cy = y + row_h / 2
            canvas.create_text(x0 + 68, cy, text=f"S{i+1}（方案{i+1}）",
                               fill=navy, font=("微软雅黑", 12, "bold"))
            for j, value in enumerate(row):
                cx = x0 + left_w + j * cell_w + cell_w / 2
                canvas.create_text(cx, cy, text=self._fmt_num(value),
                                   fill=navy, font=("微软雅黑", 16, "bold"))
            score_text = f"{scores[i]:.4f}"
            if i in best_indices:
                score_text += "（max）"
            canvas.create_text(score_x + score_w / 2 - 18, cy, text=score_text,
                               fill=green if i in best_indices else navy,
                               font=("微软雅黑", 14, "bold"))
            if i in best_indices:
                canvas.create_line(score_x + score_w - 24, cy, score_x + score_w - 76, cy,
                                   fill=red, width=5, arrow=tk.LAST, arrowshape=(18, 20, 8))
        # 结论
        if len(best_indices) > 1:
            best_str = "、".join(f"方案{i+1}" for i in sorted(best_indices))
            conc = f"结论：{best_str} 并列最优，最大期望收益 = {best:.4f}"
        else:
            idx = next(iter(best_indices))
            conc = f"结论：最优方案为 方案{idx+1}，最大期望收益 = {best:.4f}"
        canvas.create_text(x0, y0 + table_h + 28, anchor="w",
                           text=conc, fill="#9b1c1c", font=("微软雅黑", 12, "bold"))

    def _draw_laplace_result(self, mat, scores, best, n_state):
        for child in self.result_frame.winfo_children():
            child.destroy()
        m = len(mat)
        n = len(mat[0]) if mat else 0
        left_w = 150; cell_w = 92; score_w = 260; header_h = 76; row_h = 46; pad = 18
        table_w = left_w + n * cell_w + score_w
        table_h = header_h + m * row_h
        width = table_w + pad * 2; height = table_h + 96
        canvas = tk.Canvas(self.result_frame, width=width, height=height,
                           bg="#fffdf1", highlightthickness=1, highlightbackground="#b8b0a0")
        canvas.pack(anchor="w")
        navy = "#0b1d72"; red = "#e21a1a"; green = "#1eb34b"; grid = "#333333"
        x0 = pad; y0 = 54
        canvas.create_text(width // 2, 22, text=self.mode, fill=red, font=("微软雅黑", 19, "bold"))
        for x in [x0, x0 + left_w] + [x0 + left_w + j * cell_w for j in range(1, n + 1)] + [x0 + table_w]:
            canvas.create_line(x, y0, x, y0 + table_h, fill=grid, width=1)
        for y in [y0, y0 + header_h] + [y0 + header_h + i * row_h for i in range(1, m + 1)]:
            canvas.create_line(x0, y, x0 + table_w, y, fill=grid, width=1)
        canvas.create_line(x0, y0, x0 + left_w, y0 + header_h, fill=grid, width=1)
        canvas.create_text(x0 + 52, y0 + 18, text="自然状态 Nⱼ", fill=navy, font=("微软雅黑", 12, "bold"))
        canvas.create_text(x0 + 34, y0 + 48, text="aᵢⱼ", fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(x0 + 62, y0 + 66, text="行动方案 Sᵢ", fill=navy, font=("微软雅黑", 12, "bold"))
        for j in range(n):
            cx = x0 + left_w + j * cell_w + cell_w / 2
            canvas.create_text(cx, y0 + 22, text=f"N{j+1}", fill=navy, font=("微软雅黑", 16, "bold"))
            canvas.create_text(cx, y0 + 45, text=f"p={self._fmt_num(1/n_state)}", fill=navy, font=("微软雅黑", 9))
            canvas.create_text(cx, y0 + 62, text=f"状态{j+1}", fill=navy, font=("微软雅黑", 10, "bold"))
        score_x = x0 + left_w + n * cell_w
        canvas.create_text(score_x + score_w / 2, y0 + 32,
                           text="Z = max [ E(Si) ]", fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(score_x + score_w / 2, y0 + 55,
                           text=f"1<=i<=n,  pj = 1/{n_state}", fill=navy, font=("Cambria Math", 10, "bold"))
        # 并列最优
        best_indices = {i for i, s in enumerate(scores) if abs(s - best) < 1e-9}
        for i, row in enumerate(mat):
            y = y0 + header_h + i * row_h; cy = y + row_h / 2
            canvas.create_text(x0 + 68, cy, text=f"S{i+1}（方案{i+1}）", fill=navy, font=("微软雅黑", 12, "bold"))
            for j, value in enumerate(row):
                cx = x0 + left_w + j * cell_w + cell_w / 2
                canvas.create_text(cx, cy, text=self._fmt_num(value), fill=navy, font=("微软雅黑", 16, "bold"))
            score_text = self._fmt_num(scores[i])
            if i in best_indices:
                score_text += "（max）"
            canvas.create_text(score_x + score_w / 2 - 18, cy, text=score_text,
                               fill=green if i in best_indices else navy,
                               font=("微软雅黑", 14, "bold"))
            if i in best_indices:
                canvas.create_line(score_x + score_w - 24, cy, score_x + score_w - 76, cy,
                                   fill=red, width=5, arrow=tk.LAST, arrowshape=(18, 20, 8))
        # 结论：并列时列出所有最优方案
        if len(best_indices) > 1:
            best_str = "、".join(f"方案{i+1}" for i in sorted(best_indices))
            conc = f"结论：{best_str} 并列最优，最大期望收益 = {self._fmt_num(best)}"
        else:
            idx = next(iter(best_indices))
            conc = f"结论：最优方案为 方案{idx+1}，最大期望收益 = {self._fmt_num(best)}"
        canvas.create_text(x0, y0 + table_h + 28, anchor="w",
                           text=conc, fill="#9b1c1c", font=("微软雅黑", 12, "bold"))
