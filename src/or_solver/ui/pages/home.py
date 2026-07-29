"""主页（欢迎页）。"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from or_solver.__version__ import __version__
from or_solver.ui.pages.menu import MenuPage


class HomePage(tk.Frame):
    OUTER_BG = "#eeece8"
    PAPER_BG = "#fbf8f1"
    HERO_BG = "#124a61"
    HERO_LINE = "#6b93a3"
    HERO_SOFT = "#cad6dc"
    GOLD = "#d9a43a"
    TITLE_RED = "#e33328"
    TEXT_LIGHT = "#d7dde0"
    TEXT_MUTED = "#75909d"
    QUOTE_BG = "#f1e5d1"
    TAB_BG = "#1f6a80"
    BORDER = "#bfb6a9"
    BODY_TEXT = "#1c2328"

    def __init__(self, master: tk.Widget, controller):
        super().__init__(master, bg=self.OUTER_BG)
        self.controller = controller
        self._build()

    def _build(self):
        self.config(bg=self.OUTER_BG)
        shell = tk.Frame(self, bg=self.PAPER_BG)
        shell.pack(fill="both", expand=True)

        hero = tk.Frame(shell, bg=self.HERO_BG, height=180)
        hero.pack(fill="x")
        hero.pack_propagate(False)

        hero_inner = tk.Frame(hero, bg=self.HERO_BG)
        hero_inner.pack(fill="both", expand=True, padx=22, pady=(8, 0))

        meta = tk.Frame(hero_inner, bg=self.HERO_BG)
        meta.pack(fill="x")
        meta_left = tk.Frame(meta, bg=self.HERO_BG)
        meta_left.pack(side="left")
        for idx, item in enumerate(("运筹学", "数据·模型·决策", "管理决策工具")):
            fg = self.TEXT_LIGHT if idx != 2 else self.HERO_SOFT
            tk.Label(
                meta_left,
                text=item,
                font=("微软雅黑", 10, "bold"),
                bg=self.HERO_BG,
                fg=fg,
            ).pack(side="left", padx=(0, 26))
        self._create_badge(meta).pack(side="right")

        hero_main = tk.Frame(hero_inner, bg=self.HERO_BG)
        hero_main.pack(fill="both", expand=True, pady=(6, 0))
        hero_main.grid_columnconfigure(0, weight=1)
        hero_main.grid_columnconfigure(1, weight=0)

        title_box = tk.Frame(hero_main, bg=self.HERO_BG)
        title_box.grid(row=0, column=0, sticky="nsew")

        title_row = tk.Frame(title_box, bg=self.HERO_BG)
        title_row.pack(anchor="center", pady=(25, 0))
        tk.Label(
            title_row,
            text="运筹帷幄",
            font=("微软雅黑", 30, "bold"),
            bg=self.HERO_BG,
            fg=self.TITLE_RED,
        ).pack(side="left")
        tk.Label(
            title_row,
            text=" · ",
            font=("微软雅黑", 30, "bold"),
            bg=self.HERO_BG,
            fg=self.GOLD,
        ).pack(side="left")
        tk.Label(
            title_row,
            text="决胜千里",
            font=("微软雅黑", 30, "bold"),
            bg=self.HERO_BG,
            fg=self.TITLE_RED,
        ).pack(side="left")

        tk.Label(
            title_box,
            text="Operations Research · Mathematical Modeling Tool",
            font=("Georgia", 10, "italic"),
            bg=self.HERO_BG,
            fg=self.TEXT_MUTED,
        ).pack(anchor="center", pady=(2, 0))
        tk.Frame(title_box, bg=self.GOLD, height=3, width=240).pack(anchor="center", pady=(8, 0))

        self._draw_hero_art(hero_main).grid(row=0, column=1, sticky="se", padx=(20, 14), pady=(20, 8))

        tk.Frame(shell, bg=self.GOLD, height=6).pack(fill="x")

        quote = tk.Frame(shell, bg=self.QUOTE_BG, height=58)
        quote.pack(fill="x")
        quote.pack_propagate(False)
        quote_inner = tk.Frame(quote, bg=self.QUOTE_BG)
        quote_inner.pack(expand=True, pady=4)
        for parts in [
            [
                ("正常情况下超常发挥是 ", self.BODY_TEXT),
                ("优秀", self.TITLE_RED),
                ("，靠的是 ", self.BODY_TEXT),
                ("计划工作", self.TAB_BG),
            ],
            [
                ("超常情况下正常发挥是 ", self.BODY_TEXT),
                ("卓越", self.TITLE_RED),
                ("，靠的是 ", self.BODY_TEXT),
                ("工作计划", self.TAB_BG),
            ],
        ]:
            row = tk.Frame(quote_inner, bg=self.QUOTE_BG)
            row.pack(anchor="center", pady=2)
            for txt, color in parts:
                tk.Label(row, text=txt, font=("微软雅黑", 11, "bold"), bg=self.QUOTE_BG, fg=color).pack(side="left")

        tabbar = tk.Frame(shell, bg=self.TAB_BG, height=48)
        tabbar.pack(fill="x")
        tabbar.pack_propagate(False)
        self._draw_concept_bar(tabbar).pack(fill="both", expand=True)

        footer = tk.Frame(shell, bg="#e4d7bf", height=34)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(
            footer,
            text="管理学院-宗胜亮 教授",
            font=("微软雅黑", 9),
            bg="#e4d7bf",
            fg="#8b6e4f",
        ).pack(side="left", expand=True)
        tk.Label(
            footer,
            text=f"v{__version__}",
            font=("Consolas", 9),
            bg="#e4d7bf",
            fg="#a08060",
        ).pack(side="right", padx=10)

        content = tk.Frame(shell, bg=self.PAPER_BG)
        content.pack(fill="both", expand=True)
        self._build_dashboard(content)

    def _create_badge(self, parent):
        badge = tk.Canvas(parent, width=54, height=54, bg=self.HERO_BG, highlightthickness=0)
        badge.create_oval(4, 4, 50, 50, outline=self.GOLD, width=1)
        badge.create_text(27, 20, text="兰州", fill=self.GOLD, font=("微软雅黑", 9, "bold"))
        badge.create_text(27, 33, text="大学", fill=self.GOLD, font=("微软雅黑", 9, "bold"))
        return badge

    def _draw_hero_art(self, parent):
        art = tk.Canvas(parent, width=240, height=118, bg=self.HERO_BG, highlightthickness=0)
        art.create_line(
            24,
            86,
            46,
            48,
            62,
            64,
            76,
            32,
            94,
            60,
            112,
            58,
            136,
            78,
            156,
            58,
            174,
            64,
            smooth=True,
            fill=self.HERO_LINE,
            width=2,
        )
        art.create_line(18, 88, 58, 82, 86, 80, 124, 85, 166, 84, fill=self.HERO_LINE, width=1, dash=(3, 4))
        art.create_arc(126, 18, 142, 30, start=10, extent=130, style="arc", outline=self.HERO_LINE, width=1)
        for x, y in ((142, 36), (156, 28), (170, 22), (178, 26), (190, 18)):
            art.create_arc(x, y, x + 10, y + 6, start=0, extent=130, style="arc", outline=self.HERO_LINE, width=1)
        art.create_oval(44, 92, 84, 98, outline=self.HERO_LINE, width=1)
        return art

    def _draw_concept_bar(self, parent):
        canvas = tk.Canvas(parent, bg=self.TAB_BG, height=48, highlightthickness=0)

        def redraw(_event=None):
            canvas.delete("all")
            width = canvas.winfo_width()
            if width <= 1:
                return
            center = width // 2
            y = 24
            canvas.create_text(
                center - 170,
                y,
                text="《数据、模型与决策》",
                fill="#f5f1e6",
                font=("微软雅黑", 17, "bold"),
            )
            canvas.create_text(
                center + 230,
                y,
                text="《运筹学》",
                fill="#f5f1e6",
                font=("微软雅黑", 17, "bold"),
            )
            canvas.create_text(center + 25, y, text="⇔", fill=self.GOLD, font=("微软雅黑", 24, "bold"))
            for offset, radius in [(-235, 26), (-152, 28), (-64, 28)]:
                x = center + offset
                canvas.create_oval(x - radius, y - 19, x + radius, y + 19, outline=self.GOLD, width=2, dash=(3, 3))

        canvas.bind("<Configure>", redraw)
        return canvas

    def _build_dashboard(self, parent):
        wrap = tk.Frame(parent, bg=self.PAPER_BG)
        wrap.pack(fill="both", expand=True, padx=48, pady=6)

        category_grid = tk.Frame(wrap, bg=self.PAPER_BG)
        category_grid.pack(fill="both", expand=True)
        descriptions = {
            "决策分析": "不确定与风险决策",
            "线性规划": "资源配置与生产计划",
            "整数规划": "离散选择与组合优化",
            "运输问题": "调运分配与任务指派",
            "目标规划": "多目标权衡",
            "网络优化": "图与网络结构优化",
            "预测问题": "历史数据预测",
        }
        categories = list(MenuPage.MENU.items())
        for idx, (title, items) in enumerate(categories):
            color = MenuPage.COL_COLORS.get(title, self.GOLD)
            card = self._info_card(category_grid, title, descriptions.get(title, ""), items, color)
            card.grid(row=idx, column=0, padx=8, pady=2, sticky="nsew")
        category_grid.grid_columnconfigure(0, weight=1)
        for row in range(len(categories)):
            category_grid.grid_rowconfigure(row, weight=1, minsize=50)

    def _info_card(self, parent, title, desc, items, color):
        card = tk.Frame(parent, bg="#fffdf8", height=50, highlightthickness=1, highlightbackground=self.BORDER)
        card.grid_propagate(False)
        tk.Frame(card, bg=color, width=5).pack(side="left", fill="y")
        body = tk.Frame(card, bg="#fffdf8")
        body.pack(side="left", fill="both", expand=True, padx=18, pady=0)

        left = tk.Frame(body, bg="#fffdf8", width=260)
        left.pack(side="left", fill="y", padx=(0, 22))
        left.pack_propagate(False)
        title_label = tk.Label(
            left,
            text=title,
            font=("微软雅黑", 12, "bold"),
            bg="#fffdf8",
            fg="#142f3a",
            anchor="w",
        )
        title_label.place(relx=0, rely=0.5, anchor="w")

        right = tk.Frame(body, bg="#fffdf8")
        right.pack(side="left", fill="both", expand=True)
        menu_label = tk.Label(
            right,
            text="、".join(items),
            font=("微软雅黑", 9),
            bg="#fffdf8",
            fg="#4f4a43",
            justify="left",
            anchor="w",
            wraplength=1350,
        )
        menu_label.place(relx=0, rely=0.5, relwidth=1, anchor="w")

        def on_enter(_event=None):
            card.configure(highlightbackground=color)
            body.configure(bg="#ffffff")
            left.configure(bg="#ffffff")
            right.configure(bg="#ffffff")
            title_label.configure(bg="#ffffff")
            menu_label.configure(bg="#ffffff")

        def on_leave(_event=None):
            card.configure(highlightbackground=self.BORDER)
            body.configure(bg="#fffdf8")
            left.configure(bg="#fffdf8")
            right.configure(bg="#fffdf8")
            title_label.configure(bg="#fffdf8")
            menu_label.configure(bg="#fffdf8")

        for widget in (card, body, left, right, title_label, menu_label):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        return card


if __name__ == "__main__":
    class _PreviewController:
        def show_home(self) -> None:
            pass

    root = tk.Tk()
    root.title("主页预览")
    root.geometry("1300x800")
    HomePage(root, _PreviewController()).pack(fill="both", expand=True)
    root.mainloop()
