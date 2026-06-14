"""应用主控制器（App 窗口）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from or_solver.constants import BG_DARK
from or_solver.ui.pages.home import HomePage
from or_solver.ui.pages.menu import MenuPage
from or_solver.ui.pages.lp import LPPage
from or_solver.ui.pages.transport import TransportPage
from or_solver.ui.pages.decision import DecisionPage
from or_solver.ui.pages.network import ShortestPathPage
from or_solver.ui.pages.mst import MSTPage
from or_solver.ui.pages.scheduling import SchedulingPage
from or_solver.ui.pages.forecast import ForecastPage


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("运筹学模型求解工具")
        self.geometry("1300x800")
        self.resizable(True, True)
        self.configure(bg=BG_DARK)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        self._current: tk.Widget | None = None
        self.show_home()

    # ── 页面切换 ─────────────────────────────────────────
    def _show(self, frame: tk.Widget) -> None:
        if self._current:
            self._current.destroy()
        self._current = frame
        frame.pack(fill="both", expand=True)

    def show_home(self) -> None:
        self._show(HomePage(self, self))

    def show_menu(self) -> None:
        self._show(MenuPage(self, self))

    def open_solver(self, name: str) -> None:
        pages = {
            "线性规划问题": lambda: LPPage(self, self, "线性规划问题"),
            "纯整数规划":   lambda: LPPage(self, self, "纯整数规划", integer_vars=True),
            "0-1整数规划":  lambda: LPPage(self, self, "0-1整数规划", binary_vars=True),
            "混合整数规划": lambda: LPPage(self, self, "混合整数规划", integer_vars=[]),
            "产销平衡问题": lambda: TransportPage(self, self, "平衡"),
            "产大于销问题": lambda: TransportPage(self, self, "产大于销"),
            "销大于产问题": lambda: TransportPage(self, self, "销大于产"),
            "指派问题":     lambda: TransportPage(self, self, "指派"),
            "最大最小准则": lambda: DecisionPage(self, self, "最大最小准则"),
            "最大最大准则": lambda: DecisionPage(self, self, "最大最大准则"),
            "后悔值准则":   lambda: DecisionPage(self, self, "后悔值准则"),
            "期望值准则":   lambda: DecisionPage(self, self, "期望值准则"),
            "乐观系数准则": lambda: DecisionPage(self, self, "乐观系数准则"),
            "等可能性准则": lambda: DecisionPage(self, self, "等可能性准则"),
            "最短路问题":   lambda: ShortestPathPage(self, self),
            "最小支撑树":   lambda: MSTPage(self, self),
            "移动平均法":   lambda: ForecastPage(self, self, "移动平均法"),
            "指数平滑法":   lambda: ForecastPage(self, self, "指数平滑法"),
            "回归分析法":   lambda: ForecastPage(self, self, "回归分析法"),
            "合理排班问题": lambda: SchedulingPage(self, self),
        }
        if name in pages:
            self._show(pages[name]())
        else:
            messagebox.showinfo("提示", f"【{name}】功能正在开发中...")

    def quit_app(self) -> None:
        if messagebox.askyesno("退出", "确认退出系统？"):
            self.destroy()
