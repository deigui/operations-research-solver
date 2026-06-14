"""主页（欢迎页）。"""
from __future__ import annotations

import tkinter as tk

from or_solver.__version__ import __version__


class HomePage(tk.Frame):
    OUTER_BG  = "#eeece8"
    PAPER_BG  = "#fbf8f1"
    HERO_BG   = "#124a61"
    HERO_LINE = "#6b93a3"
    HERO_SOFT = "#cad6dc"
    GOLD      = "#d9a43a"
    TITLE_RED = "#e33328"
    TEXT_LIGHT = "#d7dde0"
    TEXT_MUTED = "#75909d"
    QUOTE_BG  = "#f1e5d1"
    TAB_BG    = "#1f6a80"
    TAB_DOT   = "#5b8796"
    BORDER    = "#bfb6a9"
    BODY_TEXT = "#1c2328"

    def __init__(self, master: tk.Widget, controller):
        super().__init__(master, bg=self.OUTER_BG)
        self.controller = controller
        self._build()

    def _build(self):
        self.config(bg=self.OUTER_BG)
        shell = tk.Frame(self, bg=self.PAPER_BG)
        shell.pack(fill="both", expand=True)

        hero = tk.Frame(shell, bg=self.HERO_BG, height=250)
        hero.pack(fill="x")
        hero.pack_propagate(False)

        hero_inner = tk.Frame(hero, bg=self.HERO_BG)
        hero_inner.pack(fill="both", expand=True, padx=22, pady=(12, 0))

        meta = tk.Frame(hero_inner, bg=self.HERO_BG)
        meta.pack(fill="x")
        meta_left = tk.Frame(meta, bg=self.HERO_BG)
        meta_left.pack(side="left")
        for idx, item in enumerate(("运筹学", "数据·模型·决策", "管理决策工具")):
            fg = self.TEXT_LIGHT if idx != 2 else self.HERO_SOFT
            tk.Label(meta_left, text=item, font=("微软雅黑", 10, "bold"),
                     bg=self.HERO_BG, fg=fg).pack(side="left", padx=(0, 26))
        self._create_badge(meta).pack(side="right")

        hero_main = tk.Frame(hero_inner, bg=self.HERO_BG)
        hero_main.pack(fill="both", expand=True, pady=(30, 0))
        hero_main.grid_columnconfigure(0, weight=1)
        hero_main.grid_columnconfigure(1, weight=0)

        title_box = tk.Frame(hero_main, bg=self.HERO_BG)
        title_box.grid(row=0, column=0, sticky="nsew")

        title_row = tk.Frame(title_box, bg=self.HERO_BG)
        title_row.pack(anchor="center", pady=(52, 0))
        tk.Label(title_row, text="运筹帷幄", font=("微软雅黑", 33, "bold"),
                 bg=self.HERO_BG, fg=self.TITLE_RED).pack(side="left")
        tk.Label(title_row, text=" · ", font=("微软雅黑", 33, "bold"),
                 bg=self.HERO_BG, fg=self.GOLD).pack(side="left")
        tk.Label(title_row, text="决胜千里", font=("微软雅黑", 33, "bold"),
                 bg=self.HERO_BG, fg=self.TITLE_RED).pack(side="left")

        tk.Label(title_box,
                 text="Operations Research · Mathematical Modeling Tool",
                 font=("Georgia", 10, "italic"),
                 bg=self.HERO_BG, fg=self.TEXT_MUTED).pack(anchor="center", pady=(2, 0))
        tk.Frame(title_box, bg=self.GOLD, height=3, width=260).pack(anchor="center", pady=(14, 0))

        self._draw_hero_art(hero_main).grid(row=0, column=1, sticky="se", padx=(20, 14), pady=(28, 12))

        tk.Frame(shell, bg=self.GOLD, height=6).pack(fill="x")

        quote = tk.Frame(shell, bg=self.QUOTE_BG, height=76)
        quote.pack(fill="x")
        quote.pack_propagate(False)
        quote_inner = tk.Frame(quote, bg=self.QUOTE_BG)
        quote_inner.pack(expand=True, pady=10)
        for parts in [
            [("正常情况下超常发挥是 ", self.BODY_TEXT), ("优秀", self.TITLE_RED),
             ("，靠的是 ", self.BODY_TEXT), ("计划工作", self.TAB_BG)],
            [("超常情况下正常发挥是 ", self.BODY_TEXT), ("卓越", self.TITLE_RED),
             ("，靠的是 ", self.BODY_TEXT), ("工作计划", self.TAB_BG)],
        ]:
            row = tk.Frame(quote_inner, bg=self.QUOTE_BG)
            row.pack(anchor="center", pady=2)
            for txt, color in parts:
                tk.Label(row, text=txt, font=("微软雅黑", 12, "bold"),
                         bg=self.QUOTE_BG, fg=color).pack(side="left")

        tabbar = tk.Frame(shell, bg=self.TAB_BG, height=64)
        tabbar.pack(fill="x")
        tabbar.pack_propagate(False)
        self._draw_concept_bar(tabbar).pack(fill="both", expand=True)

        content = tk.Frame(shell, bg=self.PAPER_BG, height=245)
        content.pack(fill="both", expand=True)
        content.pack_propagate(False)

        button_zone = tk.Frame(content, bg=self.PAPER_BG)
        button_zone.place(relx=0.5, rely=0.38, anchor="center")
        for col in range(3):
            button_zone.grid_columnconfigure(col, minsize=176)

        actions = [
            ("求解程序", "全傻瓜式操作", self.controller.show_menu, "#2f7d56"),
            ("Excel原表", "全手工式操作", self._excel_tip, "#1d5f83"),
            ("退出系统", "", self.controller.quit_app, "#7b7b7b"),
        ]
        for idx, (title, subtitle, cmd, accent) in enumerate(actions):
            self._create_action_card(button_zone, title, subtitle, cmd, accent).grid(
                row=0, column=idx, padx=10, sticky="nsew"
            )

        footer = tk.Frame(shell, bg="#e4d7bf", height=34)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(
            footer,
            text="案例内容来源:管理学院-宗胜亮 教授  |  开发团队：@",
            font=("微软雅黑", 9), bg="#e4d7bf", fg="#8b6e4f",
        ).pack(side="left", expand=True)
        tk.Label(
            footer, text=f"v{__version__}",
            font=("Consolas", 9), bg="#e4d7bf", fg="#a08060",
        ).pack(side="right", padx=10)

    def _create_badge(self, parent):
        badge = tk.Canvas(parent, width=54, height=54, bg=self.HERO_BG, highlightthickness=0)
        badge.create_oval(4, 4, 50, 50, outline=self.GOLD, width=1)
        badge.create_text(27, 20, text="兰州", fill=self.GOLD, font=("微软雅黑", 9, "bold"))
        badge.create_text(27, 33, text="大学", fill=self.GOLD, font=("微软雅黑", 9, "bold"))
        return badge

    def _draw_hero_art(self, parent):
        art = tk.Canvas(parent, width=240, height=118, bg=self.HERO_BG, highlightthickness=0)
        art.create_line(24, 86, 46, 48, 62, 64, 76, 32, 94, 60, 112, 58,
                        136, 78, 156, 58, 174, 64, smooth=True, fill=self.HERO_LINE, width=2)
        art.create_line(18, 88, 58, 82, 86, 80, 124, 85, 166, 84,
                        fill=self.HERO_LINE, width=1, dash=(3, 4))
        art.create_arc(126, 18, 142, 30, start=10, extent=130,
                       style="arc", outline=self.HERO_LINE, width=1)
        for x, y in ((142, 36), (156, 28), (170, 22), (178, 26), (190, 18)):
            art.create_arc(x, y, x + 10, y + 6, start=0, extent=130,
                           style="arc", outline=self.HERO_LINE, width=1)
        art.create_oval(44, 92, 84, 98, outline=self.HERO_LINE, width=1)
        return art

    def _draw_concept_bar(self, parent):
        canvas = tk.Canvas(parent, bg=self.TAB_BG, height=64, highlightthickness=0)

        def redraw(_event=None):
            canvas.delete("all")
            width = canvas.winfo_width()
            if width <= 1:
                return
            center = width // 2
            y = 32
            canvas.create_text(center - 170, y, text="《数据、模型与决策》",
                               fill="#f5f1e6", font=("微软雅黑", 19, "bold"))
            canvas.create_text(center + 230, y, text="《运筹学》",
                               fill="#f5f1e6", font=("微软雅黑", 19, "bold"))
            canvas.create_text(center + 25, y, text="⇔",
                               fill=self.GOLD, font=("微软雅黑", 28, "bold"))
            for offset, radius in [(-235, 26), (-152, 28), (-64, 28)]:
                x = center + offset
                canvas.create_oval(x - radius, y - 23, x + radius, y + 23,
                                   outline=self.GOLD, width=2, dash=(3, 3))

        canvas.bind("<Configure>", redraw)
        return canvas

    def _create_action_card(self, parent, title, subtitle, command, accent):
        outer = tk.Frame(parent, bg=self.PAPER_BG, width=160, height=60)
        outer.pack_propagate(False)
        shadow = tk.Frame(outer, bg=accent, height=2)
        shadow.pack(fill="x", side="bottom")
        card = tk.Frame(outer, bg="#fffdf8", highlightthickness=1,
                        highlightbackground=self.BORDER, bd=0, cursor="hand2")
        card.pack(fill="both", expand=True)
        inner = tk.Frame(card, bg="#fffdf8")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        title_label = tk.Label(inner, text=title, font=("微软雅黑", 11, "bold"),
                               bg="#fffdf8", fg="#171717", cursor="hand2")
        title_label.pack()
        subtitle_label = tk.Label(inner, text=subtitle, font=("微软雅黑", 8),
                                  bg="#fffdf8",
                                  fg="#ddd7cb" if subtitle else "#fffdf8",
                                  cursor="hand2")
        subtitle_label.pack(pady=(2, 0))

        def set_style(bg, border, title_fg, sub_fg):
            card.configure(bg=bg, highlightbackground=border)
            inner.configure(bg=bg)
            title_label.configure(bg=bg, fg=title_fg)
            subtitle_label.configure(bg=bg, fg=sub_fg)

        def on_enter(_e):
            set_style("#ffffff", accent, "#102f3b", "#bdb4a8" if subtitle else "#ffffff")

        def on_leave(_e):
            set_style("#fffdf8", self.BORDER, "#171717", "#ddd7cb" if subtitle else "#fffdf8")

        for widget in (outer, card, inner, title_label, subtitle_label):
            widget.bind("<Button-1>", lambda _e: command())
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        return outer

    def _excel_tip(self):
        from tkinter import messagebox
        messagebox.showinfo("提示", "请直接用Excel打开模板库中的对应模板文件手工操作。")
