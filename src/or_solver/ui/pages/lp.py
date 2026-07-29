"""线性规划 / 整数规划求解页。"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from or_solver.constants import FONT_SMALL, xname
from or_solver.core.goal_solver import solve_preemptive_goal_lp
from or_solver.core.lp_solver import solve_lp, solve_integer_lp, simplex_steps
from or_solver.io import autosave
from or_solver.utils.expr_parser import (
    normalize_expr,
    parse_lp_data_matrix,
    parse_lp_expr,
    parse_table_lp_expr,
)
from or_solver.ui.mixins import TableEditMixin


class LPPage(tk.Frame, TableEditMixin):
    def __init__(self, master: tk.Widget, controller,
                 title: str = "线性规划问题",
                 integer_vars=None, binary_vars: bool = False):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.title_text = title
        self.integer_vars = integer_vars
        self.binary_vars = binary_vars
        is_cutting_stock = title in ("已穷举套材下料", "待穷举套材下料")
        is_mixed = title == "混合整数规划"
        is_invest_site = title == "投资与选址"
        self.var_names: list[str] | None = None
        is_priority_goal = title == "优先级目标"
        self.n_vars = tk.IntVar(value=5 if title == "线性规划问题" else (19 if is_mixed else (14 if is_invest_site else (12 if is_priority_goal else 2))))
        self.n_cons = tk.IntVar(value=5 if title == "线性规划问题" else (8 if is_mixed else (11 if is_invest_site else (5 if is_priority_goal else (3 if is_cutting_stock else 2)))))
        self.obj_type = tk.StringVar(value="最小化" if is_mixed else "最大化")
        self.entries_built = False
        self._build_header()
        if self.title_text == "线性规划问题":
            self.after_idle(self._build_default_lp_table)

    def _is_table_mode(self) -> bool:
        return self.title_text == "表格式线性规划"

    def _var_label(self, j: int) -> str:
        subs = "₀₁₂₃₄₅₆₇₈₉"
        if self.var_names and j < len(self.var_names):
            name = self.var_names[j]
            return "".join(subs[int(ch)] if ch.isdigit() else ch for ch in name)
        return xname(j)

    def _uses_var_type_controls(self) -> bool:
        return self.title_text in ("混合整数规划", "投资与选址", "整数连续投资")

    def _default_var_type(self, j: int) -> str:
        name = self.var_names[j] if self.var_names and j < len(self.var_names) else ""
        if self._uses_var_type_controls():
            return "B" if name.startswith("y") else "I"
        if self.title_text == "投资与选址":
            return "I" if name.startswith("y") or (not name and j >= 11) else "C"
        if self.title_text == "整数连续投资":
            return "I" if name.startswith("y") else "C"
        return "C"

    # ── 布局构建 ────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg="#d7ccc8", relief="raised", bd=1)
        hdr.pack(fill="x")
        ctrl = tk.Frame(hdr, bg="#d7ccc8")
        ctrl.pack(anchor="center", pady=6)
        tk.Label(ctrl, text="决策变量个数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left", padx=(8, 0))
        tk.Spinbox(ctrl, from_=1, to=20, textvariable=self.n_vars, width=4,
                   font=FONT_SMALL, relief="sunken").pack(side="left", padx=2)
        tk.Label(ctrl, text="约束条件个数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left", padx=(12, 0))
        tk.Spinbox(ctrl, from_=1, to=30, textvariable=self.n_cons, width=4,
                   font=FONT_SMALL, relief="sunken").pack(side="left", padx=2)
        tk.Radiobutton(ctrl, text="最大化", variable=self.obj_type, value="最大化",
                       bg="#d7ccc8", font=FONT_SMALL).pack(side="left", padx=(12, 2))
        tk.Radiobutton(ctrl, text="最小化", variable=self.obj_type, value="最小化",
                       bg="#d7ccc8", font=FONT_SMALL).pack(side="left", padx=2)
        tk.Button(ctrl, text="确  定", command=self._build_table,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=8)
        tk.Button(ctrl, text="求  解", command=self._solve,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=2)
        tk.Button(ctrl, text="存  盘", command=self._save,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=2)
        tk.Button(ctrl, text="导  入", command=self._load,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=2)
        tk.Button(ctrl, text="恢复历史", command=self._prompt_auto_load,
                  bg="#ffd700", font=FONT_SMALL, width=8).pack(side="left", padx=6)

        main_pane = tk.PanedWindow(self, orient="horizontal", bg="#888",
                                   sashwidth=5, sashrelief="raised", sashpad=2)
        main_pane.pack(fill="both", expand=True)

        left_pane = tk.Frame(main_pane, bg="#f8f4eb")
        main_pane.add(left_pane, minsize=400, width=750)

        left_pw = tk.PanedWindow(left_pane, orient="vertical", bg="#c8b89a",
                                 sashwidth=5, sashrelief="raised", sashpad=2)
        left_pw.pack(fill="both", expand=True)

        expr_frame = tk.Frame(left_pw, bg="#f0ece4", relief="groove", bd=1)
        left_pw.add(expr_frame, minsize=60, height=120)
        top_row = tk.Frame(expr_frame, bg="#f0ece4")
        top_row.pack(fill="x", padx=6, pady=(4, 2))
        tk.Label(top_row, text="模型表达式（输入或粘贴）:",
                 bg="#f0ece4", font=("宋体", 9, "bold")).pack(side="left")
        tk.Button(top_row, text="解析填入表格", command=self._expr_to_table,
                  bg="#90ee90", font=("宋体", 9), width=12).pack(side="left", padx=6)
        tk.Button(top_row, text="从表格刷新", command=self._table_to_expr,
                  bg="#87ceeb", font=("宋体", 9), width=10).pack(side="left", padx=2)
        tk.Button(top_row, text="清  空",
                  command=lambda: self.main_expr_text.delete("1.0", "end"),
                  bg="#ffcccc", font=("宋体", 9), width=6).pack(side="left", padx=2)
        self.main_expr_text = tk.Text(expr_frame, font=("Consolas", 10), bg="#fffff0",
                                      relief="sunken", bd=1, height=5)
        self.main_expr_text.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self.main_expr_text.insert("1.0", self._default_expr_text())

        left_bottom = tk.Frame(left_pw, bg="#f8f4eb")
        left_pw.add(left_bottom, minsize=320)
        vsb = tk.Scrollbar(left_bottom, orient="vertical")
        hsb = tk.Scrollbar(left_bottom, orient="horizontal")
        canvas = tk.Canvas(left_bottom, bg="#f8f4eb", width=700,
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=canvas.yview)
        hsb.config(command=canvas.xview)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(canvas, bg="#f8f4eb")
        canvas.create_window((4, 4), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        right_pane = tk.Frame(main_pane, bg="#f5f5f0", relief="groove", bd=1)
        main_pane.add(right_pane, minsize=300)

        right_pw = tk.PanedWindow(right_pane, orient="vertical", bg="#888",
                                  sashwidth=5, sashrelief="raised", sashpad=2)
        right_pw.pack(fill="both", expand=True)

        step_top = tk.Frame(right_pw, bg="#f5f5f0")
        right_pw.add(step_top, minsize=80, height=220)
        tk.Label(step_top, text="── 求解步骤 ──",
                 bg="#f5f5f0", font=("宋体", 10, "bold")).pack(pady=(4, 2))
        step_outer = tk.Frame(step_top, bg="#f5f5f0")
        step_outer.pack(fill="both", expand=True)
        vsb3 = tk.Scrollbar(step_outer, orient="vertical")
        self.step_text = tk.Text(step_outer, font=("Consolas", 10),
                                 bg="#fffff0", yscrollcommand=vsb3.set,
                                 wrap="none", state="disabled")
        vsb3.config(command=self.step_text.yview)
        vsb3.pack(side="right", fill="y")
        self.step_text.pack(fill="both", expand=True)

        self.chart_frame = tk.Frame(right_pw, bg="#f5f5f0", relief="groove", bd=1)
        right_pw.add(self.chart_frame, minsize=200)
        tk.Label(self.chart_frame,
                 text="求解后自动显示图形\n【2个变量】可行域图  |  【2个以上变量】灵敏度区间图",
                 bg="#f5f5f0", fg="#888", font=("宋体", 9), justify="center").pack(expand=True)

    # ── TableEditMixin 接口 ──────────────────────────────
    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            n = len(self.obj_entries)
            m = len(self.rhs_entries)
            if r == 0 and c < n:
                return self.obj_entries[c]
            if 1 <= r <= m and c < n:
                return self.con_entries[r - 1][c]
            if 1 <= r <= m and c == n:
                return self.rhs_entries[r - 1]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        try:
            n = len(self.obj_entries)
            if r == 0: return "#ffff99"
            if c < n:  return "#ccffcc"
            return "#ccccff"
        except AttributeError:
            return "#ffffff"

    def _all_entries(self):
        try:
            n = len(self.obj_entries)
            for j, e in enumerate(self.obj_entries):
                yield (0, j, e)
            for i, row in enumerate(self.con_entries):
                for j, e in enumerate(row):
                    yield (i + 1, j, e)
            for i, e in enumerate(self.rhs_entries):
                yield (i + 1, n, e)
        except AttributeError:
            return

    # ── 建表 ────────────────────────────────────────────
    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        n = self.n_vars.get()
        m = self.n_cons.get()
        BG = "#f8f4eb"; YELL = "#fff59d"; GRN = "#d7f8d7"
        PINK = "#f8a5a8"; CYAN = "#c8f1f3"; HDR = "#ffd59e"; W = 8
        LINE = "#c8c8c8"
        subs = "₁₂₃₄₅₆₇₈₉"

        # Canvas 行列尺寸（与决策分析页保持一致风格）
        ROW_H = 26; HDR_H = 26; CON_HDR_H = 44
        LBL_W = 52; COL_W = 60
        ACT_W = 96; REL_W = 66; RHS_W = 96

        # ── 输入区（pack 布局）──
        inp = tk.Frame(self.body, bg=BG)
        inp.grid(row=0, column=0, sticky="w", padx=4, pady=(4, 2))

        # 目标函数 Canvas
        tk.Label(inp, text="目标函数系数", bg=BG,
                 font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=6, pady=(2, 1))
        obj_w = LBL_W + n * COL_W
        obj_h = HDR_H + ROW_H
        obj_cv = tk.Canvas(inp, width=obj_w + 1, height=obj_h + 1,
                           bg="white", highlightthickness=0, bd=0)
        obj_cv.pack(anchor="w", padx=6)

        obj_cv.create_rectangle(0, 0, obj_w, HDR_H, fill=HDR, outline="")
        obj_cv.create_rectangle(LBL_W, HDR_H, obj_w, obj_h, fill=YELL, outline="")
        for y in (0, HDR_H, obj_h):
            obj_cv.create_line(0, y, obj_w, y, fill=LINE)
        for c in range(n + 2):
            x = 0 if c == 0 else LBL_W + (c - 1) * COL_W
            obj_cv.create_line(x, 0, x, obj_h, fill=LINE)
        obj_cv.create_line(obj_w, 0, obj_w, obj_h, fill=LINE)
        for j in range(n):
            vname = self._var_label(j)
            obj_cv.create_text(LBL_W + j * COL_W + COL_W // 2, HDR_H // 2,
                               text=vname, font=("宋体", 10), fill="#333")

        self.obj_entries: list[tk.Entry] = []
        for j in range(n):
            e = tk.Entry(obj_cv, font=("宋体", 10), bg=YELL,
                         relief="flat", bd=0, highlightthickness=0)
            obj_cv.create_window(LBL_W + j * COL_W + COL_W // 2, HDR_H + ROW_H // 2,
                                 window=e, width=COL_W - 4, height=ROW_H - 4)
            self._bind_cell(e, 0, j)
            e.bind("<Control-v>", lambda ev, c=j: self._paste_from_clipboard(ev, 0, c))
            e.bind("<Control-V>", lambda ev, c=j: self._paste_from_clipboard(ev, 0, c))
            self.obj_entries.append(e)

        # 约束条件 Canvas
        tk.Label(inp, text="约束条件系数", bg=BG,
                 font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=6, pady=(4, 1))
        x_act = LBL_W + n * COL_W
        x_rel = x_act + ACT_W
        x_rhs = x_rel + REL_W
        con_w = x_rhs + RHS_W
        con_h = CON_HDR_H + m * ROW_H
        con_cv = tk.Canvas(inp, width=con_w + 1, height=con_h + 1,
                           bg="white", highlightthickness=0, bd=0)
        con_cv.pack(anchor="w", padx=6, pady=(0, 4))

        # 表头背景（使用 CON_HDR_H 高度）
        con_cv.create_rectangle(0, 0, con_w, CON_HDR_H, fill=HDR, outline="")
        con_cv.create_rectangle(0, CON_HDR_H, LBL_W, con_h, fill="#f0ece4", outline="")
        con_cv.create_rectangle(LBL_W, CON_HDR_H, x_act, con_h, fill=GRN, outline="")
        con_cv.create_rectangle(x_act, CON_HDR_H, x_rel, con_h, fill=PINK, outline="")
        con_cv.create_rectangle(x_rel, CON_HDR_H, x_rhs, con_h, fill="#f0f0f0", outline="")
        con_cv.create_rectangle(x_rhs, CON_HDR_H, con_w, con_h, fill="#d9dcff", outline="")

        # 水平分隔线
        for r in range(m + 2):
            y = 0 if r == 0 else CON_HDR_H + (r - 1) * ROW_H
            con_cv.create_line(0, y, con_w, y, fill=LINE)
        con_cv.create_line(0, con_h, con_w, con_h, fill=LINE)
        # 垂直分隔线
        for x in [0, LBL_W] + [LBL_W + (j + 1) * COL_W for j in range(n)] + [x_rel, x_rhs, con_w]:
            con_cv.create_line(x, 0, x, con_h, fill=LINE)

        # 表头文字（普通列居中于 CON_HDR_H//2）
        for cx, txt in (
            [(LBL_W + j * COL_W + COL_W // 2, self._var_label(j)) for j in range(n)] +
            [(x_act + ACT_W // 2, "约束条件实际值"),
             (x_rhs + RHS_W // 2, "约束条件常数项")]
        ):
            con_cv.create_text(cx, CON_HDR_H // 2, text=txt, font=("宋体", 9), fill="#333")

        # "约束关系"列头：上半行显示标签，下半行嵌入批量下拉框（选一项即全部设置）
        con_cv.create_text(x_rel + REL_W // 2, CON_HDR_H // 4,
                           text="约束关系", font=("宋体", 9), fill="#333")
        _batch_rel = tk.StringVar(value="全设")
        _batch_cb = ttk.Combobox(con_cv, textvariable=_batch_rel,
                                  values=["≤", "≥", "=", "<", ">"], width=4,
                                  font=("Arial", 10), state="readonly")
        _batch_cb.bind("<<ComboboxSelected>>",
                       lambda e: [rv.set(_batch_rel.get()) for rv in self.rel_vars])
        con_cv.create_window(x_rel + REL_W // 2, CON_HDR_H * 3 // 4,
                             window=_batch_cb, width=REL_W - 4, height=CON_HDR_H // 2 - 4)

        self.con_entries: list[list[tk.Entry]] = []
        self.rel_vars: list[tk.StringVar] = []
        self.rhs_entries: list[tk.Entry] = []
        self.actual_labels: list[tk.Label] = []
        for i in range(m):
            cy = CON_HDR_H + i * ROW_H + ROW_H // 2
            con_cv.create_text(LBL_W // 2, cy, text=str(i + 1),
                               font=("宋体", 10), fill="#555")
            row_e = []
            for j in range(n):
                e = tk.Entry(con_cv, font=("宋体", 10), bg=GRN,
                             relief="flat", bd=0, highlightthickness=0)
                con_cv.create_window(LBL_W + j * COL_W + COL_W // 2, cy,
                                     window=e, width=COL_W - 4, height=ROW_H - 4)
                self._bind_cell(e, i + 1, j)
                e.bind("<Control-v>", lambda ev, r=i+1, c=j: self._paste_from_clipboard(ev, r, c))
                e.bind("<Control-V>", lambda ev, r=i+1, c=j: self._paste_from_clipboard(ev, r, c))
                row_e.append(e)
            self.con_entries.append(row_e)

            al = tk.Label(con_cv, text="0", bg=PINK, font=("宋体", 10), relief="flat")
            con_cv.create_window(x_act + ACT_W // 2, cy, window=al,
                                 width=ACT_W - 4, height=ROW_H - 4)
            self.actual_labels.append(al)

            rv = tk.StringVar(value="≤")
            cb = ttk.Combobox(con_cv, textvariable=rv,
                              values=["≤", "≥", "=", "<", ">"], width=4,
                              font=("Arial", 10), state="readonly")
            cb.set("≤")
            con_cv.create_window(x_rel + REL_W // 2, cy, window=cb,
                                 width=REL_W - 4, height=ROW_H - 4)
            self.rel_vars.append(rv)

            rhs = tk.Entry(con_cv, font=("宋体", 10), bg="#d9dcff",
                           relief="flat", bd=0, highlightthickness=0)
            con_cv.create_window(x_rhs + RHS_W // 2, cy, window=rhs,
                                 width=RHS_W - 4, height=ROW_H - 4)
            self._bind_cell(rhs, i + 1, n)
            rhs.bind("<Control-v>", lambda ev, r=i+1: self._paste_from_clipboard(ev, r, n))
            rhs.bind("<Control-V>", lambda ev, r=i+1: self._paste_from_clipboard(ev, r, n))
            self.rhs_entries.append(rhs)


        # 混合整数规划变量类型行
        self.var_type_vars: list[tk.StringVar] = []
        if self.title_text == "混合整数规划":
            vt_f = tk.Frame(inp, bg=BG)
            vt_f.pack(anchor="w", padx=6, pady=(2, 0))
            tk.Label(vt_f, text="变量类型 (C=连续 I=整数 B=0-1):",
                     bg=BG, font=("宋体", 9, "bold")).pack(side="left")
            for j in range(n):
                vt = tk.StringVar(value=self._default_var_type(j))
                cb2 = ttk.Combobox(vt_f, textvariable=vt, values=["C", "I", "B"],
                                   width=3, font=("宋体", 9), state="readonly")
                cb2.pack(side="left", padx=2)
                self.var_type_vars.append(vt)

        # 最优解行（Canvas，与约束表列对齐）
        sol_cv = tk.Canvas(inp, width=con_w + 1, height=ROW_H + 1,
                           bg="white", highlightthickness=0, bd=0)
        sol_cv.pack(anchor="w", padx=6, pady=(0, 4))
        sol_cv.create_rectangle(0, 0, LBL_W, ROW_H, fill="#f0ece4", outline="")
        sol_cv.create_rectangle(LBL_W, 0, x_act, ROW_H, fill=CYAN, outline="")
        sol_cv.create_rectangle(x_act, 0, x_rel, ROW_H, fill=BG, outline="")
        sol_cv.create_rectangle(x_rel, 0, x_rhs, ROW_H, fill=BG, outline="")
        sol_cv.create_rectangle(x_rhs, 0, con_w, ROW_H, fill=PINK, outline="")
        for gx in [0, LBL_W] + [LBL_W + (j+1)*COL_W for j in range(n)] + [x_rel, x_rhs, con_w]:
            sol_cv.create_line(gx, 0, gx, ROW_H, fill=LINE)
        sol_cv.create_line(0, 0, con_w, 0, fill=LINE)
        sol_cv.create_line(0, ROW_H, con_w, ROW_H, fill=LINE)
        sol_cv.create_text(LBL_W // 2, ROW_H // 2, text="最优解",
                           font=("宋体", 10, "bold"), fill="#333")
        sol_cv.create_text(x_rel + REL_W // 2, ROW_H // 2, text="最优值",
                           font=("宋体", 10, "bold"), fill="#333")
        self.result_labels: list[tk.Label] = []
        for j in range(n):
            rl = tk.Label(sol_cv, text="", bg=CYAN, font=("宋体", 10), relief="flat")
            sol_cv.create_window(LBL_W + j * COL_W + COL_W // 2, ROW_H // 2,
                                 window=rl, width=COL_W - 4, height=ROW_H - 4)
            self.result_labels.append(rl)
        self.opt_label = tk.Label(sol_cv, text="", bg=PINK,
                                  font=("宋体", 11, "bold"), relief="flat")
        sol_cv.create_window(x_rhs + RHS_W // 2, ROW_H // 2,
                             window=self.opt_label, width=RHS_W - 4, height=ROW_H - 4)

        # ── 灵敏度分析区（求解后动态构建）──
        self.out_frame = tk.Frame(self.body, bg=BG)
        self.out_frame.grid(row=1, column=0, sticky="w", padx=4, pady=(2, 2))
        self.sens_var_rows: list[list[tk.Label]] = []
        self.sens_con_rows: list[list[tk.Label]] = []
        self.conclusion_label = tk.Label(self.out_frame, text="", bg=BG,
                                         font=("宋体", 10), fg="#cc0000")
        self.entries_built = True

    def _snapshot_entries(self) -> dict:
        if not self.entries_built:
            return {}
        return {
            "obj": [e.get() for e in self.obj_entries],
            "A": [[e.get() for e in row] for row in self.con_entries],
            "rels": [rv.get() for rv in self.rel_vars],
            "rhs": [e.get() for e in self.rhs_entries],
            "var_types": [v.get() for v in getattr(self, "var_type_vars", [])],
        }

    def _restore_entries(self, data: dict) -> None:
        for j, value in enumerate(data.get("obj", [])):
            if j < len(self.obj_entries):
                self.obj_entries[j].delete(0, "end")
                self.obj_entries[j].insert(0, value)
        for i, row in enumerate(data.get("A", [])):
            if i >= len(self.con_entries):
                break
            for j, value in enumerate(row):
                if j < len(self.con_entries[i]):
                    self.con_entries[i][j].delete(0, "end")
                    self.con_entries[i][j].insert(0, value)
        for i, value in enumerate(data.get("rels", [])):
            if i < len(self.rel_vars):
                self.rel_vars[i].set(value)
        for i, value in enumerate(data.get("rhs", [])):
            if i < len(self.rhs_entries):
                self.rhs_entries[i].delete(0, "end")
                self.rhs_entries[i].insert(0, value)
        for j, value in enumerate(data.get("var_types", [])):
            if j < len(getattr(self, "var_type_vars", [])):
                self.var_type_vars[j].set(value)

    def _delete_selected_row(self) -> None:
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        if cell is None or cell[0] <= 0:
            messagebox.showinfo("删除行", "请先选中要删除的约束行")
            return
        if self.n_cons.get() <= 1:
            messagebox.showinfo("删除行", "至少保留 1 个约束条件")
            return
        remove_i = cell[0] - 1
        data = self._snapshot_entries()
        data["A"].pop(remove_i)
        data["rels"].pop(remove_i)
        data["rhs"].pop(remove_i)
        self.n_cons.set(self.n_cons.get() - 1)
        self._build_table()
        self._restore_entries(data)
        self._table_to_expr()

    def _insert_selected_row(self) -> None:
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        insert_i = self.n_cons.get() if cell is None or cell[0] <= 0 else cell[0]
        data = self._snapshot_entries()
        data["A"].insert(insert_i, [""] * self.n_vars.get())
        data["rels"].insert(insert_i, "≤")
        data["rhs"].insert(insert_i, "")
        self.n_cons.set(self.n_cons.get() + 1)
        self._build_table()
        self._restore_entries(data)
        self._table_to_expr()

    def _delete_selected_col(self) -> None:
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        if cell is None:
            messagebox.showinfo("删除列", "请先选中要删除的变量列")
            return
        remove_j = cell[1]
        if remove_j >= self.n_vars.get():
            messagebox.showinfo("删除列", "请选择变量系数列")
            return
        if self.n_vars.get() <= 1:
            messagebox.showinfo("删除列", "至少保留 1 个决策变量")
            return
        data = self._snapshot_entries()
        data["obj"].pop(remove_j)
        for row in data["A"]:
            if remove_j < len(row):
                row.pop(remove_j)
        if remove_j < len(data["var_types"]):
            data["var_types"].pop(remove_j)
        self.n_vars.set(self.n_vars.get() - 1)
        self._build_table()
        self._restore_entries(data)
        self._table_to_expr()

    def _insert_selected_col(self) -> None:
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        insert_j = self.n_vars.get() if cell is None else min(cell[1] + 1, self.n_vars.get())
        data = self._snapshot_entries()
        data["obj"].insert(insert_j, "")
        for row in data["A"]:
            row.insert(insert_j, "")
        if data["var_types"]:
            data["var_types"].insert(insert_j, "C")
        self.n_vars.set(self.n_vars.get() + 1)
        self._build_table()
        self._restore_entries(data)
        self._table_to_expr()

    def _default_expr_text(self) -> str:
        if self._is_table_mode():
            return (
                "max\n"
                "15 10 7 13 9\n"
                "5 10 7 0 0 <= 8000\n"
                "6 4 8 6 4 <= 12000\n"
                "3 2 2 3 2 <= 10000"
            )
        if self.title_text == "线性规划问题":
            return ""
        if self.title_text == "混合整数规划":
            return (
                "min f=8x1+15x2+10x3+12x4+7x5+9x6+18x7+16x8+x9+11x10+12x11+8x12+19x13+4x14+15x15"
                "+370000y1+300000y2+375000y3+500000y4\n"
                "s.t.\n"
                "x1+x2+x3<=30000\n"
                "x4+x5+x6-20000y1<=0\n"
                "x7+x8+x9-40000y2<=0\n"
                "x10+x11+x12-30000y3<=0\n"
                "x13+x14+x15-10000y4<=0\n"
                "x1+x4+x7+x10+x13=30000\n"
                "x2+x5+x8+x11+x14=20000\n"
                "x3+x6+x9+x12+x15=20000"
            )
        if self.title_text == "投资与选址":
            return (
                "max z = 1.15x4 + 1.28x5 + 1.40x6 + 1.06x11\n"
                "s.t.\n"
                "x1 + x7 = 10\n"
                "x2 + x6 - 1.06x7 + x8 = 0\n"
                "-1.15x1 + x3 + x5 - 1.06x8 + x9 = 0\n"
                "-1.15x2 + x4 - 1.06x9 + x10 = 0\n"
                "-1.15x3 - 1.06x10 + x11 = 0\n"
                "x1 - 4y1 >= 0\n"
                "x1 - 16y1 >= 0\n"
                "x5 - 5y2 >= 0\n"
                "x5 - 3y2 >= 0\n"
                "x6 - 2y3 = 0\n"
                "y3 <= 4"
            )
        if self.title_text == "优先级目标":
            return (
                "# P1: min dp1 + dm2\n"
                "# P2: min dm3\n"
                "# P3: min dm4 + 2dm5\n"
                "min z = dp1 + dm2 + dm3 + dm4 + 2dm5\n"
                "s.t.\n"
                "200x1 + 300x2 + dm1 - dp1 = 68000\n"
                "200x1 + 300x2 + dm2 - dp2 = 60000\n"
                "250x1 + 125x2 + dm3 - dp3 = 70000\n"
                "x1 + dm4 - dp4 = 200\n"
                "x2 + dm5 - dp5 = 120"
            )
        if self.title_text == "已穷举套材下料":
            return (
                "min  W = 0.1x1 + 0.3x2\n"
                "s.t.\n"
                "  2x1 + x2 >= 10\n"
                "  2x2 >= 8\n"
                "  x1 >= 4\n"
                "\n"
                "x1 >= 0\n"
                "x2 >= 0"
            )
        if self.title_text == "待穷举套材下料":
            return (
                "# 先穷举可行方案，再按“已穷举套材下料”建模。\n"
                "# 例：原材料 7.4m，下料长度 2.9m、2.1m、1.5m，方案如下：\n"
                "# 方案1: 2根2.9m、0根2.1m、1根1.5m，余料0.1m\n"
                "# 方案2: 1根2.9m、2根2.1m、0根1.5m，余料0.3m\n"
                "min  W = 0.1x1 + 0.3x2\n"
                "s.t.\n"
                "  2x1 + x2 >= 10\n"
                "  2x2 >= 8\n"
                "  x1 >= 4\n"
                "\n"
                "x1 >= 0\n"
                "x2 >= 0"
            )
        return "max  Z = 15x1 + 10x2 + 7x3\ns.t.\n  5x1 + 10x2 + 7x3 <= 8000\n  x1 >= 0"

    def _build_default_lp_table(self) -> None:
        if self.entries_built:
            return
        self._build_table()
        self._clear_lp_outputs()

    def _clear_lp_outputs(self) -> None:
        if not self.entries_built:
            return
        for lbl in getattr(self, "result_labels", []):
            lbl.config(text="")
        for lbl in getattr(self, "actual_labels", []):
            lbl.config(text="0")
        if hasattr(self, "opt_label"):
            self.opt_label.config(text="")
        # 清空动态灵敏度区
        if hasattr(self, "out_frame"):
            for w in self.out_frame.winfo_children():
                w.destroy()
            self.sens_var_rows = []
            self.sens_con_rows = []
            self.conclusion_label = tk.Label(self.out_frame, text="", bg="#f8f4eb",
                                             font=("宋体", 10), fg="#cc0000")
        if hasattr(self, "step_text"):
            self.step_text.config(state="normal")
            self.step_text.delete("1.0", "end")
            self.step_text.config(state="disabled")
        if hasattr(self, "chart_frame"):
            for w in self.chart_frame.winfo_children():
                w.destroy()
            tk.Label(
                self.chart_frame,
                text="求解后自动显示图形\n【2个变量】可行域图  |  【2个以上变量】灵敏度区间图",
                bg="#f5f5f0",
                fg="#888",
                font=("宋体", 9),
                justify="center",
            ).pack(expand=True)

    @staticmethod
    def _set_entry_value(entry: tk.Entry, value: str) -> None:
        entry.delete(0, "end")
        if value != "":
            entry.insert(0, value)

    def _snapshot_input_state(self) -> dict | None:
        if not self.entries_built:
            return None
        c, A, b, rels = self._get_data()
        return {
            "n_vars": self.n_vars.get(),
            "n_cons": self.n_cons.get(),
            "obj_type": self.obj_type.get(),
            "c": c,
            "A": A,
            "b": b,
            "rels": rels,
        }

    def _restore_input_state(self, snapshot: dict | None) -> None:
        if not snapshot or not self.entries_built:
            return
        self.obj_type.set(snapshot.get("obj_type", "最大化"))
        c = snapshot.get("c", [])
        A = snapshot.get("A", [])
        b = snapshot.get("b", [])
        rels = snapshot.get("rels", [])
        m = min(len(A), len(self.con_entries))
        n = min(len(c), len(self.obj_entries))

        for j in range(n):
            value = c[j]
            self._set_entry_value(
                self.obj_entries[j],
                self._format_number(value) if abs(value) > 1e-12 else "",
            )

        for i in range(m):
            row = A[i] if i < len(A) else []
            for j in range(min(len(row), len(self.con_entries[i]))):
                value = row[j]
                self._set_entry_value(
                    self.con_entries[i][j],
                    self._format_number(value) if abs(value) > 1e-12 else "",
                )
            if i < len(b):
                self._set_entry_value(
                    self.rhs_entries[i],
                    self._format_number(b[i]) if abs(b[i]) > 1e-12 else "",
                )
            if i < len(rels):
                self.rel_vars[i].set(rels[i])

    def _ensure_table_size(self, new_n: int, new_m: int) -> None:
        cur_n = self.n_vars.get()
        cur_m = self.n_cons.get()
        if new_n == cur_n and new_m == cur_m:
            return
        snapshot = self._snapshot_input_state()
        self.n_vars.set(new_n)
        self.n_cons.set(new_m)
        self.entries_built = False
        self._build_table()
        self._restore_input_state(snapshot)

    @staticmethod
    def _is_num_text(text: str) -> bool:
        s = text.strip()
        if s in ("", "-", "—"):
            return True
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _parse_clipboard_block(self, text: str) -> list[list[str]]:
        lines = [ln for ln in text.strip().splitlines() if ln.strip()]
        if not lines:
            return []
        if "\t" in text:
            raw_rows = [ln.split("\t") for ln in lines]
        else:
            raw_rows = [ln.split() for ln in lines]
        if not raw_rows:
            return []

        skip_row = 1 if any(not self._is_num_text(c) and c.strip() for c in raw_rows[0]) else 0
        skip_col = 0
        for row in raw_rows[skip_row:]:
            if row and not self._is_num_text(row[0]) and row[0].strip():
                skip_col = 1
                break

        return [[row[c].strip() for c in range(skip_col, len(row))] for row in raw_rows[skip_row:]]

    def _looks_like_numeric_matrix(self, raw: str) -> bool:
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            return False
        if any(re.match(r"^(max|min)\b", line, re.I) for line in lines):
            return False
        if any(re.search(r"[xX]\d+", line) for line in lines):
            return False
        numeric_rows = 0
        for line in lines:
            cells = line.replace("\t", " ").split()
            if len(cells) < 2:
                return False
            if all(self._is_num_text(cell) for cell in cells):
                numeric_rows += 1
            else:
                return False
        return numeric_rows >= 1

    def _infer_constraint_paste_layout(
        self, row_width: int, start_c: int, current_n: int
    ) -> tuple[int, bool]:
        if row_width <= 0:
            return 0, False
        if start_c >= current_n:
            return 0, True
        if (
            start_c == 0
            and (
                row_width > current_n + 1
                or (current_n >= 4 and row_width == current_n + 1)
            )
        ):
            return row_width - 1, True
        return row_width, False

    def _paste_from_clipboard(self, event, start_r: int = 0, start_c: int = 0):
        try:
            text = self.body.clipboard_get()
        except Exception:
            return None

        if "\t" not in text and "\n" not in text.strip():
            widget = event.widget if event else None
            if isinstance(widget, tk.Entry):
                try:
                    if widget.selection_present():
                        widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except Exception:
                    pass
                widget.insert(tk.INSERT, text.strip())
            return "break"

        data = self._parse_clipboard_block(text)
        if not data:
            return "break"

        cur_n = self.n_vars.get()
        cur_m = self.n_cons.get()
        new_n = cur_n
        new_m = cur_m

        if start_r == 0:
            new_n = max(new_n, start_c + len(data[0]))
            constraint_rows = data[1:]
            if constraint_rows:
                new_m = max(new_m, len(constraint_rows))
                for row in constraint_rows:
                    coeff_width, _ = self._infer_constraint_paste_layout(len(row), 0, new_n)
                    new_n = max(new_n, coeff_width)
        else:
            new_m = max(new_m, start_r + len(data) - 1)
            for row in data:
                coeff_width, _ = self._infer_constraint_paste_layout(len(row), start_c, new_n)
                new_n = max(new_n, start_c + coeff_width)

        self._ensure_table_size(new_n, new_m)

        if start_r == 0:
            for j, value in enumerate(data[0]):
                if start_c + j < len(self.obj_entries):
                    self._set_entry_value(self.obj_entries[start_c + j], value)
            row_blocks = data[1:]
            base_r = 1
            base_c = 0
        else:
            row_blocks = data
            base_r = start_r
            base_c = start_c

        for i, row in enumerate(row_blocks):
            target_r = base_r + i
            if target_r < 1 or target_r > len(self.con_entries):
                continue
            coeff_width, rhs_included = self._infer_constraint_paste_layout(
                len(row), base_c, self.n_vars.get()
            )
            coeff_values = row[:coeff_width]
            rhs_value = row[-1] if rhs_included and row else None

            for j, value in enumerate(coeff_values):
                target_c = base_c + j
                if target_c < len(self.con_entries[target_r - 1]):
                    self._set_entry_value(self.con_entries[target_r - 1][target_c], value)
            if rhs_value is not None and target_r - 1 < len(self.rhs_entries):
                self._set_entry_value(self.rhs_entries[target_r - 1], rhs_value)

        self._sel_start = (start_r, start_c)
        self._sel_end = (
            base_r + max(len(row_blocks) - 1, 0),
            base_c + max((max((len(r) for r in row_blocks), default=1) - 1), 0),
        )
        self._highlight_sel()
        return "break"

    # ── 数据读取 ─────────────────────────────────────────
    def _get_data(self):
        n = self.n_vars.get()
        m = self.n_cons.get()
        c, A, b, rels = [], [], [], []
        for e in self.obj_entries:
            c.append(float(e.get() or 0))
        REL_MAP = {"<": "≤", ">": "≥", "=": "=", "≤": "≤", "≥": "≥"}
        for i in range(m):
            row = [float(e.get() or 0) for e in self.con_entries[i]]
            A.append(row)
            b.append(float(self.rhs_entries[i].get() or 0))
            rels.append(REL_MAP.get(self.rel_vars[i].get(), "≤"))
        return c, A, b, rels

    # ── 求解 ────────────────────────────────────────────
    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        try:
            c, A, b, rels = self._get_data()
            n = len(c)
            maximize = (self.obj_type.get() == "最大化")

            if self.title_text == "优先级目标":
                self._solve_priority_goal_branch(c, A, b, rels)
                return

            # 整数规划分支
            if self.binary_vars or self.integer_vars or self._uses_var_type_controls():
                self._solve_integer_branch(c, A, b, rels, maximize)
                return

            result = solve_lp(c, A, b, rels, maximize)
            if result.status != "optimal":
                messagebox.showerror("求解失败", f"无可行解或无界\n{result.message}")
                return

            x = result.x
            opt = result.obj_value

            def nfmt(v):
                if abs(v) < 1e-8: return "0"
                if abs(v - round(v)) < 1e-6: return str(int(round(v)))
                return f"{v:.2f}"

            for j, lbl in enumerate(self.result_labels):
                lbl.config(text=nfmt(x[j]))
            self.opt_label.config(text=nfmt(opt))
            for i in range(len(A)):
                val = result.actual_values[i] if i < len(result.actual_values) else 0.0
                self.actual_labels[i].config(text=nfmt(val))
            self._auto_save()

            self._show_sensitivity(x, c, A, b, rels, opt,
                                   result.shadow_prices,
                                   result.c_lower, result.c_upper,
                                   result.b_lower, result.b_upper,
                                   maximize, c_diff=result.c_diff)

        except ValueError as e:
            messagebox.showerror("输入错误", f"请检查数据格式\n{e}")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _solve_integer_branch(self, c, A, b, rels, maximize):
        n = len(c)
        mixed_types = None
        if self._uses_var_type_controls() and hasattr(self, "var_type_vars") and self.var_type_vars:
            mixed_types = [self.var_type_vars[j].get() if j < len(self.var_type_vars) else "C"
                           for j in range(n)]

        result = solve_integer_lp(c, A, b, rels, maximize,
                                  integer_vars=self.integer_vars if not self.binary_vars else None,
                                  binary_vars=self.binary_vars,
                                  mixed_var_types=mixed_types)
        if result.status != "optimal":
            messagebox.showerror("求解失败", result.message)
            return

        xvals = result.x
        opt_v = result.obj_value
        for j, lbl in enumerate(self.result_labels):
            v = xvals[j] if xvals[j] is not None else 0.0
            lbl.config(text=str(int(round(v))) if abs(v - round(v)) < 1e-4 else f"{v:.4f}")
        self.opt_label.config(text=str(int(round(opt_v))) if abs(opt_v - round(opt_v)) < 1 else f"{opt_v:.4f}")
        for i in range(len(A)):
            val = sum(A[i][j] * (xvals[j] or 0) for j in range(n))
            self.actual_labels[i].config(text=f"{val:.1f}")
        try:
            self.step_text.config(state="normal")
            self.step_text.delete("1.0", "end")
            self.step_text.tag_config("title", foreground="#1a5276", font=("宋体", 10, "bold"))
            self.step_text.tag_config("vars",  foreground="#196F3D", font=("Courier New", 10))
            self.step_text.tag_config("obj",   foreground="#922B21", font=("Courier New", 10, "bold"))
            self.step_text.insert("end", "【整数规划求解结果】\n\n", "title")
            for j in range(n):
                vt = (self.var_type_vars[j].get()
                      if hasattr(self, "var_type_vars") and j < len(self.var_type_vars) else "?")
                v = xvals[j] or 0.0
                self.step_text.insert("end", f"  {self._var_label(j)}({vt}) = {v:.4g}\n", "vars")
            self.step_text.insert("end", f"\n  最优值 Z = {opt_v:.4g}\n", "obj")

            # 显示约束实际值与松弛量
            self.step_text.insert("end", "\n【约束满足情况】\n", "title")
            for i in range(len(A)):
                val = sum(A[i][j] * (xvals[j] or 0) for j in range(n))
                slack = b[i] - val if rels[i] not in ("≥", ">=", ">") else val - b[i]
                self.step_text.insert("end",
                    f"  约束{i+1}: 实际值={val:.4g}  {rels[i]}  {b[i]:g}  "
                    f"(松弛={slack:.4g})\n", "vars")

            self.step_text.config(state="disabled")
            self._auto_save()
        except Exception:
            pass

        try:
            self._draw_integer_chart(xvals, c, A, b, rels, opt_v, maximize)
        except Exception:
            pass

    def _solve_priority_goal_branch(self, c, A, b, rels):
        n = len(c)
        names = self.var_names or [f"x{j+1}" for j in range(n)]
        name_to_idx = {name.lower(): j for j, name in enumerate(names)}

        def objective(terms: list[tuple[str, float]]) -> list[float]:
            obj = [0.0] * n
            missing: list[str] = []
            for name, coef in terms:
                idx = name_to_idx.get(name.lower())
                if idx is None:
                    missing.append(name)
                else:
                    obj[idx] = coef
            if missing:
                raise ValueError(f"优先级目标缺少偏差变量：{', '.join(missing)}")
            return obj

        priorities = [
            objective([("dp1", 1.0), ("dm2", 1.0)]),
            objective([("dm3", 1.0)]),
            objective([("dm4", 1.0), ("dm5", 2.0)]),
        ]
        result = solve_preemptive_goal_lp(priorities, A, b, rels)
        if result.status != "optimal":
            messagebox.showerror("求解失败", result.message)
            return

        xvals = result.x

        def nfmt(v):
            if abs(v) < 1e-8:
                return "0"
            if abs(v - round(v)) < 1e-6:
                return str(int(round(v)))
            return f"{v:.4g}"

        for j, lbl in enumerate(self.result_labels):
            lbl.config(text=nfmt(xvals[j]))
        self.opt_label.config(text=", ".join(f"P{i+1}={nfmt(v)}" for i, v in enumerate(result.objective_values)))
        for i in range(len(A)):
            val = result.actual_values[i] if i < len(result.actual_values) else 0.0
            self.actual_labels[i].config(text=nfmt(val))

        try:
            self.step_text.config(state="normal")
            self.step_text.delete("1.0", "end")
            self.step_text.tag_config("title", foreground="#1a5276", font=("宋体", 10, "bold"))
            self.step_text.tag_config("vars", foreground="#196F3D", font=("Courier New", 10))
            self.step_text.tag_config("obj", foreground="#922B21", font=("Courier New", 10, "bold"))
            self.step_text.insert("end", "【优先级目标规划求解结果】\n\n", "title")
            for stage in result.stage_results:
                self.step_text.insert(
                    "end",
                    f"  第{stage.priority}级目标值 = {nfmt(stage.objective_value)}\n",
                    "obj",
                )
            self.step_text.insert("end", "\n【最优解】\n", "title")
            for j, value in enumerate(xvals):
                if abs(value) > 1e-8 or names[j].startswith(("x", "dm", "dp")):
                    self.step_text.insert("end", f"  {self._var_label(j)} = {nfmt(value)}\n", "vars")
            self.step_text.config(state="disabled")
            self._auto_save()
        except Exception:
            pass

        try:
            self._draw_integer_chart(xvals, [0.0] * n, A, b, rels, result.objective_values[-1], False)
        except Exception:
            pass

    # ── 整数规划图形 ────────────────────────────────────────
    def _draw_integer_chart(self, x, c, A, b, rels, opt, maximize):
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np

        for w in self.chart_frame.winfo_children():
            w.destroy()
        self.chart_frame.config(height=0)

        n = len(c)
        active_vars = [j for j in range(n) if c[j] != 0 or any(A[i][j] != 0 for i in range(len(A)))]
        n_active = len(active_vars)

        fig, ax = plt.subplots(1, 1, figsize=(5.5, 4.0), dpi=90)
        fig.patch.set_facecolor("#f5f5f0")

        if n_active == 2 and active_vars == [0, 1]:
            ax.set_facecolor("white")
            title_map = {"纯整数规划": "纯整数规划可行域", "0-1规划": "0-1规划可行域",
                         "混合整数规划": "混合整数规划可行域"}
            ax.set_title(title_map.get(self.title_text, "整数规划可行域"),
                         fontsize=13, fontweight="bold", fontfamily="SimHei")

            x1_max = max([b[i] / A[i][0] for i in range(len(b)) if A[i][0] > 1e-10] + [x[0] * 2 + 2])
            x2_max = max([b[i] / A[i][1] for i in range(len(b)) if A[i][1] > 1e-10] + [x[1] * 2 + 2])
            x1_max *= 1.08; x2_max *= 1.08
            x1v = np.linspace(0, x1_max, 600)
            colors = ["#e74c3c", "#2980b9", "#27ae60", "#8e44ad", "#e67e22"]

            # LP 松弛可行域（半透明填充）
            from scipy.spatial import ConvexHull
            from itertools import combinations
            m_con = len(b)
            A_full = [list(row) for row in A] + [[-1, 0], [0, -1]]
            b_full = list(b) + [0, 0]
            vertices = []
            n_con = len(A_full)
            for i, j in combinations(range(n_con), 2):
                a_mat = np.array([[A_full[i][0], A_full[i][1]],
                                  [A_full[j][0], A_full[j][1]]], dtype=float)
                bv = np.array([b_full[i], b_full[j]], dtype=float)
                try:
                    pt = np.linalg.solve(a_mat, bv)
                    if pt[0] < -1e-6 or pt[1] < -1e-6:
                        continue
                    ok = True
                    for k in range(m_con):
                        lhs = A[k][0] * pt[0] + A[k][1] * pt[1]
                        if rels[k] in ("≤", "<=", "<") and lhs > b[k] + 1e-6: ok = False; break
                        if rels[k] in ("≥", ">=", ">") and lhs < b[k] - 1e-6: ok = False; break
                    if ok:
                        vertices.append(pt)
                except np.linalg.LinAlgError:
                    pass

            if len(vertices) >= 3:
                verts = np.array(vertices)
                try:
                    hull = ConvexHull(verts)
                    hull_pts = verts[hull.vertices]
                    cx2, cy2 = hull_pts.mean(0)
                    angles = np.arctan2(hull_pts[:, 1] - cy2, hull_pts[:, 0] - cx2)
                    hull_pts = hull_pts[np.argsort(angles)]
                    from matplotlib.patches import Polygon as MplPolygon
                    poly = MplPolygon(hull_pts, closed=True, facecolor="#f1948a",
                                     alpha=0.30, edgecolor="none", zorder=1, label="LP松弛可行域")
                    ax.add_patch(poly)
                except Exception:
                    pass

            # 约束线
            for i in range(m_con):
                a1, a2 = A[i][0], A[i][1]
                col = colors[i % len(colors)]
                terms = []
                if abs(a1) > 1e-10:
                    c1v = int(a1) if a1 == int(a1) else round(a1, 3)
                    terms.append(("" if c1v == 1 else str(c1v)) + "$x_1$")
                if abs(a2) > 1e-10:
                    c2v = int(a2) if a2 == int(a2) else round(a2, 3)
                    sign = "+" if a2 > 0 and terms else ""
                    terms.append(sign + ("" if c2v == 1 else str(c2v)) + "$x_2$")
                rhs_v = int(b[i]) if b[i] == int(b[i]) else round(b[i], 3)
                expr_str = "".join(terms) + f"={rhs_v}"
                if abs(a2) > 1e-10:
                    x2v = (b[i] - a1 * x1v) / a2
                    mask = (x2v >= -x2_max * 0.05) & (x2v <= x2_max * 1.05) & (x1v >= 0)
                    if mask.sum() > 1:
                        ax.plot(x1v[mask], x2v[mask], color=col, linewidth=2, zorder=3)
                        idx2 = np.where(mask)[0]
                        mid_idx = idx2[len(idx2) * 2 // 3]
                        ax.text(x1v[mid_idx] + x1_max * 0.01, x2v[mid_idx] + x2_max * 0.01,
                                expr_str, fontsize=8.5, color=col, fontweight="bold", zorder=5)
                elif abs(a1) > 1e-10:
                    xv = b[i] / a1
                    ax.axvline(xv, color=col, linewidth=2, zorder=3)
                    ax.text(xv + x1_max * 0.01, x2_max * 0.6,
                            f"$x_1$={rhs_v}", fontsize=8.5, color=col, fontweight="bold")

            # 整数格点（在可行域内的所有整数点）
            x1_int_max = int(x1_max) + 1
            x2_int_max = int(x2_max) + 1
            int_pts_x, int_pts_y = [], []
            for ix in range(0, x1_int_max + 1):
                for iy in range(0, x2_int_max + 1):
                    ok = True
                    for k in range(m_con):
                        lhs = A[k][0] * ix + A[k][1] * iy
                        if rels[k] in ("≤", "<=", "<") and lhs > b[k] + 1e-6:
                            ok = False; break
                        if rels[k] in ("≥", ">=", ">") and lhs < b[k] - 1e-6:
                            ok = False; break
                    if ok:
                        int_pts_x.append(ix)
                        int_pts_y.append(iy)
            if int_pts_x:
                ax.scatter(int_pts_x, int_pts_y, color="#2471a3", s=28, zorder=5,
                           alpha=0.85, label="整数可行点")

            # 最优整数解
            ox, oy = float(x[0] or 0), float(x[1] or 0)
            ax.plot(ox, oy, "*", color="red", markersize=16, zorder=8, label="最优整数解")
            ox_lbl = f"{int(round(ox))}" if abs(ox - round(ox)) < 1e-4 else f"{ox:.3g}"
            oy_lbl = f"{int(round(oy))}" if abs(oy - round(oy)) < 1e-4 else f"{oy:.3g}"
            ax.annotate(f"最优({ox_lbl},{oy_lbl})\nZ={opt:.4g}",
                        xy=(ox, oy),
                        xytext=(ox + x1_max * 0.04, oy + x2_max * 0.04),
                        fontsize=9, color="red", fontweight="bold", zorder=9,
                        arrowprops=dict(arrowstyle="->", color="red", lw=1.5),
                        fontfamily="SimHei")

            ax.set_xlim(-x1_max * 0.02, x1_max * 1.02)
            ax.set_ylim(-x2_max * 0.02, x2_max * 1.02)
            ax.spines["left"].set_position("zero"); ax.spines["bottom"].set_position("zero")
            ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False)
            ax.plot(x1_max * 1.04, 0, ">k", markersize=6, clip_on=False, zorder=10)
            ax.plot(0, x2_max * 1.04, "^k", markersize=6, clip_on=False, zorder=10)
            ax.grid(True, alpha=0.25, linestyle="--")
            ax.text(x1_max * 1.03, -x2_max * 0.05, "$x_1$", fontsize=12, ha="center")
            ax.text(-x1_max * 0.04, x2_max * 1.03, "$x_2$", fontsize=12, va="center")
            ax.text(-x1_max * 0.04, -x2_max * 0.05, "O", fontsize=10, color="#555")
            ax.legend(fontsize=8, loc="upper right")
        else:
            # 多变量：横向条形图展示最优解各变量值
            ax.set_facecolor("#fafafa")
            fig.set_size_inches(5.5, 3.2)
            labels = [f"$x_{{{j+1}}}$" for j in active_vars]
            vals = [float(x[j] or 0) for j in active_vars]
            y_pos = np.arange(n_active)
            bar_colors = ["#2980b9" if v >= 0 else "#e74c3c" for v in vals]
            ax.barh(y_pos, vals, color=bar_colors, alpha=0.8,
                    edgecolor="#1a5276", height=0.5)
            max_abs = max((abs(v) for v in vals), default=1) or 1
            for i, v in enumerate(vals):
                v_str = str(int(round(v))) if abs(v - round(v)) < 1e-4 else f"{v:.4g}"
                ax.text(v + max_abs * 0.02, i, v_str,
                        va="center", fontsize=9, color="#333")
            ax.set_yticks(y_pos); ax.set_yticklabels(labels, fontsize=10)
            opt_str = str(int(round(opt))) if abs(opt - round(opt)) < 1e-4 else f"{opt:.4g}"
            ax.set_title(f"整数规划最优解  Z = {opt_str}",
                         fontsize=10, fontweight="bold", fontfamily="SimHei")
            ax.set_xlabel("变量值", fontsize=9)
            ax.grid(True, alpha=0.3, axis="x")
            ax.axvline(0, color="gray", linewidth=0.8)

        plt.tight_layout(pad=0.3)
        canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas_widget.draw()
        canvas_widget.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    # ── 灵敏度更新 ────────────────────────────────────────
    def _show_sensitivity(self, x, c, A, b, rels, opt, shadow,
                          c_lo, c_hi, b_lo, b_hi, maximize, c_diff=None):
        INF = 1e30
        BG = "#f8f4eb"; YELL = "#fff59d"; HDR = "#ffd59e"
        PINK = "#f8a5a8"; CYAN = "#c8f1f3"; W = 8
        subs = "₁₂₃₄₅₆₇₈₉"

        def fmt(v):
            if v is None: return "-"
            if abs(v) >= INF * 0.9: return "1E+30" if v > 0 else "-1E+30"
            if abs(v) < 1e-8: return "0"
            if abs(v - round(v)) < 1e-6 and abs(v) < 1e10: return str(int(round(v)))
            return f"{v:.5g}"

        n = len(x)
        m = len(b)

        # 只显示有非零系数的变量和约束
        active_vars = [j for j in range(n)
                       if c[j] != 0 or any(A[i][j] != 0 for i in range(m))]
        active_cons = [i for i in range(m)
                       if b[i] != 0 or any(A[i][j] != 0 for j in range(n))]

        # 清空并重建灵敏度区
        for w in self.out_frame.winfo_children():
            w.destroy()
        self.sens_var_rows = []
        self.sens_con_rows = []

        out = self.out_frame
        LINE = "#c8c8c8"
        ROW_H = 26; HDR_H = 26
        # 变量灵敏度表列宽
        VN_W = 44; VD_W = 68          # 变量名列 / 数据列（5列）
        # 约束灵敏度表列宽
        CI_W = 32; CD_W = 68          # 约束号列 / 数据列（6列）
        nv = len(active_vars)
        nc = len(active_cons)

        def _build_sens_canvas(parent, hdrs, rows_data, col_widths, row_colors):
            """通用 Canvas 灵敏度表构建"""
            ncol = len(col_widths)
            xs = [0]
            for w in col_widths:
                xs.append(xs[-1] + w)
            total_w = xs[-1]
            total_h = HDR_H + len(rows_data) * ROW_H
            cv = tk.Canvas(parent, width=total_w + 1, height=total_h + 1,
                           bg="white", highlightthickness=0, bd=0)
            cv.pack(anchor="w", padx=6, pady=(0, 2))
            # header bg
            cv.create_rectangle(0, 0, total_w, HDR_H, fill=HDR, outline="")
            # data row bg
            for ri, row_vals in enumerate(rows_data):
                for ci, bg in enumerate(row_colors):
                    cv.create_rectangle(xs[ci], HDR_H + ri * ROW_H,
                                        xs[ci + 1], HDR_H + (ri + 1) * ROW_H,
                                        fill=bg, outline="")
            # grid lines
            for y in [0, HDR_H] + [HDR_H + (r + 1) * ROW_H for r in range(len(rows_data))]:
                cv.create_line(0, y, total_w, y, fill=LINE)
            for x in xs:
                cv.create_line(x, 0, x, total_h, fill=LINE)
            # headers
            for ci, (h, x0, x1) in enumerate(zip(hdrs, xs, xs[1:])):
                cv.create_text((x0 + x1) // 2, HDR_H // 2, text=h,
                               font=("宋体", 9), fill="#333")
            # data cells (Labels via create_window)
            cell_refs = []
            for ri, row_vals in enumerate(rows_data):
                cy = HDR_H + ri * ROW_H + ROW_H // 2
                row_lbls = []
                for ci, (val, bg, x0, x1) in enumerate(zip(row_vals, row_colors, xs, xs[1:])):
                    ll = tk.Label(cv, text=val, bg=bg, font=("宋体", 9), relief="flat")
                    cv.create_window((x0 + x1) // 2, cy, window=ll,
                                     width=x1 - x0 - 2, height=ROW_H - 4)
                    row_lbls.append(ll)
                cell_refs.append(row_lbls)
            return cv, cell_refs

        # ── 目标函数变量系数表 ──
        tk.Label(out, text="最优方案  ·  目标函数变量系数", bg=BG,
                 font=("宋体", 10, "bold")).pack(anchor="w", padx=6, pady=(3, 1))
        var_hdrs = ["变量", "最优解", "相差值", "下限", "当前值", "上限"]
        var_col_w = [VN_W] + [VD_W] * 5
        var_colors = [BG, CYAN, YELL, "#e0e0ff", YELL, "#e0e0ff"]
        var_rows_data = []
        for j in active_vars:
            cur = c[j]; lo = c_lo[j] if j < len(c_lo) else -INF
            hi = c_hi[j] if j < len(c_hi) else INF
            diff = c_diff[j] if c_diff and j < len(c_diff) else 0.0
            vname = self._var_label(j)
            var_rows_data.append([vname, fmt(x[j]), fmt(diff), fmt(lo), fmt(cur), fmt(hi)])
        _, self.sens_var_rows = _build_sens_canvas(
            out, var_hdrs, var_rows_data, var_col_w, var_colors)

        # ── 约束条件常数项表 ──
        tk.Label(out, text="约束条件  ·  约束条件常数项", bg=BG,
                 font=("宋体", 10, "bold")).pack(anchor="w", padx=6, pady=(4, 1))
        con_hdrs = ["约束", "实际值", "松弛剩余", "对偶价格", "下限", "当前值", "上限"]
        con_col_w = [CI_W] + [CD_W] * 6
        con_colors = [BG, PINK, YELL, "#ffe0e0", "#e0e0ff", YELL, "#e0e0ff"]
        con_rows_data = []
        for i in active_cons:
            actual = sum(A[i][j] * x[j] for j in range(n))
            slack = b[i] - actual if rels[i] not in ("≥", ">=", ">") else actual - b[i]
            sp = shadow[i] if i < len(shadow) else 0
            lo = b_lo[i] if i < len(b_lo) else -INF
            hi = b_hi[i] if i < len(b_hi) else INF
            con_rows_data.append([str(i + 1), fmt(actual), fmt(slack),
                                   fmt(sp), fmt(lo), fmt(b[i]), fmt(hi)])
        _, self.sens_con_rows = _build_sens_canvas(
            out, con_hdrs, con_rows_data, con_col_w, con_colors)

        zero_slack = sum(1 for j in range(n) if abs(x[j]) < 1e-6)
        conclusion = ("本模型存在唯一解，且存在对应的唯一对偶价格" if zero_slack > 0
                      else "本模型最优解已求得")
        self.conclusion_label = tk.Label(out, text=conclusion, bg=BG,
                                         font=("宋体", 10), fg="#cc0000")
        self.conclusion_label.pack(anchor="w", padx=8, pady=(2, 1))

        try:
            self._draw_chart(x, c, A, b, rels, opt, c_lo, c_hi, b_lo, b_hi, maximize)
        except Exception:
            pass

        # 更新表达式框
        def coef_str(v, j, first=False):
            if v == 0: return ""
            vn = xname(j)
            s = f"{abs(v):g}{vn}"
            if first: return f"-{s}" if v < 0 else s
            return f" - {s}" if v < 0 else f" + {s}"

        obj_type = "max" if maximize else "min"
        obj_parts = [p for p in [coef_str(c[j], j, j == 0) for j in range(n)] if p]
        lines = [f"{obj_type}  Z = {'  '.join(obj_parts) or '0'}", "", "s.t."]
        for i in range(m):
            parts = [p for p in [coef_str(A[i][j], j, j == 0) for j in range(n)] if p]
            lines.append(f"  {'  '.join(parts) or '0'}  {rels[i]}  {b[i]:g}")
        active = [j for j in range(n) if c[j] != 0 or any(A[i][j] != 0 for i in range(m))]
        lines += [""] + [f"  x{j+1} >= 0" for j in active]
        active_sol = active if active else list(range(n))
        lines += ["", f"最优解: " + ",  ".join(f"{xname(j)}={fmt(x[j])}" for j in active_sol)]
        lines.append(f"最优值: Z = {fmt(opt)}")

        try:
            self.step_text.config(state="normal")
            self.step_text.insert("end", "\n" + "─" * 50 + "\n", "sep")
            self.step_text.insert("end", "【求解结果】\n", "title")
            self.step_text.insert("end", "  " + "\n  ".join(lines) + "\n", "vars")
            self.step_text.config(state="disabled")
            self.step_text.see("end")
        except Exception:
            pass

    # ── 可行域 / 灵敏度图 ────────────────────────────────
    def _draw_chart(self, x, c, A, b, rels, opt, c_lo, c_hi, b_lo, b_hi, maximize):
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np

        for w in self.chart_frame.winfo_children():
            w.destroy()
        self.chart_frame.config(height=0)

        # 单纯形步骤
        step_text = self.step_text
        step_text.config(state="normal")
        step_text.delete("1.0", "end")
        step_text.tag_config("title",   foreground="#1a5276", font=("宋体", 10, "bold"))
        step_text.tag_config("note",    foreground="#333333", font=("Courier New", 10))
        step_text.tag_config("vars",    foreground="#196F3D", font=("Courier New", 10))
        step_text.tag_config("obj",     foreground="#922B21", font=("Courier New", 10, "bold"))
        step_text.tag_config("sep",     foreground="#aaaaaa", font=("Courier New", 9))
        try:
            A_ub_only = [A[i] for i in range(len(A)) if rels[i] in ("≤", "<=", "<")]
            b_ub_only = [b[i] for i in range(len(b)) if rels[i] in ("≤", "<=", "<")]
            steps = simplex_steps(c, A_ub_only, b_ub_only, maximize)
            n_v = len(c)
            for s in steps:
                step_text.insert("end", "─" * 50 + "\n", "sep")
                step_text.insert("end", f"【{s['title']}】\n", "title")
                step_text.insert("end", f"  {s['note']}\n", "note")
                if "basic" in s:
                    xvals = {s["basic"][k]: s["x_B"][k] for k in range(len(s["basic"]))}
                    xline = "   ".join(
                        xname(j) + f"={xvals.get(xname(j), 0):.4g}"
                        for j in range(n_v))
                    step_text.insert("end", f"  决策变量: {xline}\n", "vars")
                    bline = "   ".join(f"{s['basic'][k]}={s['x_B'][k]:.4g}"
                                       for k in range(len(s["basic"])))
                    step_text.insert("end", f"  基变量:   {bline}\n", "vars")
                if "obj" in s and s["obj"] != 0:
                    step_text.insert("end", f"  目标值:   Z = {s['obj']:.6g}\n", "obj")
        except Exception as e:
            step_text.insert("end", f"步骤计算出错: {e}")
        step_text.config(state="disabled")

        n = len(c)
        # 统计实际有非零系数的变量数（用于判断显示可行域图还是灵敏度图）
        active_vars = [j for j in range(n) if c[j] != 0 or any(A[i][j] != 0 for i in range(len(A)))]
        n_active = len(active_vars)
        INF = 1e30
        fig, ax = plt.subplots(1, 1, figsize=(5.5, 4.0), dpi=90)
        fig.patch.set_facecolor("#f5f5f0")

        if n_active == 2 and active_vars == [0, 1]:
            ax.set_facecolor("white")
            ax.set_title("可行域", fontsize=13, fontweight="bold", fontfamily="SimHei")
            x1_max = max([b[i] / A[i][0] for i in range(len(b)) if A[i][0] > 1e-10] + [x[0] * 2 + 1])
            x2_max = max([b[i] / A[i][1] for i in range(len(b)) if A[i][1] > 1e-10] + [x[1] * 2 + 1])
            x1_max *= 1.08; x2_max *= 1.08
            x1v = np.linspace(0, x1_max, 600)
            colors = ["#e74c3c", "#2980b9", "#27ae60", "#8e44ad", "#e67e22"]
            from scipy.spatial import ConvexHull
            from itertools import combinations
            m_con = len(b)
            A_full = [list(row) for row in A] + [[-1, 0], [0, -1]]
            b_full = list(b) + [0, 0]
            vertices = []
            n_con = len(A_full)
            for i, j in combinations(range(n_con), 2):
                a = np.array([[A_full[i][0], A_full[i][1]],
                              [A_full[j][0], A_full[j][1]]], dtype=float)
                bv = np.array([b_full[i], b_full[j]], dtype=float)
                try:
                    pt = np.linalg.solve(a, bv)
                    if pt[0] < -1e-6 or pt[1] < -1e-6: continue
                    ok = True
                    for k in range(m_con):
                        lhs = A[k][0] * pt[0] + A[k][1] * pt[1]
                        if rels[k] in ("≤", "<=", "<") and lhs > b[k] + 1e-6: ok = False; break
                        if rels[k] in ("≥", ">=", ">") and lhs < b[k] - 1e-6: ok = False; break
                    if ok: vertices.append(pt)
                except np.linalg.LinAlgError:
                    pass
            if len(vertices) >= 3:
                verts = np.array(vertices)
                try:
                    hull = ConvexHull(verts)
                    hull_pts = verts[hull.vertices]
                    cx, cy = hull_pts.mean(0)
                    angles = np.arctan2(hull_pts[:, 1] - cy, hull_pts[:, 0] - cx)
                    hull_pts = hull_pts[np.argsort(angles)]
                    from matplotlib.patches import Polygon as MplPolygon
                    poly = MplPolygon(hull_pts, closed=True, facecolor="#f1948a",
                                      alpha=0.7, edgecolor="none", zorder=1)
                    ax.add_patch(poly)
                except Exception:
                    pass
            for i in range(m_con):
                a1, a2 = A[i][0], A[i][1]
                col = colors[i % len(colors)]
                terms = []
                if abs(a1) > 1e-10:
                    c1 = int(a1) if a1 == int(a1) else round(a1, 3)
                    terms.append(("" if c1 == 1 else str(c1)) + "$x_1$")
                if abs(a2) > 1e-10:
                    c2 = int(a2) if a2 == int(a2) else round(a2, 3)
                    sign = "+" if a2 > 0 and terms else ""
                    terms.append(sign + ("" if c2 == 1 else str(c2)) + "$x_2$")
                rhs = int(b[i]) if b[i] == int(b[i]) else round(b[i], 3)
                expr_str = "".join(terms) + f"={rhs}"
                if abs(a2) > 1e-10:
                    x2v = (b[i] - a1 * x1v) / a2
                    mask = (x2v >= -x2_max * 0.05) & (x2v <= x2_max * 1.05) & (x1v >= 0)
                    if mask.sum() > 1:
                        ax.plot(x1v[mask], x2v[mask], color=col, linewidth=2, zorder=3)
                        idx = np.where(mask)[0]
                        mid_idx = idx[len(idx) * 2 // 3]
                        ax.text(x1v[mid_idx] + x1_max * 0.01, x2v[mid_idx] + x2_max * 0.01,
                                expr_str, fontsize=8.5, color=col, fontweight="bold", zorder=5)
                elif abs(a1) > 1e-10:
                    xv = b[i] / a1
                    ax.axvline(xv, color=col, linewidth=2, zorder=3)
                    ax.text(xv + x1_max * 0.01, x2_max * 0.6,
                            f"$x_1$={rhs}", fontsize=8.5, color=col, fontweight="bold")
            ALPHA = "ABCDEFGHIJ"
            for idx2, pt in enumerate(sorted(vertices, key=lambda p: (round(p[0], 1), round(p[1], 1)))):
                ax.plot(pt[0], pt[1], "o", color="#333", markersize=6, zorder=6)
                lbl = f"{ALPHA[idx2]}({int(pt[0]) if abs(pt[0]-round(pt[0]))<0.01 else pt[0]:.3g},"
                lbl += f"{int(pt[1]) if abs(pt[1]-round(pt[1]))<0.01 else pt[1]:.3g})"
                ax.annotate(lbl, xy=(pt[0], pt[1]), xytext=(6, 4), textcoords="offset points",
                            fontsize=8, color="#333", fontweight="bold", zorder=7)
            ax.plot(x[0], x[1], "*", color="red", markersize=16, zorder=8)
            opt_lbl = (f"最优点({int(x[0]) if abs(x[0]-round(x[0]))<0.01 else x[0]:.3g},"
                       f"{int(x[1]) if abs(x[1]-round(x[1]))<0.01 else x[1]:.3g})\nZ={opt:.4g}")
            ax.annotate(opt_lbl, xy=(x[0], x[1]),
                        xytext=(x[0] + x1_max * 0.04, x[1] + x2_max * 0.04),
                        fontsize=9, color="red", fontweight="bold", zorder=9,
                        arrowprops=dict(arrowstyle="->", color="red", lw=1.5),
                        fontfamily="SimHei")
            ax.set_xlim(-x1_max * 0.02, x1_max * 1.02)
            ax.set_ylim(-x2_max * 0.02, x2_max * 1.02)
            ax.spines["left"].set_position("zero"); ax.spines["bottom"].set_position("zero")
            ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False)
            ax.plot(x1_max * 1.04, 0, ">k", markersize=6, clip_on=False, zorder=10)
            ax.plot(0, x2_max * 1.04, "^k", markersize=6, clip_on=False, zorder=10)
            ax.grid(True, alpha=0.25, linestyle="--")
            ax.text(x1_max * 1.03, -x2_max * 0.05, "$x_1$", fontsize=12, ha="center")
            ax.text(-x1_max * 0.04, x2_max * 1.03, "$x_2$", fontsize=12, va="center")
            ax.text(-x1_max * 0.04, -x2_max * 0.05, "O", fontsize=10, color="#555")
        else:
            ax.set_facecolor("#fafafa")
            fig.set_size_inches(5.5, 3.2)
            labels = [f"$x_{{{j+1}}}$" for j in range(n)]
            cur_vals = np.array(c, dtype=float)
            lo_vals = np.array([v if v > -INF * 0.9 else cur_vals[j] - cur_vals[j] * 2
                                for j, v in enumerate(c_lo)])
            hi_vals = np.array([v if v < INF * 0.9 else cur_vals[j] + cur_vals[j] * 2
                                for j, v in enumerate(c_hi)])
            y_pos = np.arange(n)
            ax.barh(y_pos, hi_vals - lo_vals, left=lo_vals,
                    color="#aed6f1", edgecolor="#2980b9", height=0.5, alpha=0.8)
            ax.scatter(cur_vals, y_pos, color="red", zorder=5, s=50)
            ax.scatter(np.array(x), y_pos - 0.25, color="green", zorder=5, s=40, marker="D")
            ax.set_yticks(y_pos); ax.set_yticklabels(labels, fontsize=10)
            ax.set_title("Sensitivity Range of Objective Coefficients", fontsize=10, fontweight="bold")
            ax.set_xlabel("系数值", fontsize=9)
            ax.grid(True, alpha=0.3, axis="x")
            ax.axvline(0, color="gray", linewidth=0.5)
            for j in range(n):
                lo_str = f"{c_lo[j]:.4g}" if c_lo[j] > -INF * 0.9 else "-∞"
                hi_str = f"{c_hi[j]:.4g}" if c_hi[j] < INF * 0.9 else "+∞"
                ax.text(lo_vals[j], y_pos[j] + 0.28, f"[{lo_str}, {hi_str}]",
                        fontsize=7, color="#333", va="bottom")

        plt.tight_layout(pad=0.3)
        canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas_widget.draw()
        canvas_widget.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    # ── 表达式互转 ────────────────────────────────────────
    def _table_to_expr(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成表格"); return
        try:
            c, A, b, rels = self._get_data()
            n, m = len(c), len(b)
            maximize = (self.obj_type.get() == "最大化")

            if self._is_table_mode():
                prefix = "max" if maximize else "min"
                lines = [prefix, " ".join(self._format_number(v) for v in c)]
                for i in range(m):
                    row = [self._format_number(A[i][j]) for j in range(n)]
                    rel = rels[i].replace("≤", "<=").replace("≥", ">=")
                    row.append(rel)
                    row.append(self._format_number(b[i]))
                    lines.append(" ".join(row))
                self.main_expr_text.delete("1.0", "end")
                self.main_expr_text.insert("end", "\n".join(lines))
                return
            def term(v, j, first=False):
                if v == 0: return ""
                vstr = str(int(v)) if v == int(v) else str(v)
                xstr = self._var_label(j)
                if first: return f"-{vstr}{xstr}" if v < 0 else f"{vstr}{xstr}"
                return f" - {vstr}{xstr}" if v < 0 else f" + {vstr}{xstr}"

            obj_str = "".join(t for t in [term(c[j], j, j == 0) for j in range(n)] if t) or "0"
            prefix = "max" if maximize else "min"
            lines = [f"{prefix}  Z = {obj_str}", "", "s.t."]
            for i in range(m):
                lhs = "".join(t for t in [term(A[i][j], j, j == 0) for j in range(n)] if t) or "0"
                rel = rels[i].replace("≤", "<=").replace("≥", ">=")
                rhs = str(int(b[i])) if b[i] == int(b[i]) else str(b[i])
                lines.append(f"  {lhs} {rel} {rhs}")
            active2 = [j for j in range(n) if c[j] != 0 or any(A[i][j] != 0 for i in range(m))]
            lines += [""] + [self._var_label(j) + " >= 0" for j in (active2 if active2 else range(n))]
            self.main_expr_text.delete("1.0", "end")
            self.main_expr_text.insert("end", "\n".join(lines))
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _expr_to_table(self):
        try:
            raw = self.main_expr_text.get("1.0", "end").strip()
            if self._is_table_mode():
                parsed = parse_table_lp_expr(raw)
            elif self._looks_like_numeric_matrix(raw):
                parsed = parse_lp_data_matrix(
                    raw,
                    maximize=(self.obj_type.get() == "最大化"),
                )
            else:
                parsed = parse_lp_expr(raw)
            self._fill_from_parsed_model(parsed)
            messagebox.showinfo(
                "解析成功",
                f"已填入：{parsed['n_vars']}个变量，{parsed['n_cons']}个约束",
            )
        except Exception as e:
            messagebox.showerror("解析错误", str(e))

    def _fill_from_parsed_model(self, parsed: dict) -> None:
        n = parsed["n_vars"]
        m = parsed["n_cons"]
        self.var_names = parsed.get("var_names")
        self.obj_type.set("最大化" if parsed["maximize"] else "最小化")
        self.n_vars.set(n)
        self.n_cons.set(m)
        self.entries_built = False
        self._build_table()

        obj_coefs = parsed["obj_coefs"]
        constraints = parsed["constraints"]

        for j in range(n):
            value = obj_coefs.get(j, 0)
            self.obj_entries[j].delete(0, "end")
            if abs(value) > 1e-12:
                self.obj_entries[j].insert(0, self._format_number(value))

        for i, con in enumerate(constraints):
            coefs = con["coefs"]
            for j in range(n):
                value = coefs.get(j, 0)
                self.con_entries[i][j].delete(0, "end")
                if abs(value) > 1e-12:
                    self.con_entries[i][j].insert(0, self._format_number(value))
            self.rel_vars[i].set(con["rel"])
            self.rhs_entries[i].delete(0, "end")
            self.rhs_entries[i].insert(0, self._format_number(con["rhs"]))

        var_types = parsed.get("var_types")
        if (
            self._uses_var_type_controls()
            and var_types
            and hasattr(self, "var_type_vars")
        ):
            for j, var_type in enumerate(var_types):
                if j < len(self.var_type_vars):
                    self.var_type_vars[j].set(
                        self._default_var_type(j) if self.title_text == "投资与选址" else var_type
                    )

    @staticmethod
    def _format_number(value: float) -> str:
        return str(int(value)) if float(value).is_integer() else str(value)

    # ── 自动保存 / 导入 ──────────────────────────────────
    def _auto_save(self):
        if not self.entries_built:
            return
        try:
            c, A, b, rels = self._get_data()
            data = {"title": self.title_text,
                    "n_vars": self.n_vars.get(), "n_cons": self.n_cons.get(),
                    "obj_type": self.obj_type.get(),
                    "c": c, "A": A, "b": b, "rels": rels}
            autosave.save(self.title_text, data)
        except Exception:
            pass

    def _prompt_auto_load(self):
        data = autosave.load(self.title_text)
        if not data:
            messagebox.showinfo("恢复历史", "暂无历史数据"); return
        try:
            self.n_vars.set(data["n_vars"])
            self.n_cons.set(data["n_cons"])
            self.obj_type.set(data.get("obj_type", "最大化"))
            self.entries_built = False
            self._build_table()
            for j, v in enumerate(data["c"]):
                self.obj_entries[j].delete(0, "end")
                self.obj_entries[j].insert(0, str(v))
            for i in range(data["n_cons"]):
                for j, v in enumerate(data["A"][i]):
                    self.con_entries[i][j].delete(0, "end")
                    if v != 0:
                        self.con_entries[i][j].insert(0, str(v))
                self.rhs_entries[i].delete(0, "end")
                self.rhs_entries[i].insert(0, str(data["b"][i]))
                self.rel_vars[i].set(data["rels"][i])
            self._table_to_expr()
            messagebox.showinfo("恢复历史", "历史数据已恢复")
        except Exception as e:
            messagebox.showerror("恢复失败", str(e))

    def _save(self):
        if not self.entries_built: return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON文件", "*.json")], title="存盘")
        if not path: return
        c, A, b, rels = self._get_data()
        data = {"title": self.title_text, "n_vars": self.n_vars.get(),
                "n_cons": self.n_cons.get(), "obj_type": self.obj_type.get(),
                "c": c, "A": A, "b": b, "rels": rels}
        autosave.save_to_path(path, data)
        messagebox.showinfo("存盘", f"已保存到 {path}")

    def _load(self):
        path = filedialog.askopenfilename(filetypes=[("JSON文件", "*.json")], title="导入")
        if not path: return
        data = autosave.load_from_path(path)
        if not data:
            messagebox.showerror("导入失败", "文件读取失败"); return
        self.n_vars.set(data["n_vars"])
        self.n_cons.set(data["n_cons"])
        self.obj_type.set(data["obj_type"])
        self._build_table()
        for j, v in enumerate(data["c"]):
            self.obj_entries[j].delete(0, "end")
            self.obj_entries[j].insert(0, str(v))
        for i in range(data["n_cons"]):
            for j, v in enumerate(data["A"][i]):
                self.con_entries[i][j].delete(0, "end")
                if v != 0:
                    self.con_entries[i][j].insert(0, str(v))
            self.rhs_entries[i].delete(0, "end")
            self.rhs_entries[i].insert(0, str(data["b"][i]))
            self.rel_vars[i].set(data["rels"][i])
        messagebox.showinfo("导入", "数据导入成功")
