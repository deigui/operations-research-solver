"""运输问题 / 指派问题求解页。"""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox

from or_solver.constants import FONT_SMALL, BTN_GREEN, xname
from or_solver.core.transport_solver import solve_transport, solve_assignment, parse_cost
from or_solver.utils.expr_parser import normalize_expr
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button


class TransportPage(tk.Frame, TableEditMixin):
    PAGE_BG = "#f3efe8"
    BAR_BG = "#e1d8d2"
    PANEL_BG = "#fbfaf4"
    PANEL_LINE = "#c9c0b5"
    HEADER_BG = "#f4d39e"
    COST_BG = "#e6f3e8"
    SUPPLY_BG = "#fff5ba"
    DEMAND_BG = "#e2f1fb"
    RESULT_BG = "#fffbe6"
    TOP_CARD_MIN_W = 560
    TOP_CARD_MIN_H = 220

    def __init__(self, master: tk.Widget, controller, mode: str = "平衡"):
        super().__init__(master, bg=self.PAGE_BG)
        self.controller = controller
        self.mode = mode  # 平衡 / 产大于销 / 销大于产 / 指派
        self.n_src = tk.IntVar(value=3)
        self.n_dst = tk.IntVar(value=3)
        self.entries_built = False
        self.virtual_src_rows: set[int] = set()
        self.virtual_dst_cols: set[int] = set()
        self._build_header()

    def _build_header(self):
        hdr = tk.Frame(self, bg=self.BAR_BG, highlightthickness=1, highlightbackground="#b9afa7")
        hdr.pack(fill="x")

        controls = tk.Frame(hdr, bg=self.BAR_BG)
        controls.pack(anchor="center", pady=8)

        ctrl = tk.Frame(controls, bg=self.PANEL_BG, highlightthickness=1, highlightbackground="#b9afa7")
        ctrl.pack(side="left", padx=(0, 12))
        if self.mode == "指派":
            tk.Label(ctrl, text="人数/任务数", bg=self.PANEL_BG, font=FONT_SMALL).pack(side="left", padx=(12, 4), pady=6)
            tk.Spinbox(ctrl, from_=2, to=15, textvariable=self.n_src, width=4,
                       font=FONT_SMALL, relief="sunken").pack(side="left", padx=(0, 12), pady=6)
        else:
            tk.Label(ctrl, text="产地数", bg=self.PANEL_BG, font=FONT_SMALL).pack(side="left", padx=(12, 4), pady=6)
            tk.Spinbox(ctrl, from_=1, to=15, textvariable=self.n_src, width=4,
                       font=FONT_SMALL, relief="sunken").pack(side="left", padx=(0, 12), pady=6)
            tk.Label(ctrl, text="销地数", bg=self.PANEL_BG, font=FONT_SMALL).pack(side="left", padx=(0, 4), pady=6)
            tk.Spinbox(ctrl, from_=1, to=15, textvariable=self.n_dst, width=4,
                       font=FONT_SMALL, relief="sunken").pack(side="left", padx=(0, 12), pady=6)

        actions = tk.Frame(controls, bg=self.BAR_BG)
        actions.pack(side="left")
        make_button(actions, "确定", self._build_table, bg=BTN_GREEN, width=7).pack(side="left", padx=(0, 10))
        make_button(actions, "求解", self._solve, bg="#e53935", fg="white", width=7).pack(side="left")

        body_shell = tk.Frame(self, bg=self.PAGE_BG)
        body_shell.pack(fill="both", expand=True)
        self.body_canvas = tk.Canvas(body_shell, bg=self.PAGE_BG, highlightthickness=0, bd=0)
        self.body_vsb = tk.Scrollbar(body_shell, orient="vertical", command=self.body_canvas.yview)
        self.body_canvas.configure(yscrollcommand=self.body_vsb.set)
        self.body_vsb.pack(side="right", fill="y")
        self.body_canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.body_canvas, bg=self.PAGE_BG)
        self._body_window = self.body_canvas.create_window((0, 0), window=self.body, anchor="n")
        self.body.bind("<Configure>", self._sync_body_scrollregion)
        self.body_canvas.bind("<Configure>", self._sync_body_width)

    def _sync_body_scrollregion(self, _event=None) -> None:
        self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all"))

    def _sync_body_width(self, event) -> None:
        self.body_canvas.itemconfigure(self._body_window, width=event.width)

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

        content = tk.Frame(self.body, bg=self.PAGE_BG)
        content.pack(anchor="n", pady=(4, 18))
        content.grid_columnconfigure(0, weight=1, uniform="transport_top")
        content.grid_columnconfigure(1, weight=1, uniform="transport_top")
        self._lp_result_parent = content

        table_card = tk.Frame(
            content,
            bg=self.PANEL_BG,
            width=self.TOP_CARD_MIN_W,
            height=self.TOP_CARD_MIN_H,
            highlightthickness=1,
            highlightbackground=self.PANEL_LINE,
        )
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 16))
        table_card.grid_propagate(False)
        table_area = tk.Frame(table_card, bg=self.PANEL_BG)
        table_area.pack(fill="both", expand=True, padx=16, pady=14)

        result_card = tk.Frame(
            content,
            bg=self.PANEL_BG,
            width=self.TOP_CARD_MIN_W,
            height=self.TOP_CARD_MIN_H,
            highlightthickness=1,
            highlightbackground=self.PANEL_LINE,
        )
        result_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=(0, 16))
        result_card.grid_propagate(False)
        result_area = tk.Frame(result_card, bg=self.PANEL_BG)
        result_area.pack(fill="both", expand=True, padx=16, pady=14)
        result_area.grid_rowconfigure(1, weight=1)
        result_area.grid_columnconfigure(0, weight=1)

        tk.Label(table_area, text="费用矩阵 (单位运费)", bg=self.PANEL_BG,
                 fg="#111", font=("微软雅黑", 10, "bold")).grid(
                 row=0, column=0, sticky="w", columnspan=n + 2, pady=(0, 8))
        matrix = tk.Frame(table_area, bg="#d2c9bd", highlightthickness=1, highlightbackground="#a99f94")
        matrix.grid(row=1, column=0, sticky="nw")

        def cell_label(parent, text, bg, width=10, font=FONT_SMALL, fg="#222"):
            return tk.Label(parent, text=text, bg=bg, fg=fg, font=font,
                            width=width, relief="flat", bd=0)

        cell_label(matrix, "", "#f7efe2", width=9).grid(row=0, column=0, padx=1, pady=1, sticky="nsew")
        for j in range(n):
            if self.mode == "指派":
                lbl = f"任务{j+1}"
            elif j in self.virtual_dst_cols:
                lbl = f"虚拟销地{j+1}"
            else:
                lbl = f"销地{j+1}"
            cell_label(matrix, lbl, self.HEADER_BG).grid(row=0, column=j + 1, padx=1, pady=1, sticky="nsew")
        if self.mode != "指派":
            cell_label(matrix, "产量", self.HEADER_BG).grid(row=0, column=n + 1, padx=1, pady=1, sticky="nsew")

        self.cost_entries: list[list[tk.Entry]] = []
        self.supply_entries: list[tk.Entry] = []
        for i in range(m):
            if self.mode == "指派":
                lbl = f"工人{i+1}"
            elif i in self.virtual_src_rows:
                lbl = f"虚拟产地{i+1}"
            else:
                lbl = f"产地{i+1}"
            cell_label(matrix, lbl, "#f7efe2", width=9).grid(row=i + 1, column=0, padx=1, pady=1, sticky="nsew")
            row_e = []
            for j in range(n):
                e = tk.Entry(matrix, width=10, font=FONT_SMALL, bg=self.COST_BG,
                             relief="flat", bd=0, highlightthickness=0)
                e.grid(row=i + 1, column=j + 1, padx=1, pady=1, ipady=3, sticky="nsew")
                self._bind_cell(e, i, j)
                e.bind("<Control-v>", lambda ev, r=i, c=j: self._paste_from_clipboard(ev, r, c, "cost"))
                e.bind("<Control-V>", lambda ev, r=i, c=j: self._paste_from_clipboard(ev, r, c, "cost"))
                row_e.append(e)
            self.cost_entries.append(row_e)
            if self.mode != "指派":
                se = tk.Entry(matrix, width=10, font=FONT_SMALL, bg=self.SUPPLY_BG,
                              relief="flat", bd=0, highlightthickness=0)
                se.grid(row=i + 1, column=n + 1, padx=1, pady=1, ipady=3, sticky="nsew")
                self._bind_cell(se, i, n)
                se.bind("<Control-v>", lambda ev, r=i: self._paste_from_clipboard(ev, r, 0, "supply"))
                se.bind("<Control-V>", lambda ev, r=i: self._paste_from_clipboard(ev, r, 0, "supply"))
                self.supply_entries.append(se)

        self.demand_entries: list[tk.Entry] = []
        if self.mode != "指派":
            cell_label(matrix, "销量", "#f7efe2", width=9).grid(row=m + 1, column=0, padx=1, pady=1, sticky="nsew")
            for j in range(n):
                de = tk.Entry(matrix, width=10, font=FONT_SMALL, bg=self.DEMAND_BG,
                              relief="flat", bd=0, highlightthickness=0)
                de.grid(row=m + 1, column=j + 1, padx=1, pady=1, ipady=3, sticky="nsew")
                self._bind_cell(de, m, j)
                de.bind("<Control-v>", lambda ev, c=j: self._paste_from_clipboard(ev, 0, c, "demand"))
                de.bind("<Control-V>", lambda ev, c=j: self._paste_from_clipboard(ev, 0, c, "demand"))
                self.demand_entries.append(de)
            cell_label(matrix, "", "#f7efe2").grid(row=m + 1, column=n + 1, padx=1, pady=1, sticky="nsew")

        tk.Label(result_area, text="求解结果", bg=self.PANEL_BG,
                 fg="#111", font=("微软雅黑", 10, "bold")).grid(
                 row=0, column=0, sticky="w", pady=(0, 8))
        self.result_text = tk.Text(result_area, height=8, width=66,
                                   font=FONT_SMALL, bg=self.RESULT_BG,
                                   relief="flat", bd=0, highlightthickness=1,
                                   highlightbackground=self.PANEL_LINE)
        self.result_text.grid(row=1, column=0, sticky="nsew")
        self.entries_built = True

    def _snapshot_entries(self) -> dict:
        if not self.entries_built:
            return {}
        return {
            "cost": [[e.get() for e in row] for row in self.cost_entries],
            "supply": [e.get() for e in self.supply_entries],
            "demand": [e.get() for e in self.demand_entries],
        }

    def _restore_entries(self, data: dict) -> None:
        for i, row in enumerate(data.get("cost", [])):
            if i >= len(self.cost_entries):
                break
            for j, value in enumerate(row):
                if j < len(self.cost_entries[i]):
                    self.cost_entries[i][j].delete(0, "end")
                    self.cost_entries[i][j].insert(0, value)
        for i, value in enumerate(data.get("supply", [])):
            if i < len(self.supply_entries):
                self.supply_entries[i].delete(0, "end")
                self.supply_entries[i].insert(0, value)
        for j, value in enumerate(data.get("demand", [])):
            if j < len(self.demand_entries):
                self.demand_entries[j].delete(0, "end")
                self.demand_entries[j].insert(0, value)

    def _clear_result_outputs(self) -> None:
        if hasattr(self, "result_text"):
            self.result_text.delete("1.0", "end")
        if hasattr(self, "_lp_result_frame") and self._lp_result_frame.winfo_exists():
            self._lp_result_frame.destroy()

    def _delete_selected_row(self) -> None:
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        if cell is None:
            messagebox.showinfo("删除产地", "请先选中要删除的产地行")
            return
        remove_i = cell[0]
        m = self.n_src.get()
        if remove_i >= m:
            messagebox.showinfo("删除产地", "请选择费用矩阵中的产地行")
            return
        if m <= (2 if self.mode == "指派" else 1):
            messagebox.showinfo("删除产地", "已达到最小行数，不能继续删除")
            return
        data = self._snapshot_entries()
        data["cost"].pop(remove_i)
        if self.mode != "指派" and remove_i < len(data["supply"]):
            data["supply"].pop(remove_i)
        self.n_src.set(m - 1)
        self.virtual_src_rows = {
            idx - 1 if idx > remove_i else idx
            for idx in self.virtual_src_rows
            if idx != remove_i
        }
        self._build_table()
        self._restore_entries(data)
        self._clear_result_outputs()

    def _insert_selected_row(self) -> None:
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        insert_i = self.n_src.get() if cell is None else min(cell[0] + 1, self.n_src.get())
        n = self.n_src.get() if self.mode == "指派" else self.n_dst.get()
        data = self._snapshot_entries()
        data["cost"].insert(insert_i, [""] * n)
        if self.mode != "指派":
            data["supply"].insert(insert_i, "")
        else:
            for row in data["cost"]:
                row.insert(insert_i, "")
        self.n_src.set(self.n_src.get() + 1)
        self.virtual_src_rows = {
            idx + 1 if idx >= insert_i else idx
            for idx in self.virtual_src_rows
        }
        self._build_table()
        self._restore_entries(data)
        self._clear_result_outputs()

    def _delete_selected_col(self) -> None:
        if self.mode == "指派":
            self._delete_selected_row()
            return
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        if cell is None:
            messagebox.showinfo("删除销地", "请先选中要删除的销地列")
            return
        remove_j = cell[1]
        n = self.n_dst.get()
        if remove_j >= n:
            messagebox.showinfo("删除销地", "请选择费用矩阵中的销地列")
            return
        if n <= 1:
            messagebox.showinfo("删除销地", "至少保留 1 个销地")
            return
        data = self._snapshot_entries()
        for row in data["cost"]:
            if remove_j < len(row):
                row.pop(remove_j)
        if remove_j < len(data["demand"]):
            data["demand"].pop(remove_j)
        self.n_dst.set(n - 1)
        self.virtual_dst_cols = {
            idx - 1 if idx > remove_j else idx
            for idx in self.virtual_dst_cols
            if idx != remove_j
        }
        self._build_table()
        self._restore_entries(data)
        self._clear_result_outputs()

    def _insert_selected_col(self) -> None:
        if self.mode == "指派":
            self._insert_selected_row()
            return
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        insert_j = self.n_dst.get() if cell is None else min(cell[1] + 1, self.n_dst.get())
        data = self._snapshot_entries()
        for row in data["cost"]:
            row.insert(insert_j, "")
        data["demand"].insert(insert_j, "")
        self.n_dst.set(self.n_dst.get() + 1)
        self.virtual_dst_cols = {
            idx + 1 if idx >= insert_j else idx
            for idx in self.virtual_dst_cols
        }
        self._build_table()
        self._restore_entries(data)
        self._clear_result_outputs()

    def _add_dummy_destination(self, demand_value: float) -> None:
        data = self._snapshot_entries()
        insert_j = self.n_dst.get()
        for row in data["cost"]:
            row.append("0")
        data["demand"].append(self._format_number(demand_value))
        self.n_dst.set(insert_j + 1)
        self.virtual_dst_cols.add(insert_j)
        self._build_table()
        self._restore_entries(data)

    def _add_dummy_source(self, supply_value: float) -> None:
        data = self._snapshot_entries()
        insert_i = self.n_src.get()
        n = self.n_dst.get()
        data["cost"].append(["0"] * n)
        data["supply"].append(self._format_number(supply_value))
        self.n_src.set(insert_i + 1)
        self.virtual_src_rows.add(insert_i)
        self._build_table()
        self._restore_entries(data)

    def _read_table_data(self):
        import numpy as np

        m = self.n_src.get()
        n = self.n_dst.get() if self.mode != "指派" else m
        cost = np.array([[parse_cost(self.cost_entries[i][j].get())
                          for j in range(n)] for i in range(m)])
        if self.mode == "指派":
            return m, n, cost, [], []
        supply = [float(self.supply_entries[i].get() or 0) for i in range(m)]
        demand = [float(self.demand_entries[j].get() or 0) for j in range(n)]
        return m, n, cost, supply, demand

    @staticmethod
    def _format_number(value: float) -> str:
        return str(int(value)) if float(value).is_integer() else str(value)

    # ── 求解 ────────────────────────────────────────────
    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        try:
            balance_note = ""
            m, n, cost, supply, demand = self._read_table_data()

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

            if sum(supply) <= 0:
                messagebox.showwarning("输入错误", "请填写各产地的产量，产量合计必须大于 0")
                return
            if sum(demand) <= 0:
                messagebox.showwarning("输入错误", "请填写各销地的销量，销量合计必须大于 0")
                return
            if self.mode == "平衡" and abs(sum(supply) - sum(demand)) > 1e-8:
                messagebox.showwarning(
                    "输入错误",
                    f"产销平衡问题要求产量合计等于销量合计：当前产量 {sum(supply):g}，销量 {sum(demand):g}",
                )
                return
            if self.mode == "产大于销":
                diff = sum(supply) - sum(demand)
                if diff < -1e-8:
                    messagebox.showwarning(
                        "输入错误",
                        f"当前是产大于销问题，但销量大于产量：产量 {sum(supply):g}，销量 {sum(demand):g}",
                    )
                    return
                if diff > 1e-8:
                    self._add_dummy_destination(diff)
                    balance_note = f"已在上方表格增加虚拟销地，需求量 = {diff:g}，单位运费 = 0"
                    m, n, cost, supply, demand = self._read_table_data()
            elif self.mode == "销大于产":
                diff = sum(demand) - sum(supply)
                if diff < -1e-8:
                    messagebox.showwarning(
                        "输入错误",
                        f"当前是销大于产问题，但产量大于销量：产量 {sum(supply):g}，销量 {sum(demand):g}",
                    )
                    return
                if diff > 1e-8:
                    self._add_dummy_source(diff)
                    balance_note = f"已在上方表格增加虚拟产地，供应量 = {diff:g}，单位运费 = 0"
                    m, n, cost, supply, demand = self._read_table_data()
            result = solve_transport(cost.tolist(), supply, demand)

            self.result_text.delete("1.0", "end")
            if result.status != "optimal":
                self.result_text.insert("end", f"求解失败：{result.status}")
                return

            self.result_text.insert("end",
                f"最优运输方案  最小总费用 = {result.total_cost:.2f}")
            if balance_note:
                self.result_text.insert("end", "\n" + balance_note)
            display_cost = cost.tolist()
            display_supply = list(supply)
            display_demand = list(demand)
            if result.dummy_added == "col":
                shortage = sum(supply) - sum(demand)
                display_cost = [row + [0.0] for row in display_cost]
                display_demand.append(shortage)
                self.result_text.insert(
                    "end",
                    f"\n已自动增加虚拟销地，需求量 = {shortage:g}，单位运费 = 0",
                )
            elif result.dummy_added == "row":
                shortage = sum(demand) - sum(supply)
                display_cost.append([0.0] * len(display_demand))
                display_supply.append(shortage)
                self.result_text.insert(
                    "end",
                    f"\n已自动增加虚拟产地，供应量 = {shortage:g}，单位运费 = 0",
                )
            x_opt = result.allocation
            self._show_lp_result(display_cost, display_supply, display_demand,
                                 x_opt, result.total_cost)

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

        n = len(demand)
        m = len(supply)
        total_vars = m * n
        total_cons = m + n

        c_flat = [float(cost_orig[i][j]) for i in range(m) for j in range(n)]
        x_flat = [float(x_opt[i][j]) for i in range(m) for j in range(n)]

        A, b_vec, rels = [], [], []
        for ii in range(m):
            row = [0] * total_vars
            for j in range(n): row[ii * n + j] = 1
            A.append(row); b_vec.append(supply[ii]); rels.append("=")
        for j in range(n):
            row = [0] * total_vars
            for ii in range(m): row[ii * n + j] = 1
            A.append(row); b_vec.append(demand[j]); rels.append("=")

        HDR = "#f5ef96"; RHS = "#f6c5c9"; OPT = "#b7d5f5"; BG = self.PAGE_BG; W = 7
        ROW_LABEL_W = 6

        def L(p, text, bg, font=("宋体", 10), **kw):
            return tk.Label(p, text=text, bg=bg, font=font, relief="ridge", **kw)

        parent = getattr(self, "_lp_result_parent", self.body)
        outer = tk.Frame(parent, bg=BG, highlightthickness=1, highlightbackground=self.PANEL_LINE)
        outer.grid(row=1, column=0, columnspan=2, pady=(0, 12), sticky="nw")
        self._lp_result_frame = outer

        r = 0
        tk.Label(outer, text="目标函数系数", bg=BG,
                 font=("宋体", 10, "bold")).grid(
                 row=r, column=0, sticky="w", columnspan=total_vars + 5, padx=4, pady=(4, 0))
        r += 1
        tk.Label(outer, text="", bg=BG, width=ROW_LABEL_W, relief="flat").grid(row=r, column=0)
        for k in range(total_vars):
            L(outer, xname(k), HDR, width=W).grid(row=r, column=k + 1, padx=1, pady=1)
        r += 1
        tk.Label(outer, text="", bg=BG, width=ROW_LABEL_W, relief="flat").grid(row=r, column=0)
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
            L(outer, str(ci + 1), HDR, width=ROW_LABEL_W).grid(row=r, column=0, padx=1, pady=1)
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
        L(outer, "最优解", HDR, font=("宋体", 10, "bold"), width=ROW_LABEL_W).grid(
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

        def _is_num(s):
            value = s.strip()
            if value == "":
                return True
            if value.upper() == "M":
                return True
            try:
                float(value); return True
            except ValueError:
                return False

        def _set(entry, val):
            val = val.strip()
            if val:
                entry.delete(0, "end")
                entry.insert(0, val)

        def _split_row(line: str) -> list[str]:
            if "\t" in line:
                cells: list[str] = []
                for part in line.split("\t"):
                    stripped = part.strip()
                    if stripped and not _is_num(stripped) and " " in stripped:
                        pieces = stripped.split()
                        if all(_is_num(piece) for piece in pieces):
                            cells.extend(pieces)
                            continue
                    cells.append(part)
                return cells
            return line.split()

        raw_rows = [_split_row(ln) for ln in text.strip().splitlines() if ln.strip()]
        if not raw_rows:
            return "break"

        if len(raw_rows) == 1 and len(raw_rows[0]) == 1 and "\t" not in text:
            w = event.widget
            try:
                if w.selection_present():
                    w.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except Exception:
                pass
            w.insert(tk.INSERT, text.strip())
            return "break"

        skip_row = 1 if len(raw_rows) > 1 and any(not _is_num(c) and c.strip() for c in raw_rows[0]) else 0
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
            has_supply_col = False
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

            if start_r == 0 and start_c == 0:
                n_cost_rows = demand_row_idx if demand_row_idx is not None else len(data)
                if self.mode != "指派":
                    d_last = data[demand_row_idx][-1].strip() if demand_row_idx is not None and data[demand_row_idx] else ""
                    c_lasts = [data[ri][-1].strip() for ri in range(n_cost_rows) if data[ri]]
                    header_last = ""
                    if skip_row == 1 and raw_rows and raw_rows[0]:
                        header_last = raw_rows[0][-1].strip().lower()
                    header_supply = any(kw in header_last for kw in ["产量", "供应", "supply"])
                    fits_current_supply_col = (
                        demand_row_idx is None
                        and len({len(row) for row in data[:n_cost_rows] if row}) == 1
                        and len(data[0]) == n + 1
                    )
                    has_supply_col = (
                        bool(c_lasts)
                        and all(_is_num(v) and v for v in c_lasts)
                        and ((demand_row_idx is not None and not d_last) or header_supply or fits_current_supply_col)
                    )
                new_m = n_cost_rows
                new_n = max((len(row) for row in data[:n_cost_rows]), default=0)
                if self.mode != "指派" and has_supply_col:
                    new_n -= 1
                if self.mode == "指派":
                    new_n = max(new_m, new_n)
                if new_m > 0 and new_n > 0 and (new_m != m or new_n != n):
                    self.n_src.set(new_m)
                    if self.mode != "指派":
                        self.n_dst.set(new_n)
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
