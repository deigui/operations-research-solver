"""线性规划 / 整数规划求解页。"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from or_solver.constants import FONT_SMALL, xname
from or_solver.core.lp_solver import solve_lp, solve_integer_lp, simplex_steps
from or_solver.io import autosave
from or_solver.utils.expr_parser import normalize_expr
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
        self.n_vars = tk.IntVar(value=2)
        self.n_cons = tk.IntVar(value=2)
        self.obj_type = tk.StringVar(value="最大化")
        self.entries_built = False
        self._build_header()

    # ── 布局构建 ────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg="#c8b89a", relief="raised", bd=1)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"运筹学模型求解系统———{self.title_text}",
                 font=("宋体", 13, "bold"), bg="#c8b89a", fg="#222").pack(pady=4)
        ctrl = tk.Frame(hdr, bg="#c8b89a")
        ctrl.pack(pady=(0, 4))
        tk.Label(ctrl, text="决策变量个数:", bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(8, 0))
        tk.Spinbox(ctrl, from_=1, to=20, textvariable=self.n_vars, width=4,
                   font=FONT_SMALL, relief="sunken").pack(side="left", padx=2)
        tk.Label(ctrl, text="约束条件个数:", bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(12, 0))
        tk.Spinbox(ctrl, from_=1, to=30, textvariable=self.n_cons, width=4,
                   font=FONT_SMALL, relief="sunken").pack(side="left", padx=2)
        tk.Radiobutton(ctrl, text="最大化", variable=self.obj_type, value="最大化",
                       bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(12, 2))
        tk.Radiobutton(ctrl, text="最小化", variable=self.obj_type, value="最小化",
                       bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=2)
        tk.Button(ctrl, text="确  定", command=self._build_table,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=8)
        tk.Button(ctrl, text="求  解", command=self._solve,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=2)
        tk.Button(ctrl, text="返  回", command=self.controller.show_menu,
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

        left_pane = tk.Frame(main_pane, bg="#e8e0d0")
        main_pane.add(left_pane, minsize=400, width=750)

        left_pw = tk.PanedWindow(left_pane, orient="vertical", bg="#888",
                                 sashwidth=5, sashrelief="raised", sashpad=2)
        left_pw.pack(fill="both", expand=True)

        expr_frame = tk.Frame(left_pw, bg="#f5f0e0", relief="groove", bd=1)
        left_pw.add(expr_frame, minsize=80, height=220)
        top_row = tk.Frame(expr_frame, bg="#f5f0e0")
        top_row.pack(fill="x", padx=6, pady=(4, 2))
        tk.Label(top_row, text="模型表达式（输入或粘贴）:",
                 bg="#f5f0e0", font=("宋体", 9, "bold")).pack(side="left")
        tk.Button(top_row, text="解析填入表格", command=self._expr_to_table,
                  bg="#90ee90", font=("宋体", 9), width=12).pack(side="left", padx=6)
        tk.Button(top_row, text="从表格刷新", command=self._table_to_expr,
                  bg="#87ceeb", font=("宋体", 9), width=10).pack(side="left", padx=2)
        tk.Button(top_row, text="清  空",
                  command=lambda: self.main_expr_text.delete("1.0", "end"),
                  bg="#ffcccc", font=("宋体", 9), width=6).pack(side="left", padx=2)
        self.main_expr_text = tk.Text(expr_frame, font=("Consolas", 10), bg="#fffff0",
                                      relief="sunken", bd=1)
        self.main_expr_text.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self.main_expr_text.insert("1.0",
            "max  Z = 15x1 + 10x2 + 7x3\ns.t.\n  5x1 + 10x2 + 7x3 <= 8000\n  x1 >= 0")

        left_bottom = tk.Frame(left_pw, bg="#e8e0d0")
        left_pw.add(left_bottom, minsize=200)
        vsb = tk.Scrollbar(left_bottom, orient="vertical")
        hsb = tk.Scrollbar(left_bottom, orient="horizontal")
        canvas = tk.Canvas(left_bottom, bg="#e8e0d0", width=700,
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=canvas.yview)
        hsb.config(command=canvas.xview)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(canvas, bg="#e8e0d0")
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
        BG = "#e8e0d0"; YELL = "#ffff99"; GRN = "#ccffcc"
        PINK = "#ff9999"; CYAN = "#ccffff"; HDR = "#ffcc99"; W = 7
        subs = "₁₂₃₄₅₆₇₈₉"

        tk.Label(self.body, text="目标函数系数", bg=BG,
                 font=("宋体", 10, "bold")).grid(row=0, column=0, sticky="w",
                 padx=4, pady=(4, 0), columnspan=n + 2)
        for j in range(n):
            vname = f"x{subs[j]}" if j < len(subs) else f"x{j+1}"
            tk.Label(self.body, text=vname, bg=HDR, font=("宋体", 10),
                     relief="ridge", width=W).grid(row=1, column=j + 1, padx=1, pady=1)
        self.obj_entries: list[tk.Entry] = []
        for j in range(n):
            e = tk.Entry(self.body, width=W, font=("宋体", 10), bg=YELL, relief="sunken", bd=1)
            e.grid(row=2, column=j + 1, padx=1, pady=1)
            self._bind_cell(e, 0, j)
            self.obj_entries.append(e)

        tk.Label(self.body, text="约束条件系数", bg=BG,
                 font=("宋体", 10, "bold")).grid(row=3, column=0, sticky="w",
                 padx=4, pady=(6, 0), columnspan=n + 4)
        tk.Label(self.body, text="", bg=BG, width=3).grid(row=4, column=0)
        for j in range(n):
            vname = f"x{subs[j]}" if j < len(subs) else f"x{j+1}"
            tk.Label(self.body, text=vname, bg=HDR, font=("宋体", 10),
                     relief="ridge", width=W).grid(row=4, column=j + 1, padx=1, pady=1)
        tk.Label(self.body, text="约束条件实际值", bg=HDR, font=("宋体", 10),
                 relief="ridge", width=14).grid(row=4, column=n + 1, padx=1, pady=1)
        tk.Label(self.body, text="约束关系", bg=HDR, font=("宋体", 10),
                 relief="ridge", width=10).grid(row=4, column=n + 2, padx=1, pady=1)
        tk.Label(self.body, text="约束条件常数项", bg=HDR, font=("宋体", 10),
                 relief="ridge", width=14).grid(row=4, column=n + 3, padx=1, pady=1)

        self.con_entries: list[list[tk.Entry]] = []
        self.rel_vars: list[tk.StringVar] = []
        self.rhs_entries: list[tk.Entry] = []
        self.actual_labels: list[tk.Label] = []
        for i in range(m):
            row = 5 + i
            tk.Label(self.body, text=str(i + 1), bg=BG,
                     font=("宋体", 10), width=3).grid(row=row, column=0, padx=2)
            row_e = []
            for j in range(n):
                e = tk.Entry(self.body, width=W, font=("宋体", 10), bg=GRN, relief="sunken", bd=1)
                e.grid(row=row, column=j + 1, padx=1, pady=1)
                self._bind_cell(e, i + 1, j)
                row_e.append(e)
            self.con_entries.append(row_e)
            al = tk.Label(self.body, text="0", bg=PINK, font=("宋体", 10),
                          relief="sunken", width=14)
            al.grid(row=row, column=n + 1, padx=1, pady=1)
            self.actual_labels.append(al)
            rv = tk.StringVar(value="≤")
            cb = ttk.Combobox(self.body, textvariable=rv,
                              values=["≤", "≥", "=", "<", ">"], width=4,
                              font=("宋体", 10), state="readonly")
            cb.grid(row=row, column=n + 2, padx=1, pady=1)
            self.rel_vars.append(rv)
            rhs = tk.Entry(self.body, width=14, font=("宋体", 10), bg="#ccccff", relief="sunken", bd=1)
            rhs.grid(row=row, column=n + 3, padx=1, pady=1)
            self._bind_cell(rhs, i + 1, n)
            self.rhs_entries.append(rhs)

        VAR_ROW = 5 + m + 1
        self.var_type_vars: list[tk.StringVar] = []
        if self.title_text == "混合整数规划":
            tk.Label(self.body, text="变量类型", bg=BG,
                     font=("宋体", 9, "bold")).grid(row=VAR_ROW, column=0, sticky="w", padx=4, pady=(6, 2))
            tk.Label(self.body, text="(C=连续 I=整数 B=0-1)",
                     bg=BG, font=("宋体", 8), fg="#666").grid(
                     row=VAR_ROW, column=1, columnspan=min(n, 6), sticky="w")
            VAR_ROW += 1
            for j in range(n):
                vt = tk.StringVar(value="C")
                cb2 = ttk.Combobox(self.body, textvariable=vt,
                                   values=["C", "I", "B"], width=3,
                                   font=("宋体", 9), state="readonly")
                cb2.grid(row=VAR_ROW, column=j + 1, padx=1, pady=1)
                self.var_type_vars.append(vt)
            VAR_ROW += 2
        else:
            VAR_ROW += 1

        R0 = VAR_ROW
        tk.Label(self.body, text="最优解", bg=BG,
                 font=("宋体", 10, "bold"), width=6).grid(row=R0, column=0, sticky="w", padx=4)
        self.result_labels: list[tk.Label] = []
        for j in range(n):
            rl = tk.Label(self.body, text="", bg=CYAN, font=("宋体", 10),
                          relief="sunken", width=W)
            rl.grid(row=R0, column=j + 1, padx=1, pady=1)
            self.result_labels.append(rl)
        tk.Label(self.body, text="最优值", bg=BG,
                 font=("宋体", 10, "bold")).grid(row=R0, column=n + 2, sticky="e", padx=2)
        self.opt_label = tk.Label(self.body, text="", bg=PINK,
                                  font=("宋体", 11, "bold"), relief="sunken", width=W)
        self.opt_label.grid(row=R0, column=n + 3, padx=1, pady=1)

        R1 = R0 + 2
        tk.Label(self.body, text="最优方案", bg=BG,
                 font=("宋体", 10, "bold")).grid(row=R1, column=0, sticky="w", padx=4, pady=(6, 0))
        tk.Label(self.body, text="目标函数变量系数", bg=BG,
                 font=("宋体", 9, "bold")).grid(row=R1, column=3, columnspan=3, padx=1)
        R1 += 1
        for k, h in enumerate(["变量", "最优解", "相差值", "下限", "当前值", "上限"]):
            tk.Label(self.body, text=h, bg=HDR, font=("宋体", 9),
                     relief="ridge", width=W).grid(row=R1, column=k + 1, padx=1, pady=1)
        R1 += 1
        self.sens_var_rows: list[list[tk.Label]] = []
        for j in range(n):
            row_lbls = []
            for k in range(6):
                bg = [BG, CYAN, YELL, "#e0e0ff", YELL, "#e0e0ff"][k]
                ll = tk.Label(self.body, text="-", bg=bg, font=("宋体", 9),
                              relief="sunken", width=W)
                ll.grid(row=R1 + j, column=k + 1, padx=1, pady=1)
                row_lbls.append(ll)
            self.sens_var_rows.append(row_lbls)

        R2 = R1 + n + 1
        tk.Label(self.body, text="约束条件", bg=BG,
                 font=("宋体", 10, "bold")).grid(row=R2, column=0, sticky="w", padx=4, pady=(4, 0))
        tk.Label(self.body, text="约束条件常数项", bg=BG,
                 font=("宋体", 9, "bold")).grid(row=R2, column=5, columnspan=3, padx=1)
        R2 += 1
        for k, h in enumerate(["约束", "实际值", "松弛剩余", "对偶价格", "下限", "当前值", "上限"]):
            tk.Label(self.body, text=h, bg=HDR, font=("宋体", 9),
                     relief="ridge", width=W).grid(row=R2, column=k + 1, padx=1, pady=1)
        R2 += 1
        self.sens_con_rows: list[list[tk.Label]] = []
        for i in range(m):
            row_lbls = []
            for k in range(7):
                bg = [BG, PINK, YELL, "#ffe0e0", "#e0e0ff", YELL, "#e0e0ff"][k]
                ll = tk.Label(self.body, text="-", bg=bg, font=("宋体", 9),
                              relief="sunken", width=W)
                ll.grid(row=R2 + i, column=k + 1, padx=1, pady=1)
                row_lbls.append(ll)
            self.sens_con_rows.append(row_lbls)

        self.conclusion_label = tk.Label(self.body, text="", bg=BG,
                                         font=("宋体", 10), fg="#cc0000")
        self.conclusion_label.grid(row=R2 + m + 1, column=0, columnspan=10,
                                   sticky="w", padx=4, pady=(4, 2))
        self.entries_built = True

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

            # 整数规划分支
            if self.binary_vars or self.integer_vars or self.title_text == "混合整数规划":
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
        if self.title_text == "混合整数规划" and hasattr(self, "var_type_vars") and self.var_type_vars:
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
            self.step_text.insert("end", "【整数规划求解结果】\n\n", "title")
            self.step_text.tag_config("title", foreground="#1a5276", font=("宋体", 10, "bold"))
            for j in range(n):
                vt = (self.var_type_vars[j].get()
                      if hasattr(self, "var_type_vars") and j < len(self.var_type_vars) else "?")
                v = xvals[j] or 0.0
                self.step_text.insert("end", f"  x{j+1}({vt}) = {v:.4g}\n")
            self.step_text.insert("end", f"\n  最优值 Z = {opt_v:.4g}\n")
            self.step_text.config(state="disabled")
            self._auto_save()
        except Exception:
            pass

    # ── 灵敏度更新 ────────────────────────────────────────
    def _show_sensitivity(self, x, c, A, b, rels, opt, shadow,
                          c_lo, c_hi, b_lo, b_hi, maximize, c_diff=None):
        INF = 1e30
        subs = "₁₂₃₄₅₆₇₈₉"

        def fmt(v):
            if v is None: return "-"
            if abs(v) >= INF * 0.9: return "1E+30" if v > 0 else "-1E+30"
            if abs(v) < 1e-8: return "0"
            if abs(v - round(v)) < 1e-6 and abs(v) < 1e10: return str(int(round(v)))
            return f"{v:.5g}"

        n = len(x)
        m = len(b)

        for j in range(n):
            cur = c[j]
            lo = c_lo[j] if j < len(c_lo) else -INF
            hi = c_hi[j] if j < len(c_hi) else INF
            diff = c_diff[j] if c_diff and j < len(c_diff) else 0.0
            vname = f"X{subs[j]}" if j < len(subs) else f"X{j+1}"
            vals = [vname, fmt(x[j]), fmt(diff), fmt(lo), fmt(cur), fmt(hi)]
            for k, v in enumerate(vals):
                self.sens_var_rows[j][k].config(text=v)

        for i in range(m):
            actual = sum(A[i][j] * x[j] for j in range(n))
            slack = b[i] - actual if rels[i] != "≥" else actual - b[i]
            sp = shadow[i] if i < len(shadow) else 0
            lo = b_lo[i] if i < len(b_lo) else -INF
            hi = b_hi[i] if i < len(b_hi) else INF
            vals = [str(i + 1), fmt(actual), fmt(slack),
                    fmt(sp), fmt(lo), fmt(b[i]), fmt(hi)]
            for k, v in enumerate(vals):
                self.sens_con_rows[i][k].config(text=v)

        zero_slack = sum(1 for j in range(n) if abs(x[j]) < 1e-6)
        conclusion = ("本模型存在唯一解，且存在对应的唯一对偶价格" if zero_slack > 0
                      else "本模型最优解已求得")
        self.conclusion_label.config(text=conclusion)

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
        lines += [""] + [f"  x{j+1} >= 0" for j in range(n)]
        lines += ["", f"最优解: " + ",  ".join(f"{xname(j)}={fmt(x[j])}" for j in range(n))]
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
                        xname(j) + f"={xvals.get(f'x{j+1}', 0):.4g}"
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
        INF = 1e30
        fig, ax = plt.subplots(1, 1, figsize=(5.5, 4.0), dpi=90)
        fig.patch.set_facecolor("#f5f5f0")

        if n == 2:
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

            def term(v, j, first=False):
                if v == 0: return ""
                vstr = str(int(v)) if v == int(v) else str(v)
                xstr = xname(j)
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
            lines += [""] + [xname(j) + " >= 0" for j in range(n)]
            self.main_expr_text.delete("1.0", "end")
            self.main_expr_text.insert("end", "\n".join(lines))
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _expr_to_table(self):
        try:
            raw = self.main_expr_text.get("1.0", "end").strip()
            if "# ── 求解结果" in raw:
                raw = raw[:raw.index("# ── 求解结果")].strip()
            raw = normalize_expr(raw)
            lines = [l.strip() for l in raw.split("\n") if l.strip()]

            def parse_poly(s):
                s = s.strip().replace(" ", "")
                if s and s[0] not in "+-": s = "+" + s
                coefs = {}
                for m in re.finditer(r"([+-])([0-9.]*)[xX]([0-9]+)", s):
                    sign = 1 if m.group(1) == "+" else -1
                    c_str = m.group(2)
                    coefs[int(m.group(3)) - 1] = sign * (float(c_str) if c_str else 1.0)
                return coefs

            obj_line = next((l for l in lines if re.match(r"(max|min|MAX|MIN)", l, re.I)), None)
            if not obj_line:
                messagebox.showwarning("解析失败", "找不到目标函数行(需含max或min)"); return
            if re.match(r"(max|MAX)", obj_line, re.I):
                self.obj_type.set("最大化")
            else:
                self.obj_type.set("最小化")
            obj_part = re.sub(r"^(max|min)[^=]*=\s*", "", obj_line, flags=re.I)
            obj_coefs = parse_poly(obj_part)

            REL_RE = re.compile(r"(<=|>=|<|>|=)")
            con_lines = []
            for l in lines:
                if not REL_RE.search(l): continue
                if re.match(r"s\.?t\.?", l, re.I): continue
                if re.match(r"\s*(max|min)", l, re.I): continue
                if l.strip().startswith("#"): continue
                if re.match(r"\s*(最优|Z\s*=)", l): continue
                l_clean = l.replace(" ", "")
                if re.match(r"x\d+>=0$", l_clean): continue
                if re.match(r"x\d+<=0$", l_clean): continue
                con_lines.append(l)

            if not con_lines:
                messagebox.showwarning("解析失败", "找不到约束条件"); return

            parsed_cons = []
            REL_MAP = {"<=": "≤", ">=": "≥", "<": "≤", ">": "≥", "=": "="}
            for l in con_lines:
                l_clean = l.replace(" ", "")
                for sym in ["<=", ">=", "<", ">", "="]:
                    if sym in l_clean:
                        parts = l_clean.split(sym, 1)
                        try:
                            rhs = float(parts[1])
                        except Exception:
                            continue
                        parsed_cons.append((parse_poly(parts[0]), REL_MAP[sym], rhs))
                        break

            all_vars = set(obj_coefs.keys())
            for coefs, _, _ in parsed_cons: all_vars |= set(coefs.keys())
            if not all_vars:
                messagebox.showwarning("解析失败", "未识别到变量(格式应为x1,x2...)"); return
            n = max(all_vars) + 1
            m = len(parsed_cons)
            self.n_vars.set(n); self.n_cons.set(m)
            self.entries_built = False
            self._build_table()

            for j in range(n):
                v = obj_coefs.get(j, 0)
                self.obj_entries[j].delete(0, "end")
                self.obj_entries[j].insert(0, str(int(v) if v == int(v) else v))
            for i, (coefs, rel, rhs) in enumerate(parsed_cons):
                for j in range(n):
                    v = coefs.get(j, 0)
                    self.con_entries[i][j].delete(0, "end")
                    if v != 0:
                        self.con_entries[i][j].insert(0, str(int(v) if v == int(v) else v))
                self.rel_vars[i].set(rel)
                self.rhs_entries[i].delete(0, "end")
                self.rhs_entries[i].insert(0, str(int(rhs) if rhs == int(rhs) else rhs))
            messagebox.showinfo("解析成功", f"已填入：{n}个变量，{m}个约束")
        except Exception as e:
            messagebox.showerror("解析错误", str(e))

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
