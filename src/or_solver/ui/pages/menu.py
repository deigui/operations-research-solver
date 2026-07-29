"""功能菜单页。"""
from __future__ import annotations

import tkinter as tk

from or_solver.constants import BG_DARK, BTN_PINK, FG_GOLD, FONT_SMALL


class MenuPage(tk.Frame):
    MENU: dict[str, list[str]] = {
        "决策分析": [
            "最大最小准则", "最大最大准则", "乐观系数准则",
            "等可能性准则", "后悔值准则", "期望值准则",
            "全情报准则", "部分情报准则", "效用值准则",
        ],
        "线性规划": [
            "线性规划问题", "表格式线性规划", "连续投资问题",
            "产品自制与外协", "生产安排问题", "合理排班问题",
            "已穷举套材下料", "待穷举套材下料", "灰色线性规划",
        ],
        "整数规划": [
            "纯整数规划", "0-1整数规划", "混合整数规划",
            "投资与选址", "整数连续投资",
        ],
        "运输问题": ["产销平衡问题", "产大于销问题", "销大于产问题", "指派问题"],
        "目标规划": ["优先级目标", "加权目标规划"],
        "网络优化": [
            "最短路问题", "最大流问题", "最小费用流",
            "最小费最大流", "最小支撑树", "循环最短路",
        ],
        "预测问题": [
            "移动平均法", "指数平滑法", "加权移动平均",
            "趋势投影法", "趋势季节因素", "回归分析法",
        ],
    }

    IMPLEMENTED: set[str] = {item for items in MENU.values() for item in items}

    COL_COLORS: dict[str, str] = {
        "决策分析": BTN_PINK,
        "线性规划": "#ce93d8",
        "整数规划": "#80cbc4",
        "运输问题": "#80deea",
        "目标规划": "#a5d6a7",
        "网络优化": "#b0bec5",
        "预测问题": "#ffcc80",
    }

    def __init__(self, master: tk.Widget, controller, initial_category: str | None = None):
        super().__init__(master, bg=BG_DARK)
        self.controller = controller
        category = initial_category if initial_category in self.MENU else next(iter(self.MENU))
        self.active_category = tk.StringVar(value=category)
        self.category_buttons: dict[str, tk.Button] = {}
        self._build()

    def _build(self):
        tk.Label(self, text="运筹学模型求解程序",
                 font=("微软雅黑", 20, "bold"), bg=BG_DARK, fg=FG_GOLD).pack(pady=12)

        shell = tk.Frame(self, bg=BG_DARK)
        shell.pack(fill="both", expand=True, padx=34, pady=(0, 10))

        tk.Label(shell, text="一级分类", font=("微软雅黑", 11, "bold"),
                 bg=BG_DARK, fg="#f0f0f0").pack(anchor="w", pady=(0, 8))

        self.category_bar = tk.Frame(shell, bg=BG_DARK)
        self.category_bar.pack(fill="x")
        for col, cat in enumerate(self.MENU.keys()):
            btn = tk.Button(
                self.category_bar,
                text=cat,
                bg=self.COL_COLORS[cat],
                fg="#333",
                font=("微软雅黑", 11, "bold"),
                relief="raised",
                bd=1,
                cursor="hand2",
                command=lambda c=cat: self._select_category(c),
            )
            btn.grid(row=0, column=col, padx=4, pady=4, sticky="ew")
            self.category_bar.grid_columnconfigure(col, weight=1, uniform="menu_cat")
            self.category_buttons[cat] = btn

        self.item_panel = tk.Frame(shell, bg="#f7f3ea", highlightthickness=1, highlightbackground="#c8bda7")
        self.item_panel.pack(fill="both", expand=True, pady=(6, 0))
        self._render_items()

        bot = tk.Frame(self, bg=BG_DARK)
        bot.pack(pady=14)
        tk.Button(bot, text="返回主页", font=("微软雅黑", 11),
                  bg="#555", fg="#fff", width=12,
                  command=self.controller.show_home).pack(side="left", padx=8)
        tk.Button(bot, text="退出系统", font=("微软雅黑", 11),
                  bg="#555", fg="#fff", width=12,
                  command=self.controller.quit_app).pack(side="left", padx=8)

    def _select_category(self, category: str) -> None:
        self.active_category.set(category)
        self._render_items()

    def select_category(self, category: str) -> None:
        if category in self.MENU:
            self._select_category(category)

    def _render_items(self) -> None:
        for child in self.item_panel.winfo_children():
            child.destroy()

        category = self.active_category.get()
        for cat, btn in self.category_buttons.items():
            btn.configure(relief="sunken" if cat == category else "raised")

        tk.Label(self.item_panel, text=category, font=("微软雅黑", 18, "bold"),
                 bg="#f7f3ea", fg="#243744").pack(anchor="w", padx=22, pady=(18, 10))

        grid = tk.Frame(self.item_panel, bg="#f7f3ea")
        grid.pack(fill="both", expand=True, padx=26, pady=(0, 20))
        for col in range(3):
            grid.grid_columnconfigure(col, weight=1, uniform="solver_item")

        for idx, item in enumerate(self.MENU[category]):
            row, col = divmod(idx, 3)
            state = "normal" if item in self.IMPLEMENTED else "disabled"
            tk.Button(
                grid,
                text=item,
                font=FONT_SMALL,
                bg="#e8f5e9" if state == "normal" else "#dddddd",
                fg="#222" if state == "normal" else "#888",
                relief="groove",
                bd=1,
                state=state,
                cursor="hand2" if state == "normal" else "arrow",
                height=3,
                command=lambda i=item: self._open_item(i),
            ).grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        for row in range((len(self.MENU[category]) + 2) // 3):
            grid.grid_rowconfigure(row, weight=1)

    def _open_item(self, name: str) -> None:
        open_window = getattr(self.controller, "open_solver_window", None)
        if callable(open_window):
            open_window(name)
        else:
            self.controller.open_solver(name)
