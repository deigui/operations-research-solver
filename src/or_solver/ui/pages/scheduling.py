"""合理排班问题页。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from or_solver.constants import FONT_SMALL
from or_solver.core.scheduling_solver import solve_shift_schedule
from or_solver.io import autosave
from or_solver.ui.charts import draw_bar_chart
from or_solver.ui.mixins import TableEditMixin


class SchedulingPage(tk.Frame, TableEditMixin):
    def __init__(self, master: tk.Widget, controller):
        super().__init__(master, bg="#e8e0d0")
        self.controller = controller
        self.n_periods = tk.IntVar(value=7)
        self.work_days = tk.IntVar(value=5)
        self.built = False
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg="#c8b89a", relief="raised", bd=1)
        hdr.pack(fill="x")
        tk.Label(hdr, text="运筹学模型求解系统———合理排班问题",
                 font=("宋体", 13, "bold"), bg="#c8b89a").pack(pady=4)
        ctrl = tk.Frame(hdr, bg="#c8b89a")
        ctrl.pack(pady=(0, 4))
        tk.Label(ctrl, text="时间段数:", bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(8, 0))
        tk.Spinbox(ctrl, from_=2, to=14, textvariable=self.n_periods,
                   width=4, font=FONT_SMALL).pack(side="left", padx=2)
        tk.Label(ctrl, text="每人连续工作天数:", bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(12, 0))
        tk.Spinbox(ctrl, from_=1, to=13, textvariable=self.work_days,
                   width=4, font=FONT_SMALL).pack(side="left", padx=2)
        tk.Button(ctrl, text="确  定", command=self._build_table,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=8)
        tk.Button(ctrl, text="求  解", command=self._solve,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=2)
        tk.Button(ctrl, text="返  回", command=self.controller.show_menu,
                  bg="#dddddd", font=FONT_SMALL, width=7).pack(side="left", padx=2)
        tk.Button(ctrl, text="恢复历史", command=self._load_history,
                  bg="#ffd700", font=FONT_SMALL, width=8).pack(side="left", padx=6)

        main_pane = tk.Frame(self, bg="#e8e0d0")
        main_pane.pack(fill="both", expand=True)

        left_pane = tk.Frame(main_pane, bg="#e8e0d0")
        left_pane.pack(side="left", fill="both", expand=False)

        expr_frame = tk.Frame(left_pane, bg="#f5f0e0", relief="groove", bd=1, height=200)
        expr_frame.pack(fill="x", padx=2, pady=(2, 0))
        expr_frame.pack_propagate(False)
        top_row = tk.Frame(expr_frame, bg="#f5f0e0")
        top_row.pack(fill="x", padx=6, pady=(4, 2))
        tk.Label(top_row, text="模型表达式（自动生成/可复制）:",
                 bg="#f5f0e0", font=("宋体", 9, "bold")).pack(side="left")
        tk.Button(top_row, text="清  空",
                  command=lambda: self.expr_text.delete("1.0", "end"),
                  bg="#ffcccc", font=("宋体", 9), width=6).pack(side="left", padx=4)
        self.expr_text = tk.Text(expr_frame, font=("Consolas", 10), bg="#fffff0",
                                 relief="sunken", bd=1)
        self.expr_text.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        left_bottom = tk.Frame(left_pane, bg="#e8e0d0")
        left_bottom.pack(fill="both", expand=True, padx=2, pady=2)
        vsb = tk.Scrollbar(left_bottom, orient="vertical")
        hsb = tk.Scrollbar(left_bottom, orient="horizontal")
        canvas = tk.Canvas(left_bottom, bg="#e8e0d0", width=580,
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
        right_pane.pack(side="left", fill="both", expand=True, padx=4, pady=2)

        tk.Label(right_pane, text="── 求解步骤 ──",
                 bg="#f5f5f0", font=("宋体", 10, "bold")).pack(pady=(4, 2))
        step_outer = tk.Frame(right_pane, bg="#f5f5f0")
        step_outer.pack(fill="both", expand=True, padx=4, pady=(0, 2))
        vsb3 = tk.Scrollbar(step_outer, orient="vertical")
        self.step_text = tk.Text(step_outer, font=("Consolas", 10),
                                 bg="#fffff0", yscrollcommand=vsb3.set,
                                 wrap="none", state="disabled")
        vsb3.config(command=self.step_text.yview)
        vsb3.pack(side="right", fill="y")
        self.step_text.pack(fill="both", expand=True)

        self.chart_frame = tk.Frame(right_pane, bg="#f5f5f0", relief="groove", bd=1, height=300)
        self.chart_frame.pack(fill="x", padx=4, pady=(0, 4))
        self.chart_frame.pack_propagate(False)
        tk.Label(self.chart_frame, text="求解后自动显示排班图",
                 bg="#f5f5f0", fg="#888", font=("宋体", 9)).pack(expand=True)

        self.after(100, self._load_example)

    # ── TableEditMixin 接口 ───────────────────────────────
    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            if c == 0 and hasattr(self, "period_entries") and r < len(self.period_entries):
                return self.period_entries[r]
            if c == 1 and hasattr(self, "need_entries") and r < len(self.need_entries):
                return self.need_entries[r]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        return "#fffff0" if c == 0 else "#ffff99"

    def _all_entries(self):
        try:
            if hasattr(self, "period_entries"):
                for i, e in enumerate(self.period_entries):
                    yield (i, 0, e)
            if hasattr(self, "need_entries"):
                for i, e in enumerate(self.need_entries):
                    yield (i, 1, e)
        except AttributeError:
            return

    # ── 建表 ────────────────────────────────────────────
    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        n = self.n_periods.get()
        BG = "#e8e0d0"; HDR = "#ffcc99"; YELL = "#ffff99"; W = 12
        subs = "₁₂₃₄₅₆₇₈₉"

        for k, h in enumerate(["时段编号", "时段名称", "最少需求人数", "开班人数(xi)"]):
            tk.Label(self.body, text=h, bg=HDR, font=("宋体", 9),
                     relief="ridge", width=W).grid(row=0, column=k, padx=1, pady=1)

        self.period_entries: list[tk.Entry] = []
        self.need_entries: list[tk.Entry] = []
        self.result_labels: list[tk.Label] = []

        for i in range(n):
            tk.Label(self.body, text=f"第{i+1}段", bg=BG,
                     font=("宋体", 9), width=W).grid(row=i + 1, column=0, padx=1, pady=1)
            pe = tk.Entry(self.body, width=W, font=("宋体", 9), bg="#fffff0")
            pe.insert(0, f"时段{i+1}")
            pe.grid(row=i + 1, column=1, padx=1, pady=1)
            self._bind_cell(pe, i, 0)
            self.period_entries.append(pe)

            ne = tk.Entry(self.body, width=W, font=("宋体", 9), bg=YELL)
            ne.grid(row=i + 1, column=2, padx=1, pady=1)
            self._bind_cell(ne, i, 1)
            self.need_entries.append(ne)

            vn = f"x{subs[i]}" if i < len(subs) else f"x{i+1}"
            rl = tk.Label(self.body, text=vn, bg="#b2dfdb",
                          font=("宋体", 9), relief="sunken", width=W)
            rl.grid(row=i + 1, column=3, padx=1, pady=1)
            self.result_labels.append(rl)

        res_row = n + 2
        tk.Label(self.body, text="最少总人数", bg=BG,
                 font=("宋体", 10, "bold")).grid(row=res_row, column=0, columnspan=3,
                                                 sticky="e", padx=4, pady=(8, 2))
        self.total_label = tk.Label(self.body, text="", bg="#ef9a9a",
                                    font=("宋体", 11, "bold"), relief="sunken", width=W)
        self.total_label.grid(row=res_row, column=3, padx=1, pady=2)
        self.built = True

    # ── 求解 ────────────────────────────────────────────
    def _solve(self):
        if not self.built:
            messagebox.showwarning("提示", "请先点击【确定】")
            return
        try:
            n = self.n_periods.get()
            k = self.work_days.get()
            demands = [float(e.get() or 0) for e in self.need_entries]
            names = [e.get() for e in self.period_entries]
            autosave.save("合理排班", {"n": n, "k": k, "names": names, "demands": demands})

            result = solve_shift_schedule(demands, k)
            if result.status != "optimal":
                messagebox.showerror("求解失败", result.message)
                return

            x = result.x
            total = result.total
            subs = "₁₂₃₄₅₆₇₈₉"
            vnames = [f"x{subs[i]}" if i < len(subs) else f"x{i+1}" for i in range(n)]

            for i, rl in enumerate(self.result_labels):
                rl.config(text=str(round(x[i])))
            self.total_label.config(text=str(round(total)))

            # 模型表达式
            self.expr_text.delete("1.0", "end")
            self.expr_text.insert("end", f"min  Z = {' + '.join(vnames)}\n\ns.t.\n")
            for i in range(n):
                vs = sorted([(i - j) % n for j in range(k)])
                lhs = " + ".join(vnames[v] for v in vs)
                self.expr_text.insert("end", f"  {lhs} >= {int(demands[i])}  ({names[i]})\n")
            self.expr_text.insert("end", "\n")
            for v in vnames:
                self.expr_text.insert("end", f"  {v} >= 0\n")

            # 求解步骤
            rest = n - k
            self.step_text.config(state="normal")
            self.step_text.delete("1.0", "end")
            self.step_text.tag_config("title", foreground="#1a5276", font=("宋体", 10, "bold"))
            self.step_text.tag_config("data",  foreground="#196F3D", font=("Consolas", 10))
            self.step_text.tag_config("result", foreground="#922B21", font=("Consolas", 10, "bold"))
            self.step_text.insert("end", "【问题描述】\n", "title")
            self.step_text.insert("end",
                f"  共{n}个时间段，每人连续工作{k}天，休息{rest}天\n  各时段需求：\n", "data")
            for i in range(n):
                self.step_text.insert("end", f"    {names[i]}：需要 {int(demands[i])} 人\n", "data")
            self.step_text.insert("end", "\n【最优解】\n", "title")
            for i in range(n):
                od = result.actual_on_duty[i]
                self.step_text.insert("end",
                    f"  {names[i]}：开班{round(x[i])}人，实际在班{od:.0f}人"
                    f"（需求{int(demands[i])}人，{'✓' if od >= demands[i] - 1e-6 else '✗'}）\n", "data")
            self.step_text.insert("end", f"\n  最少总人数：{round(total)} 人\n", "result")
            self.step_text.config(state="disabled")
            self.step_text.see("end")

            draw_bar_chart(
                self.chart_frame,
                categories=names,
                series={"需求人数": demands, "开班人数": [round(v) for v in x]},
                title="各时段需求与开班人数对比",
                ylabel="人数",
            )
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ── 辅助 ────────────────────────────────────────────
    def _load_example(self):
        self.n_periods.set(7)
        self.work_days.set(5)
        self._build_table()
        defaults = [20, 24, 25, 20, 28, 32, 34]
        labels = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        for i, (v, lbl) in enumerate(zip(defaults, labels)):
            self.need_entries[i].delete(0, "end")
            self.need_entries[i].insert(0, str(v))
            self.period_entries[i].delete(0, "end")
            self.period_entries[i].insert(0, lbl)

    def _load_history(self):
        data = autosave.load("合理排班")
        if not data:
            messagebox.showinfo("恢复历史", "暂无历史数据")
            return
        self.n_periods.set(data["n"])
        self.work_days.set(data["k"])
        self._build_table()
        for i, (nm, nd) in enumerate(zip(data["names"], data["demands"])):
            self.period_entries[i].delete(0, "end")
            self.period_entries[i].insert(0, nm)
            self.need_entries[i].delete(0, "end")
            self.need_entries[i].insert(0, str(nd))
        messagebox.showinfo("恢复历史", "历史数据已恢复")
