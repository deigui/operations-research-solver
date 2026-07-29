"""应用主控制器（App 窗口）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from or_solver.constants import BG_DARK
from or_solver.ui.pages.home import HomePage
from or_solver.ui.pages.menu import MenuPage
from or_solver.ui.pages.lp import LPPage
from or_solver.ui.pages.transport import TransportPage
from or_solver.ui.pages.decision import DecisionPage
from or_solver.ui.pages.network import ShortestPathPage
from or_solver.ui.pages.mst import MSTPage
from or_solver.ui.pages.network_flow import NetworkFlowPage
from or_solver.ui.pages.priority_goal import PriorityGoalPage
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
        self._tabs: dict[str, tk.Widget] = {}
        self._closable_tabs: set[str] = set()
        self._pulldown_menus: list[tk.Menu] = []
        self._build_menubar()
        self._build_notebook()
        self.show_home()

    # ── 页面切换 ─────────────────────────────────────────
    def _build_notebook(self) -> None:
        style = ttk.Style(self)
        style.layout("Tabless.TNotebook.Tab", [])
        style.configure("Tabless.TNotebook", tabmargins=0, borderwidth=0)
        self.tab_strip = tk.Frame(self, bg="#eeeeee", height=26)
        self.tab_strip.pack(fill="x", side="top")
        self.tab_strip.pack_propagate(False)
        self.notebook = ttk.Notebook(self, style="Tabless.TNotebook")
        self.notebook.pack(fill="both", expand=True)
        self.tab_menu = tk.Menu(self, tearoff=0)
        self.tab_menu.add_command(label="关闭", command=self._close_context_tab)
        self.tab_menu.add_command(label="关闭所有标签页", command=self._close_all_tabs)
        self.tab_menu.add_command(label="关闭其他标签页", command=self._close_other_tabs)
        self.tab_menu.add_separator()
        self.tab_menu.add_command(label="关闭左侧标签页", command=self._close_left_tabs)
        self.tab_menu.add_command(label="关闭右侧标签页", command=self._close_right_tabs)
        self._context_tab_title: str | None = None

    def _build_menubar(self) -> None:
        top_menu_font = ("微软雅黑", 12, "bold")
        submenu_font = ("微软雅黑", 10)
        self.option_add("*Menu.font", submenu_font)
        bar = tk.Frame(self, bg="#ffffff", height=36)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        self._menu_bar = bar

        self._add_menu_button(bar, "主页", self.show_home, top_menu_font)

        for category, items in MenuPage.MENU.items():
            submenu = tk.Menu(bar, tearoff=0, font=submenu_font)
            for item in items:
                state = "normal" if item in MenuPage.IMPLEMENTED else "disabled"
                submenu.add_command(
                    label=item,
                    command=lambda name=item: self.open_solver(name),
                    font=submenu_font,
                    state=state,
                )
            self._pulldown_menus.append(submenu)
            mb = tk.Button(
                bar,
                text=category,
                font=top_menu_font,
                bg="#ffffff",
                fg="#111111",
                activebackground="#e8f3f7",
                activeforeground="#000000",
                relief="flat",
                padx=14,
                pady=4,
                cursor="hand2",
            )
            mb.configure(command=lambda m=submenu, b=mb: self._show_top_menu(m, b))
            mb.pack(side="left", fill="y")

        self._add_menu_button(bar, "退出系统", self.quit_app, top_menu_font)

    def _add_menu_button(self, parent: tk.Widget, text: str, command, font) -> None:
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=font,
            bg="#ffffff",
            fg="#111111",
            activebackground="#e8f3f7",
            activeforeground="#000000",
            relief="flat",
            bd=0,
            padx=14,
            pady=4,
            cursor="hand2",
        )
        btn.pack(side="left", fill="y")

    def _show_top_menu(self, menu: tk.Menu, button: tk.Widget) -> None:
        try:
            menu.tk_popup(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())
        finally:
            menu.grab_release()

    def _open_tab(self, title: str, factory, closable: bool = True) -> None:
        existing = self._tabs.get(title)
        if existing is not None and existing.winfo_exists():
            self.notebook.select(existing)
            self._refresh_tab_strip()
            return

        frame = factory()
        self._tabs[title] = frame
        if closable:
            self._closable_tabs.add(title)
        self.notebook.add(frame, text=title)
        self.notebook.select(frame)
        self._refresh_tab_strip()

    def _title_for_index(self, index: int) -> str:
        return str(self.notebook.tab(index, "text"))

    def _tab_titles(self) -> list[str]:
        titles = []
        for tab_id in self.notebook.tabs():
            titles.append(str(self.notebook.tab(tab_id, "text")))
        return titles

    def _refresh_tab_strip(self) -> None:
        for child in self.tab_strip.winfo_children():
            child.destroy()

        current = self._current_tab_title()
        for title in self._tab_titles():
            selected = title == current
            bg = "#ffffff" if selected else "#eeeeee"
            border = "#c8c8c8" if selected else "#dddddd"
            tab = tk.Frame(self.tab_strip, bg=bg, highlightthickness=1, highlightbackground=border)
            tab.pack(side="left", fill="y", padx=(0, 0), pady=(0, 0))
            label = tk.Label(
                tab,
                text=title,
                font=("微软雅黑", 10),
                bg=bg,
                fg="#111111",
                padx=8,
                pady=2,
                cursor="hand2",
            )
            label.pack(side="left", fill="y")
            label.bind("<Button-1>", lambda _event, t=title: self._select_tab(t))
            tab.bind("<Button-1>", lambda _event, t=title: self._select_tab(t))
            for widget in (tab, label):
                widget.bind("<Button-3>", lambda event, t=title: self._show_tab_menu(event, t))
            if title in self._closable_tabs:
                close_btn = tk.Button(
                    tab,
                    text="×",
                    command=lambda t=title: self._close_tab(t),
                    font=("Arial", 10, "bold"),
                    bg=bg,
                    fg="#333333",
                    activebackground="#f2dede",
                    activeforeground="#a00000",
                    relief="flat",
                    bd=0,
                    padx=3,
                    pady=0,
                    cursor="hand2",
                )
                close_btn.pack(side="left", fill="y", padx=(0, 2))
                close_btn.bind("<Button-3>", lambda event, t=title: self._show_tab_menu(event, t))

    def _current_tab_title(self) -> str | None:
        try:
            return str(self.notebook.tab(self.notebook.select(), "text"))
        except tk.TclError:
            return None

    def _select_tab(self, title: str) -> None:
        frame = self._tabs.get(title)
        if frame is not None and frame.winfo_exists():
            self.notebook.select(frame)
            self._refresh_tab_strip()

    def _show_tab_menu(self, event, title: str) -> None:
        self._context_tab_title = title
        is_closable = title in self._closable_tabs
        self.tab_menu.entryconfig("关闭", state="normal" if is_closable else "disabled")
        self.tab_menu.tk_popup(event.x_root, event.y_root)

    def _close_tab(self, title: str) -> None:
        if title not in self._closable_tabs:
            return
        frame = self._tabs.pop(title, None)
        self._closable_tabs.discard(title)
        if frame is not None and frame.winfo_exists():
            self.notebook.forget(frame)
            frame.destroy()
        self._refresh_tab_strip()

    def _close_tabs(self, titles: list[str]) -> None:
        for title in titles:
            self._close_tab(title)

    def _close_context_tab(self) -> None:
        if self._context_tab_title:
            self._close_tab(self._context_tab_title)

    def _close_all_tabs(self) -> None:
        self._close_tabs(self._tab_titles())
        self.show_home()

    def _close_other_tabs(self) -> None:
        current = self._context_tab_title
        if current is None:
            return
        self._close_tabs([title for title in self._tab_titles() if title != current])
        if current in self._tabs:
            self.notebook.select(self._tabs[current])
            self._refresh_tab_strip()
        else:
            self.show_home()

    def _close_left_tabs(self) -> None:
        current = self._context_tab_title
        if current is None:
            return
        titles = self._tab_titles()
        try:
            current_index = titles.index(current)
        except ValueError:
            return
        self._close_tabs(titles[:current_index])
        self._refresh_tab_strip()

    def _close_right_tabs(self) -> None:
        current = self._context_tab_title
        if current is None:
            return
        titles = self._tab_titles()
        try:
            current_index = titles.index(current)
        except ValueError:
            return
        self._close_tabs(titles[current_index + 1:])
        self._refresh_tab_strip()

    def show_home(self) -> None:
        self._open_tab("我的主页", lambda: HomePage(self.notebook, self), closable=False)

    def show_menu(self, category: str | None = None) -> None:
        title = "功能菜单" if category is None else f"功能菜单 - {category}"
        self._open_tab(
            title,
            lambda: MenuPage(self.notebook, self, initial_category=category),
            closable=True,
        )

    def _solver_page(self, name: str, master: tk.Widget | None = None, controller=None):
        master = master or self
        controller = controller or self
        pages = {
            "线性规划问题": lambda: LPPage(master, controller, "线性规划问题"),
            "表格式线性规划": lambda: LPPage(master, controller, "表格式线性规划"),
            "纯整数规划":   lambda: LPPage(master, controller, "纯整数规划", integer_vars=True),
            "0-1整数规划":  lambda: LPPage(master, controller, "0-1整数规划", binary_vars=True),
            "混合整数规划": lambda: LPPage(master, controller, "混合整数规划", integer_vars=[]),
            "连续投资问题": lambda: LPPage(master, controller, "连续投资问题"),
            "产品自制与外协": lambda: LPPage(master, controller, "产品自制与外协"),
            "生产安排问题": lambda: LPPage(master, controller, "生产安排问题"),
            "已穷举套材下料": lambda: LPPage(master, controller, "已穷举套材下料", integer_vars=True),
            "待穷举套材下料": lambda: LPPage(master, controller, "待穷举套材下料", integer_vars=True),
            "灰色线性规划": lambda: LPPage(master, controller, "灰色线性规划"),
            "投资与选址": lambda: LPPage(master, controller, "投资与选址", integer_vars=[]),
            "整数连续投资": lambda: LPPage(master, controller, "整数连续投资", integer_vars=[]),
            "产销平衡问题": lambda: TransportPage(master, controller, "平衡"),
            "产大于销问题": lambda: TransportPage(master, controller, "产大于销"),
            "销大于产问题": lambda: TransportPage(master, controller, "销大于产"),
            "指派问题":     lambda: TransportPage(master, controller, "指派"),
            "最大最小准则": lambda: DecisionPage(master, controller, "最大最小准则"),
            "最大最大准则": lambda: DecisionPage(master, controller, "最大最大准则"),
            "后悔值准则":   lambda: DecisionPage(master, controller, "后悔值准则"),
            "期望值准则":   lambda: DecisionPage(master, controller, "期望值准则"),
            "乐观系数准则": lambda: DecisionPage(master, controller, "乐观系数准则"),
            "等可能性准则": lambda: DecisionPage(master, controller, "等可能性准则"),
            "全情报准则": lambda: DecisionPage(master, controller, "全情报准则"),
            "部分情报准则": lambda: DecisionPage(master, controller, "部分情报准则"),
            "效用值准则": lambda: DecisionPage(master, controller, "效用值准则"),
            "优先级目标": lambda: PriorityGoalPage(master, controller),
            "加权目标规划": lambda: LPPage(master, controller, "加权目标规划"),
            "最短路问题":   lambda: ShortestPathPage(master, controller),
            "最小支撑树":   lambda: MSTPage(master, controller),
            "最大流问题":   lambda: NetworkFlowPage(master, controller, "最大流问题"),
            "最小费用流":   lambda: NetworkFlowPage(master, controller, "最小费用流"),
            "最小费最大流": lambda: NetworkFlowPage(master, controller, "最小费最大流"),
            "循环最短路":   lambda: NetworkFlowPage(master, controller, "循环最短路"),
            "移动平均法":   lambda: ForecastPage(master, controller, "移动平均法"),
            "指数平滑法":   lambda: ForecastPage(master, controller, "指数平滑法"),
            "加权移动平均": lambda: ForecastPage(master, controller, "加权移动平均"),
            "趋势投影法":   lambda: ForecastPage(master, controller, "趋势投影法"),
            "趋势季节因素": lambda: ForecastPage(master, controller, "趋势季节因素"),
            "回归分析法":   lambda: ForecastPage(master, controller, "回归分析法"),
            "合理排班问题": lambda: SchedulingPage(master, controller),
        }
        return pages.get(name)

    def open_solver(self, name: str) -> None:
        if name not in MenuPage.IMPLEMENTED:
            messagebox.showinfo("Info", name + " is not implemented yet.")
            return
        page_factory = self._solver_page(name, self.notebook, self)
        if page_factory:
            self._open_tab(name, page_factory, closable=True)
        else:
            messagebox.showinfo("Info", name + " is not implemented yet.")

    def open_solver_window(self, name: str) -> None:
        self.open_solver(name)

    def quit_app(self) -> None:
        if messagebox.askyesno("退出", "确认退出系统？"):
            self.destroy()
