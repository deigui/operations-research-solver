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

    IMPLEMENTED: set[str] = {
        "线性规划问题", "纯整数规划", "0-1整数规划", "混合整数规划",
        "产销平衡问题", "产大于销问题", "销大于产问题", "指派问题",
        "最大最小准则", "最大最大准则", "后悔值准则", "期望值准则",
        "乐观系数准则", "等可能性准则",
        "最短路问题", "最小支撑树",
        "移动平均法", "指数平滑法", "回归分析法",
        "合理排班问题",
    }

    COL_COLORS: dict[str, str] = {
        "决策分析": BTN_PINK,
        "线性规划": "#ce93d8",
        "整数规划": "#80cbc4",
        "运输问题": "#80deea",
        "目标规划": "#a5d6a7",
        "网络优化": "#b0bec5",
        "预测问题": "#ffcc80",
    }

    def __init__(self, master: tk.Widget, controller):
        super().__init__(master, bg=BG_DARK)
        self.controller = controller
        self._build()

    def _build(self):
        tk.Label(self, text="运筹学模型求解程序",
                 font=("微软雅黑", 20, "bold"), bg=BG_DARK, fg=FG_GOLD).pack(pady=12)

        grid = tk.Frame(self, bg=BG_DARK)
        grid.pack(padx=20, pady=4)

        for col, (cat, items) in enumerate(self.MENU.items()):
            color = self.COL_COLORS[cat]
            tk.Label(grid, text=cat, bg=color, fg="#333",
                     font=("微软雅黑", 11, "bold"),
                     relief="raised", bd=1, width=12, pady=4
                     ).grid(row=0, column=col, padx=4, pady=4)
            for row, item in enumerate(items, 1):
                state = "normal" if item in self.IMPLEMENTED else "disabled"
                tk.Button(
                    grid, text=item, width=12, font=FONT_SMALL,
                    bg="#e8f5e9" if state == "normal" else "#dddddd",
                    fg="#222" if state == "normal" else "#888",
                    relief="groove", bd=1, state=state,
                    cursor="hand2" if state == "normal" else "arrow",
                    command=lambda i=item: self.controller.open_solver(i),
                ).grid(row=row, column=col, padx=4, pady=2)

        bot = tk.Frame(self, bg=BG_DARK)
        bot.pack(pady=14)
        tk.Button(bot, text="返回主页", font=("微软雅黑", 11),
                  bg="#555", fg="#fff", width=12,
                  command=self.controller.show_home).pack(side="left", padx=8)
        tk.Button(bot, text="退出系统", font=("微软雅黑", 11),
                  bg="#555", fg="#fff", width=12,
                  command=self.controller.quit_app).pack(side="left", padx=8)
