"""Priority goal programming page."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from or_solver.constants import BTN_GREEN, FONT_SMALL
from or_solver.core.goal_solver import solve_preemptive_goal_lp
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button


class PriorityGoalPage(tk.Frame, TableEditMixin):
    """A dedicated input page for preemptive goal programming."""

    def __init__(self, master: tk.Widget, controller):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.n_vars = tk.IntVar(value=2)
        self.n_goals = tk.IntVar(value=5)
        self.n_priorities = tk.IntVar(value=3)
        self._tbl_init_sel()
        self._table_entries: dict[tuple[int, int], tk.Entry] = {}
        self._table_bgs: dict[tuple[int, int], str] = {}
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self, bg="#d7ccc8")
        header.pack(fill="x")
        controls = tk.Frame(header, bg="#d7ccc8")
        controls.pack(anchor="center", pady=6)

        for text, var in (
            ("决策变量数:", self.n_vars),
            ("目标约束数:", self.n_goals),
            ("优先级数:", self.n_priorities),
        ):
            tk.Label(controls, text=text, bg="#d7ccc8", font=FONT_SMALL).pack(
                side="left", padx=(12, 2)
            )
            tk.Spinbox(controls, from_=1, to=30, textvariable=var, width=4,
                       font=FONT_SMALL).pack(side="left")

        make_button(controls, "确 定", self._build_tables, bg=BTN_GREEN, width=8).pack(
            side="left", padx=(14, 4)
        )
        make_button(controls, "示例填充", self._load_default_example,
                    bg="#8d6e63", fg="white", width=10).pack(side="left", padx=4)
        make_button(controls, "求 解", self._solve, bg="#e53935",
                    fg="white", width=8).pack(side="left", padx=4)

        main = tk.Frame(self, bg="#f5f0e8")
        main.pack(fill="both", expand=True, padx=10, pady=8)
        canvas = tk.Canvas(main, bg="#f5f0e8", highlightthickness=0)
        ysb = tk.Scrollbar(main, orient="vertical", command=canvas.yview)
        xsb = tk.Scrollbar(main, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        ysb.pack(side="right", fill="y")
        xsb.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)

        self.body = tk.Frame(canvas, bg="#f5f0e8")
        canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        self._build_tables()
        self._load_default_example()

    def _build_tables(self) -> None:
        for widget in self.body.winfo_children():
            widget.destroy()
        self._tbl_init_sel()
        self._table_entries = {}
        self._table_bgs = {}

        n = self.n_vars.get()
        g = self.n_goals.get()

        top = tk.Frame(self.body, bg="#f5f0e8")
        top.grid(row=0, column=0, sticky="nw")

        self._build_model_hint(top)
        self._build_goal_table(top, n, g)
        self._build_priority_table(top, g)
        self._build_result_area(top)
        self._build_stage_area(top)

    def _build_model_hint(self, parent: tk.Widget) -> None:
        box = tk.Frame(parent, bg="#f5f0e8", highlightthickness=1,
                       highlightbackground="#d1c8bc")
        box.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 10), pady=(0, 8))
        tk.Label(box, text="模型说明", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
        text = (
            "目标约束统一按标准型处理：函数值 - d+ + d = 目标值。\n"
            "这里 d 表示负偏差，d+ 表示正偏差；例如 P1: d1+ + d2，P2: d3，P3: d4 + 2d5。"
        )
        tk.Label(box, text=text, justify="left", bg="#f5f0e8",
                 fg="#555", font=FONT_SMALL).pack(anchor="w", padx=12, pady=(0, 8))

    def _build_goal_table(self, parent: tk.Widget, n: int, g: int) -> None:
        box = tk.Frame(parent, bg="#f5f0e8", highlightthickness=1,
                       highlightbackground="#d1c8bc")
        box.grid(row=1, column=0, sticky="nw", padx=(0, 10), pady=(0, 8))
        tk.Label(box, text="目标约束", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )

        table = tk.Frame(box, bg="#d2c9bd")
        table.grid(row=1, column=0, padx=12, pady=(0, 12))
        headers = ["目标"] + [f"x{j + 1}" for j in range(n)] + [
            "关系", "目标值", "d", "d+"
        ]
        for c, header in enumerate(headers):
            self._cell_label(table, header, 0, c, width=9 if c == 0 else 10)

        for r in range(g):
            self._cell_label(table, str(r + 1), r + 1, 0, width=9, bg="#f7efe2")
            for c in range(n):
                self._entry(table, r + 1, c + 1, (100 + r, c), bg="#eef8ef")
            self._cell_label(table, "=", r + 1, n + 1, bg="#f0f0f0")
            self._entry(table, r + 1, n + 2, (100 + r, n), bg="#fff6b7")
            self._cell_label(table, f"d{r + 1}", r + 1, n + 3, bg="#c8f1f3")
            self._cell_label(table, f"d{r + 1}+", r + 1, n + 4, bg="#f8a5a8")

    def _build_priority_table(self, parent: tk.Widget, g: int) -> None:
        box = tk.Frame(parent, bg="#f5f0e8", highlightthickness=1,
                       highlightbackground="#d1c8bc")
        box.grid(row=1, column=1, sticky="nw", pady=(0, 8))
        tk.Label(box, text="优先级目标", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 2)
        )
        tk.Label(box, text="每行是一个优先级，空白按 0 处理。",
                 bg="#f5f0e8", fg="#555", font=FONT_SMALL).grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 6)
        )

        table = tk.Frame(box, bg="#d2c9bd")
        table.grid(row=2, column=0, padx=12, pady=(0, 12))
        headers = ["优先级"]
        for k in range(g):
            headers.extend([f"d{k + 1}", f"d{k + 1}+"])
        for c, header in enumerate(headers):
            self._cell_label(table, header, 0, c, width=8)

        for r in range(self.n_priorities.get()):
            self._cell_label(table, f"P{r + 1}", r + 1, 0, width=8, bg="#f7efe2")
            for c in range(g * 2):
                self._entry(table, r + 1, c + 1, (200 + r, c), width=8, bg="#eef8ef")

    def _build_result_area(self, parent: tk.Widget) -> None:
        box = tk.Frame(parent, bg="#f5f0e8", highlightthickness=1,
                       highlightbackground="#d1c8bc")
        box.grid(row=2, column=0, columnspan=2, sticky="nw", pady=(4, 0))
        tk.Label(box, text="求解结果", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        self.result_text = tk.Text(
            box,
            height=14,
            width=132,
            bg="#fffde7",
            font=("Consolas", 10),
            relief="flat",
            highlightthickness=1,
            highlightbackground="#d1c8bc",
        )
        self.result_text.pack(side="left", padx=(12, 0), pady=(0, 12))
        ysb = tk.Scrollbar(box, orient="vertical", command=self.result_text.yview)
        ysb.pack(side="left", fill="y", pady=(0, 12), padx=(0, 12))
        self.result_text.configure(yscrollcommand=ysb.set)

    def _build_stage_area(self, parent: tk.Widget) -> None:
        box = tk.Frame(parent, bg="#f5f0e8", highlightthickness=1,
                       highlightbackground="#d1c8bc")
        box.grid(row=3, column=0, columnspan=2, sticky="nw", pady=(8, 0))
        tk.Label(box, text="分级求解模型", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 6)
        )

        stages = [
            (
                "第一级：min d1+ + d2",
                "min  d1+ + d2\n\n"
                "s.t.\n"
                "200x1 + 300x2 - d1+ + d1 = 68000\n"
                "200x1 + 300x2 - d2+ + d2 = 60000\n"
                "x1, x2, d1, d1+, d2, d2+ >= 0",
            ),
            (
                "第二级：min d3",
                "min  d3\n\n"
                "s.t.\n"
                "200x1 + 300x2 - d1+ + d1 = 68000\n"
                "200x1 + 300x2 - d2+ + d2 = 60000\n"
                "250x1 + 125x2 - d3+ + d3 = 70000\n"
                "并保持第一级目标值最优：d1+ + d2 = 0\n"
                "x1, x2, d, d+ >= 0",
            ),
            (
                "第三级：min d4 + 2d5",
                "min  d4 + 2d5\n\n"
                "s.t.\n"
                "200x1 + 300x2 - d1+ + d1 = 68000\n"
                "200x1 + 300x2 - d2+ + d2 = 60000\n"
                "250x1 + 125x2 - d3+ + d3 = 70000\n"
                "x1 - d4+ + d4 = 200\n"
                "x2 - d5+ + d5 = 120\n"
                "并保持前两级目标值最优：d1+ + d2 = 0, d3 = 0\n"
                "x1, x2, d, d+ >= 0",
            ),
        ]

        for c, (title, content) in enumerate(stages):
            panel = tk.Frame(box, bg="#f5f0e8", highlightthickness=1,
                             highlightbackground="#d1c8bc")
            panel.grid(row=1, column=c, sticky="nw", padx=(12 if c == 0 else 4, 8),
                       pady=(0, 12))
            tk.Label(panel, text=title, bg="#f5f0e8", fg="#0b4f6c",
                     font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
            text = tk.Text(panel, height=10, width=42, bg="#fffde7",
                           font=("Consolas", 9), relief="flat",
                           highlightthickness=1, highlightbackground="#d1c8bc",
                           wrap="word")
            text.pack(padx=8, pady=(0, 8))
            text.insert("1.0", content)
            text.configure(state="disabled")

    def _cell_label(
        self,
        parent: tk.Widget,
        text: str,
        row: int,
        col: int,
        *,
        width: int = 10,
        bg: str = "#f4d7a5",
    ) -> None:
        tk.Label(parent, text=text, width=width, bg=bg, fg="#222",
                 font=FONT_SMALL, relief="flat", bd=0).grid(
            row=row, column=col, padx=1, pady=1, ipady=4, sticky="nsew"
        )

    def _entry(
        self,
        parent: tk.Widget,
        row: int,
        col: int,
        key: tuple[int, int],
        *,
        width: int = 10,
        bg: str = "#eef8ef",
    ) -> tk.Entry:
        entry = tk.Entry(parent, width=width, font=FONT_SMALL, bg=bg,
                         relief="flat", bd=0, highlightthickness=0)
        entry.grid(row=row, column=col, padx=1, pady=1, ipady=4, sticky="nsew")
        self._table_entries[key] = entry
        self._table_bgs[key] = bg
        self._bind_cell(entry, key[0], key[1])
        return entry

    def _entry_frame(self):
        return self.body

    def _entry_at(self, r: int, c: int):
        return self._table_entries.get((r, c))

    def _entry_default_bg(self, r: int, c: int) -> str:
        return self._table_bgs.get((r, c), "#eef8ef")

    def _all_entries(self):
        for (r, c), entry in self._table_entries.items():
            yield r, c, entry

    def _set_value(self, key: tuple[int, int], value: float | int | str) -> None:
        entry = self._table_entries.get(key)
        if entry is None:
            return
        entry.delete(0, "end")
        entry.insert(0, str(value))

    def _value(self, key: tuple[int, int]) -> float:
        entry = self._table_entries.get(key)
        if entry is None:
            return 0.0
        text = entry.get().strip()
        return float(text) if text else 0.0

    def _load_default_example(self) -> None:
        self.n_vars.set(2)
        self.n_goals.set(5)
        self.n_priorities.set(3)
        if not self._table_entries or self._entry_at(104, 1) is None:
            self._build_tables()

        for _, _, entry in self._all_entries():
            entry.delete(0, "end")

        goals = [
            (200, 300, 68000),
            (200, 300, 60000),
            (250, 125, 70000),
            (1, 0, 200),
            (0, 1, 120),
        ]
        for r, (x1, x2, target) in enumerate(goals):
            self._set_value((100 + r, 0), x1)
            self._set_value((100 + r, 1), x2)
            self._set_value((100 + r, 2), target)

        # Columns are d1, d1+, d2, d2+, ...
        priorities = [
            {1: 1, 2: 1},      # P1: d1+ + d2
            {4: 1},            # P2: d3
            {6: 1, 8: 2},      # P3: d4 + 2d5
        ]
        for r, row in enumerate(priorities):
            for c, value in row.items():
                self._set_value((200 + r, c), value)

        self.result_text.delete("1.0", "end")

    def _solve(self) -> None:
        try:
            n = self.n_vars.get()
            g = self.n_goals.get()
            total_vars = n + g * 2
            A: list[list[float]] = []
            b: list[float] = []
            rels: list[str] = []

            for r in range(g):
                row = [0.0] * total_vars
                for c in range(n):
                    row[c] = self._value((100 + r, c))
                dm_idx = n + r * 2
                dp_idx = n + r * 2 + 1
                row[dm_idx] = 1.0
                row[dp_idx] = -1.0
                A.append(row)
                b.append(self._value((100 + r, n)))
                rels.append("=")

            priority_objectives: list[list[float]] = []
            for r in range(self.n_priorities.get()):
                obj = [0.0] * total_vars
                for c in range(g * 2):
                    obj[n + c] = self._value((200 + r, c))
                if any(abs(v) > 1e-12 for v in obj):
                    priority_objectives.append(obj)

            if not priority_objectives:
                raise ValueError("请至少填写一个优先级目标")

            result = solve_preemptive_goal_lp(priority_objectives, A, b, rels)
            if result.status != "optimal":
                raise ValueError(result.message or "无可行解")
            self._show_result(result, n, g, A, b)
        except Exception as exc:
            messagebox.showerror("求解失败", str(exc))

    def _show_result(self, result, n: int, g: int, A, b) -> None:
        def fmt(value: float) -> str:
            if abs(value) < 1e-8:
                return "0"
            if abs(value - round(value)) < 1e-7:
                return str(int(round(value)))
            return f"{value:.6g}"

        names = [f"x{j + 1}" for j in range(n)]
        for k in range(g):
            names.extend([f"d{k + 1}", f"d{k + 1}+"])

        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", "【优先级目标规划求解结果】\n\n")
        for stage in result.stage_results:
            self.result_text.insert(
                "end", f"第{stage.priority}级目标值 = {fmt(stage.objective_value)}\n"
            )

        self.result_text.insert("end", "\n【最优解】\n")
        for name, value in zip(names, result.x):
            self.result_text.insert("end", f"{name} = {fmt(value)}\n")

        self.result_text.insert("end", "\n【目标约束实际值】\n")
        for r in range(g):
            actual = sum(A[r][c] * result.x[c] for c in range(n))
            self.result_text.insert(
                "end",
                f"G{r + 1}: 左端函数值 = {fmt(actual)}, 目标值 = {fmt(b[r])}\n",
            )
