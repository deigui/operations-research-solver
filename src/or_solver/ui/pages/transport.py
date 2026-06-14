"""运输问题 / 指派问题求解页。"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox

from or_solver.constants import FONT_SMALL, BTN_GREEN, BTN_GRAY, xname
from or_solver.core.transport_solver import solve_transport, solve_assignment, parse_cost
from or_solver.utils.expr_parser import normalize_expr
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button


class TransportPage(tk.Frame, TableEditMixin):
    def __init__(self, master: tk.Widget, controller, mode: str = "平衡"):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.mode = mode  # 平衡 / 产大于销 / 销大于产 / 指派
        self.n_src = tk.IntVar(value=3)
        self.n_dst = tk.IntVar(value=3)
        self.entries_built = False
        self._build_header()

    def _build_header(self):
        title_map = {
            "平衡": "产销平衡问题", "产大于销": "产大于销问题",
            "销大于产": "销大于产问题", "指派": "指派问题",
        }
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"运筹学模型求解系统———{title_map[self.mode]}",
                 font=("微软雅黑", 13, "bold"), bg="#d7ccc8").pack(side="left", padx=10, pady=6)
        ctrl = tk.Frame(hdr, bg="#d7ccc8")
        ctrl.pack(side="left", padx=10)
        if self.mode == "指派":
            tk.Label(ctrl, text="人数/任务数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left")
            tk.Spinbox(ctrl, from_=2, to=15, textvariable=self.n_src, width=4,
                       font=FONT_SMALL).pack(side="left", padx=4)
        else:
            tk.Label(ctrl, text="产地数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left")
            tk.Spinbox(ctrl, from_=1, to=15, textvariable=self.n_src, width=4,
                       font=FONT_SMALL).pack(side="left", padx=4)
            tk.Label(ctrl, text="销地数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left", padx=(8, 0))
            tk.Spinbox(ctrl, from_=1, to=15, textvariable=self.n_dst, width=4,
                       font=FONT_SMALL).pack(side="left", padx=4)
        make_button(hdr, "确  定", self._build_table, bg=BTN_GREEN, width=8).pack(side="left", padx=6)
        make_button(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=4)
        make_button(hdr, "返  回", self.controller.show_menu, bg=BTN_GRAY, width=8).pack(side="left", padx=4)

        expr_frame = tk.Frame(self, bg="#f0ece4", relief="groove", bd=1)
        expr_frame.pack(fill="x", padx=10, pady=(4, 0))
        expr_top = tk.Frame(expr_frame, bg="#f0ece4")
        expr_top.pack(fill="x", padx=6, pady=(4, 2))
        tk.Label(expr_top, text="模型表达式（输入或粘贴）:",
                 bg="#f0ece4", font=("宋体", 9, "bold")).pack(side="left")
        tk.Button(expr_top, text="解析填入表格", command=self._expr_to_table,
                  bg="#90ee90", font=("宋体", 9), width=12).pack(side="left", padx=6)
        tk.Button(expr_top, text="从表格刷新", command=self._table_to_expr,
                  bg="#87ceeb", font=("宋体", 9), width=10).pack(side="left", padx=2)
        tk.Button(expr_top, text="清  空",
                  command=lambda: self.expr_text.delete("1.0", "end"),
                  bg="#ffcccc", font=("宋体", 9), width=6).pack(side="left", padx=2)
        self.expr_text = tk.Text(expr_frame, font=("Consolas", 10), bg="#fffff0",
                                 relief="sunken", bd=1, height=4)
        self.expr_text.pack(fill="x", padx=6, pady=(0, 4))
        if self.mode == "指派":
            placeholder = "# 费用矩阵（每行一个工人，空格分隔）\n3 2 4\n5 3 6\n8 7 2"
        else:
            placeholder = "# 费用矩阵（每行一个产地，空格分隔）\n3 2 4\n5 3 6\n产量: 100 150\n销量: 80 90 80"
        self.expr_text.insert("1.0", placeholder)

        self.body = tk.Frame(self, bg="#f5f0e8")
        self.body.pack(fill="both", expand=True, padx=10, pady=6)

    # ── TableEditMixin 接口 ──────────────────────────────
    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        m = self.n_src.get()
        n = self.n_src.get() if self.mode == "指派" else self.n_dst.get()
        try:
            if r < m and c < n:
                return self.cost_entries[r][c]
            if self.mode != "指派":
                if r < m and c == n and r < len(self.supply_entries):
                    return self.supply_entries[r]
                if r == m and c < n and c < len(self.demand_entries):
                    return self.demand_entries[c]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        m = self.n_src.get()
        n = self.n_src.get() if self.mode == "指派" else self.n_dst.get()
        if r < m and c < n: return "#e8f5e9"
        if r < m and c == n: return "#fff9c4"
        if r == m and c < n: return "#e3f2fd"
        return "#f5f0e8"

    def _all_entries(self):
        m = self.n_src.get()
        n = self.n_src.get() if self.mode == "指派" else self.n_dst.get()
        try:
            for i, row in enumerate(self.cost_entries):
                for j, e in enumerate(row):
                    yield (i, j, e)
            if self.mode != "指派":
                for i, e in enumerate(self.supply_entries):
                    yield (i, n, e)
                for j, e in enumerate(self.demand_entries):
                    yield (m, j, e)
        except AttributeError:
            return

    # ── 建表 ────────────────────────────────────────────
    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        m = self.n_src.get()
        n = self.n_dst.get() if self.mode != "指派" else m

        tk.Label(self.body, text="费用矩阵 (单位运费)", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).grid(row=0, column=0, sticky="w", columnspan=n + 2)
        for j in range(n):
            lbl = "任务" if self.mode == "指派" else f"销地{j+1}"
            tk.Label(self.body, text=lbl, bg="#ffe0b2", font=FONT_SMALL,
                     relief="ridge", width=8).grid(row=1, column=j + 2, padx=1, pady=1)
        if self.mode != "指派":
            tk.Label(self.body, text="产量", bg="#ffe0b2", font=FONT_SMALL,
                     relief="ridge", width=8).grid(row=1, column=n + 2, padx=2)

        self.cost_entries: list[list[tk.Entry]] = []
        self.supply_entries: list[tk.Entry] = []
        for i in range(m):
            lbl = f"工人{i+1}" if self.mode == "指派" else f"产地{i+1}"
            tk.Label(self.body, text=lbl, bg="#f5f0e8",
                     font=FONT_SMALL).grid(row=i + 2, column=1, padx=4)
            row_e = []
            for j in range(n):
                e = tk.Entry(self.body, width=8, font=FONT_SMALL, bg="#e8f5e9")
                e.grid(row=i + 2, column=j + 2, padx=1, pady=0)
                self._bind_cell(e, i, j)
                e.bind("<Control-v>", lambda ev, r=i, c=j: self._paste_from_clipboard(ev, r, c, "cost"))
                row_e.append(e)
            self.cost_entries.append(row_e)
            if self.mode != "指派":
                se = tk.Entry(self.body, width=8, font=FONT_SMALL, bg="#fff9c4")
                se.grid(row=i + 2, column=n + 2, padx=1, pady=0)
                self._bind_cell(se, i, n)
                se.bind("<Control-v>", lambda ev, r=i: self._paste_from_clipboard(ev, r, 0, "supply"))
                self.supply_entries.append(se)

        self.demand_entries: list[tk.Entry] = []
        if self.mode != "指派":
            tk.Label(self.body, text="销量", bg="#f5f0e8",
                     font=FONT_SMALL).grid(row=m + 2, column=1, padx=2)
            for j in range(n):
                de = tk.Entry(self.body, width=8, font=FONT_SMALL, bg="#e3f2fd")
                de.grid(row=m + 2, column=j + 2, padx=1, pady=0)
                self._bind_cell(de, m, j)
                de.bind("<Control-v>", lambda ev, c=j: self._paste_from_clipboard(ev, 0, c, "demand"))
                self.demand_entries.append(de)

        self.result_text = tk.Text(self.body, height=8, width=60,
                                   font=FONT_SMALL, bg="#fffde7")
        self.result_text.grid(row=m + 4, column=1, columnspan=n + 3, pady=8, sticky="w")
        self.entries_built = True

    # ── 求解 ────────────────────────────────────────────
    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        try:
            m = self.n_src.get()
            n = self.n_dst.get() if self.mode != "指派" else m
            import numpy as np
            cost = np.array([[parse_cost(self.cost_entries[i][j].get())
                              for j in range(n)] for i in range(m)])

            if self.mode == "指派":
                result = solve_assignment(cost)
                self.result_text.delete("1.0", "end")
                if result.status != "optimal":
                    self.result_text.insert("end", f"求解失败：{result.status}")
                    return
                self.result_text.insert("end",
                    f"最优指派方案（最小总费用 = {result.total_cost:.2f}）\n\n")
                for i, j in zip(result.row_ind, result.col_ind):
                    self.result_text.insert("end",
                        f"  工人{i+1} → 任务{j+1}  费用={cost[i, j]}\n")
                return

            supply = [float(self.supply_entries[i].get() or 0) for i in range(m)]
            demand = [float(self.demand_entries[j].get() or 0) for j in range(n)]
            result = solve_transport(cost.tolist(), supply, demand)

            self.result_text.delete("1.0", "end")
            if result.status != "optimal":
                self.result_text.insert("end", f"求解失败：{result.status}")
                return

            self.result_text.insert("end",
                f"最优运输方案  最小总费用 = {result.total_cost:.2f}")
            x_opt = result.allocation
            orig_supply = [s for s in supply if s > 0] or supply
            orig_demand = demand[:n]
            self._show_lp_result(cost.tolist(), supply, demand,
                                 x_opt[:m, :n], result.total_cost)

        except ValueError as e:
            messagebox.showerror("输入错误", str(e))
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _populate_table(self, cost_matrix, supply, demand):
        m = len(cost_matrix)
        n = max((len(r) for r in cost_matrix), default=0)
        self.n_src.set(m)
        if self.mode != "指派":
            self.n_dst.set(n)
        self._build_table()
        for i, row in enumerate(cost_matrix):
            for j, v in enumerate(row):
                if j < len(self.cost_entries[i]):
                    self.cost_entries[i][j].delete(0, "end")
                    self.cost_entries[i][j].insert(0, str(int(v) if v == int(v) else v))
        if self.mode != "指派":
            for i, v in enumerate(supply):
                if i < len(self.supply_entries):
                    self.supply_entries[i].delete(0, "end")
                    self.supply_entries[i].insert(0, str(int(v) if v == int(v) else v))
            for j, v in enumerate(demand):
                if j < len(self.demand_entries):
                    self.demand_entries[j].delete(0, "end")
                    self.demand_entries[j].insert(0, str(int(v) if v == int(v) else v))

    # ── LP结果表 ─────────────────────────────────────────
    def _show_lp_result(self, cost_orig, supply, demand, x_opt, opt_val):
        if hasattr(self, "_lp_result_frame") and self._lp_result_frame.winfo_exists():
            self._lp_result_frame.destroy()

        real_src = [i for i in range(len(supply)) if supply[i] > 0] or list(range(len(supply)))
        n = len(demand)
        m = len(real_src)
        total_vars = m * n
        total_cons = m + n

        c_flat = [float(cost_orig[i][j]) for i in real_src for j in range(n)]
        x_flat = [float(x_opt[i][j]) for i in real_src for j in range(n)]
        supply_f = [supply[i] for i in real_src]

        A, b_vec, rels = [], [], []
        for ii in range(m):
            row = [0] * total_vars
            for j in range(n): row[ii * n + j] = 1
            A.append(row); b_vec.append(supply_f[ii]); rels.append("=")
        for j in range(n):
            row = [0] * total_vars
            for ii in range(m): row[ii * n + j] = 1
            A.append(row); b_vec.append(demand[j]); rels.append("=")

        HDR = "#ffff99"; RHS = "#ffcccc"; OPT = "#b0d0ff"; BG = "#f5f0e8"; W = 7

        def L(p, text, bg, font=("宋体", 10), **kw):
            return tk.Label(p, text=text, bg=bg, font=font, relief="ridge", **kw)

        outer = tk.Frame(self.body, bg=BG, relief="groove", bd=1)
        outer.grid(row=m + n + 5, column=0, columnspan=n + 6, pady=6, sticky="w", padx=2)
        self._lp_result_frame = outer

        r = 0
        tk.Label(outer, text="目标函数系数", bg=BG,
                 font=("宋体", 10, "bold")).grid(
                 row=r, column=0, sticky="w", columnspan=total_vars + 5, padx=4, pady=(4, 0))
        r += 1
        tk.Label(outer, text="", bg=BG, width=3, relief="flat").grid(row=r, column=0)
        for k in range(total_vars):
            L(outer, xname(k), HDR, width=W).grid(row=r, column=k + 1, padx=1, pady=1)
        r += 1
        tk.Label(outer, text="", bg=BG, width=3, relief="flat").grid(row=r, column=0)
        for k in range(total_vars):
            v = c_flat[k]
            L(outer, str(int(v) if v == int(v) else v), HDR, width=W).grid(
                row=r, column=k + 1, padx=1, pady=1)
        L(outer, "约束条件实际值", RHS, width=14).grid(row=r, column=total_vars + 1, padx=1, pady=1)
        L(outer, "约束关系", RHS, width=8).grid(row=r, column=total_vars + 2, padx=1, pady=1)
        L(outer, "约束条件常数项", RHS, width=14).grid(row=r, column=total_vars + 3, padx=1, pady=1)
        r += 1
        tk.Label(outer, text="约束条件系数", bg=BG,
                 font=("宋体", 10, "bold")).grid(
                 row=r, column=0, sticky="w", columnspan=total_vars + 5, padx=4, pady=(6, 0))
        r += 1
        for ci in range(total_cons):
            L(outer, str(ci + 1), HDR, width=3).grid(row=r, column=0, padx=1, pady=1)
            for k in range(total_vars):
                v = A[ci][k]
                L(outer, str(int(v)) if v else "", "#ffffff",
                  width=W).grid(row=r, column=k + 1, padx=1, pady=1)
            actual = sum(A[ci][k] * x_flat[k] for k in range(total_vars))
            a_str = str(int(round(actual)) if abs(actual - round(actual)) < 1e-6 else f"{actual:.2f}")
            b_str = str(int(b_vec[ci]) if b_vec[ci] == int(b_vec[ci]) else b_vec[ci])
            L(outer, a_str, RHS, width=14).grid(row=r, column=total_vars + 1, padx=1, pady=1)
            L(outer, rels[ci], RHS, width=8).grid(row=r, column=total_vars + 2, padx=1, pady=1)
            L(outer, b_str, RHS, width=14).grid(row=r, column=total_vars + 3, padx=1, pady=1)
            r += 1
        L(outer, "最优解", HDR, font=("宋体", 10, "bold"), width=3).grid(
            row=r, column=0, padx=1, pady=(6, 2))
        for k in range(total_vars):
            v = x_flat[k]
            txt = str(int(round(v)) if abs(v - round(v)) < 1e-6 else round(v, 2))
            L(outer, txt, OPT, width=W).grid(row=r, column=k + 1, padx=1, pady=(6, 2))
        opt_str = str(int(round(opt_val)) if abs(opt_val - round(opt_val)) < 1 else f"{opt_val:.2f}")
        L(outer, f"最优值\n{opt_str}", RHS, font=("宋体", 10, "bold"), width=14).grid(
            row=r, column=total_vars + 3, padx=1, pady=(6, 2))

    # ── 剪贴板粘贴 ───────────────────────────────────────
    def _paste_from_clipboard(self, event, start_r=0, start_c=0, area="cost"):
        try:
            text = self.body.clipboard_get()
        except Exception:
            return None

        if "\t" not in text and "\n" not in text.strip():
            w = event.widget
            try:
                if w.selection_present():
                    w.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except Exception:
                pass
            w.insert(tk.INSERT, text.strip())
            return "break"

        def _is_num(s):
            try:
                float(s.strip()); return True
            except ValueError:
                return s.strip() == ""

        def _set(entry, val):
            val = val.strip()
            if val:
                entry.delete(0, "end")
                entry.insert(0, val)

        raw_rows = [ln.split("\t") for ln in text.strip().splitlines() if ln.strip()]
        if not raw_rows:
            return "break"

        skip_row = 1 if any(not _is_num(c) and c.strip() for c in raw_rows[0]) else 0
        skip_col = 0
        for row in raw_rows[skip_row:]:
            if row and not _is_num(row[0]) and row[0].strip():
                skip_col = 1; break

        data = []
        for row in raw_rows[skip_row:]:
            data.append([row[ci] for ci in range(skip_col, len(row))])

        m = self.n_src.get()
        n = self.n_src.get() if self.mode == "指派" else self.n_dst.get()

        if area == "supply":
            for ri, row in enumerate(data):
                r = start_r + ri
                if r < m and row:
                    _set(self.supply_entries[r], row[0])
        elif area == "demand":
            if data:
                for ci, val in enumerate(data[0]):
                    c = start_c + ci
                    if c < n and self.mode != "指派":
                        _set(self.demand_entries[c], val)
        else:
            demand_row_idx = None
            if (self.mode != "指派" and start_r == 0 and start_c == 0 and len(data) > 1):
                last = data[-1]
                prev = data[-2]
                last_supply = last[-1].strip() if len(last) > n else ""
                prev_supply = prev[-1].strip() if len(prev) > n else ""
                supply_match = (last_supply == "" and prev_supply != "")
                last_label = ""
                if skip_col == 1 and raw_rows:
                    last_raw = raw_rows[skip_row + len(data) - 1]
                    last_label = last_raw[0].strip() if last_raw else ""
                label_match = any(kw in last_label for kw in ["用量", "销量", "需求", "demand", "Demand"])
                if supply_match or label_match:
                    demand_row_idx = len(data) - 1

            if (start_r == 0 and start_c == 0 and self.mode != "指派"
                    and demand_row_idx is not None):
                n_cost_rows = demand_row_idx
                d_last = data[demand_row_idx][-1].strip() if data[demand_row_idx] else ""
                c_lasts = [data[ri][-1].strip() for ri in range(n_cost_rows) if data[ri]]
                has_supply_col = (not d_last and bool(c_lasts)
                                  and all(_is_num(v) and v for v in c_lasts))
                new_m = n_cost_rows
                new_n = (len(data[0]) - 1) if has_supply_col else len(data[0])
                if new_m > 0 and new_n > 0 and (new_m != m or new_n != n):
                    self.n_src.set(new_m); self.n_dst.set(new_n)
                    self._build_table()
                    m, n = new_m, new_n

            for ri, row in enumerate(data):
                r = start_r + ri
                if demand_row_idx is not None and ri == demand_row_idx:
                    for j in range(n):
                        if j < len(self.demand_entries):
                            self.demand_entries[j].delete(0, "end")
                    for ci, val in enumerate(row[:n]):
                        v = val.strip()
                        if v and ci < len(self.demand_entries):
                            self.demand_entries[ci].insert(0, v)
                    continue
                for ci, val in enumerate(row):
                    c = start_c + ci
                    if r < m and c < n:
                        _set(self.cost_entries[r][c], val)
                    elif r < m and c == n and self.mode != "指派":
                        _set(self.supply_entries[r], val)
                    elif r == m and c < n and self.mode != "指派":
                        _set(self.demand_entries[c], val)
        return "break"

    # ── 表达式互转 ────────────────────────────────────────
    def _expr_to_table(self):
        try:
            raw = self.expr_text.get("1.0", "end").strip()
            if re.search(r"^\s*(min|max)\b", raw, re.I | re.M):
                self._parse_lp_to_table(raw)
                return
            lines = [l.strip() for l in raw.split("\n")
                     if l.strip() and not l.strip().startswith("#")]
            supply, demand, cost_rows = [], [], []
            for line in lines:
                if re.match(r"产量\s*[:：]", line):
                    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", re.split(r"[:：]", line, 1)[-1])
                    supply = [float(x) for x in nums]
                elif re.match(r"销量\s*[:：]", line):
                    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", re.split(r"[:：]", line, 1)[-1])
                    demand = [float(x) for x in nums]
                else:
                    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", line)
                    if nums:
                        cost_rows.append([float(x) for x in nums])
            if not cost_rows:
                messagebox.showwarning("解析失败", "未找到费用矩阵数据"); return
            self._populate_table(cost_rows, supply, demand)
            m = len(cost_rows); n = max(len(r) for r in cost_rows)
            detail = f"已解析：{m}×{n} 费用矩阵"
            if supply: detail += f"，产量 {[int(v) if v==int(v) else v for v in supply]}"
            if demand: detail += f"，销量 {[int(v) if v==int(v) else v for v in demand]}"
            messagebox.showinfo("解析成功", detail)
        except Exception as e:
            messagebox.showerror("解析错误", str(e))

    def _parse_lp_to_table(self, raw):
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

        obj_line = next((l for l in lines if re.match(r"(min|max)\b", l, re.I)), None)
        if not obj_line:
            messagebox.showwarning("解析失败", "找不到目标函数行"); return
        obj_part = re.sub(r"^(min|max)\s*\w?\s*=\s*", "", obj_line, flags=re.I)
        cost_coefs = parse_poly(obj_part)
        if not cost_coefs:
            messagebox.showwarning("解析失败", "目标函数解析失败"); return
        total_vars = max(cost_coefs.keys()) + 1

        eq_cons = []
        for line in lines:
            if re.match(r"(min|max)\b", line, re.I): continue
            if line.startswith("#"): continue
            line = re.sub(r"^s\.?\s*t\.?\s*", "", line, flags=re.I).strip()
            if not line: continue
            lc = line.replace(" ", "")
            if re.match(r"x[^0-9]*[0-9,，…\s]*\s*>=?\s*0", lc, re.I): continue
            if "=" not in lc or ">=" in lc or "<=" in lc: continue
            parts = lc.split("=", 1)
            var_set = sorted({int(m.group(1)) - 1 for m in re.finditer(r"[xX]([0-9]+)", parts[0])})
            if not var_set: continue
            try:
                eq_cons.append((var_set, float(parts[1])))
            except ValueError:
                pass

        if not eq_cons:
            messagebox.showwarning("解析失败", "未找到等式约束"); return

        supply_cons, demand_cons, n_detected = [], [], None
        for var_set, rhs in eq_cons:
            if len(var_set) < 2:
                supply_cons.append((var_set, rhs)); continue
            diffs = [var_set[k + 1] - var_set[k] for k in range(len(var_set) - 1)]
            if all(d == 1 for d in diffs):
                supply_cons.append((var_set, rhs))
                if n_detected is None: n_detected = len(var_set)
            elif len(set(diffs)) == 1:
                demand_cons.append((var_set, rhs))

        if n_detected is None:
            if demand_cons: n_detected = len(demand_cons)
            else:
                messagebox.showwarning("解析失败", "无法推断销地数"); return
        n = n_detected
        m_src = total_vars // n if total_vars % n == 0 else len(supply_cons)

        cost_matrix = [[0.0] * n for _ in range(m_src)]
        for var_idx, coef in cost_coefs.items():
            i, j = var_idx // n, var_idx % n
            if i < m_src and j < n:
                cost_matrix[i][j] = coef

        supply_cons.sort(key=lambda x: x[0][0])
        demand_cons.sort(key=lambda x: x[0][0])
        supply = [rhs for _, rhs in supply_cons]
        demand = [rhs for _, rhs in demand_cons]
        self._populate_table(cost_matrix, supply, demand)

        detail = f"已解析：{m_src}×{n} 运输问题"
        if supply: detail += f"\n产量：{[int(v) if v==int(v) else v for v in supply]}"
        if demand: detail += f"\n销量：{[int(v) if v==int(v) else v for v in demand]}"
        messagebox.showinfo("解析成功", detail)

    def _table_to_expr(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成表格"); return
        try:
            m = self.n_src.get()
            n = self.n_dst.get() if self.mode != "指派" else m
            lines = ["# 费用矩阵（每行一个工人，空格分隔）" if self.mode == "指派"
                     else "# 费用矩阵（每行一个产地，空格分隔）"]
            for i in range(m):
                row_vals = [self.cost_entries[i][j].get().strip() or "0" for j in range(n)]
                lines.append("  ".join(row_vals))
            if self.mode != "指派":
                supply_vals = [e.get().strip() or "0" for e in self.supply_entries]
                demand_vals = [e.get().strip() or "0" for e in self.demand_entries]
                lines.append(f"产量: {' '.join(supply_vals)}")
                lines.append(f"销量: {' '.join(demand_vals)}")
            self.expr_text.delete("1.0", "end")
            self.expr_text.insert("end", "\n".join(lines))
        except Exception as e:
            messagebox.showerror("错误", str(e))
