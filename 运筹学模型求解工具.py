"""
运筹学模型求解工具
兰州大学管理学院 - Python复刻版
"""

__version__ = "0.1.0-alpha"

SUBS = "₁₂₃₄₅₆₇₈₉"  # x下标字符
def xname(j): return f"x{SUBS[j]}" if j < len(SUBS) else f"x{j+1}"

def _normalize_expr(s):
    """全角符号→ASCII，Unicode 下标→普通数字"""
    s = (s.replace("＝","=").replace("＋","+").replace("－","-")
          .replace("≥",">=").replace("≤","<=")
          .replace("＜＝","<=").replace("＞＝",">="))
    for sub, num in zip("₀₁₂₃₄₅₆₇₈₉", "0123456789"):
        s = s.replace(sub, num)
    return s

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os

# ── 颜色主题 ──────────────────────────────────────────
BG_DARK   = "#1a472a"   # 深绿背景
BG_MID    = "#2d6a3f"
BTN_PINK  = "#f48fb1"
BTN_GREEN = "#4caf50"
BTN_TEAL  = "#26a69a"
BTN_GRAY  = "#78909c"
FG_WHITE  = "#ffffff"
FG_GOLD   = "#ffd700"

FONT_TITLE  = ("微软雅黑", 22, "bold")
FONT_SUB    = ("微软雅黑", 13, "bold")
FONT_BTN    = ("微软雅黑", 11)
FONT_SMALL  = ("微软雅黑", 10)

# ── 工具函数 ──────────────────────────────────────────
def make_btn(parent, text, cmd, bg=BTN_GREEN, fg=FG_WHITE, width=14):
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg, fg=fg, font=FONT_BTN,
                     relief="raised", bd=2, width=width,
                     activebackground=bg, cursor="hand2")

# ══════════════════════════════════════════════════════
#  通用表格选区编辑混入
# ══════════════════════════════════════════════════════
class _TableEditMixin:
    """通用表格选区编辑混入：拖拽选区、Ctrl+C/X/V、Delete"""

    def _tbl_init_sel(self):
        self._sel_start = None
        self._sel_end   = None

    # ── 子类必须实现 ──────────────────────────────────────────
    def _entry_at(self, r, c):          return None
    def _entry_default_bg(self, r, c): return "#ffffff"
    def _all_entries(self):             return iter([])
    def _entry_frame(self):            return self.body

    # ── 选区操作 ──────────────────────────────────────────────
    def _sel_click(self, r, c, extend):
        if extend and self._sel_start:
            self._sel_end = (r, c)
        else:
            self._sel_start = (r, c)
            self._sel_end   = (r, c)
        self._highlight_sel()

    def _sel_drag(self, event):
        ax = event.widget.winfo_rootx() + event.x
        ay = event.widget.winfo_rooty() + event.y
        target = self._entry_frame().winfo_containing(ax, ay)
        if target is None:
            return
        for r, c, e in self._all_entries():
            if e is target:
                self._sel_end = (r, c)
                self._highlight_sel()
                return

    def _highlight_sel(self):
        for r, c, e in self._all_entries():
            e.config(bg=self._entry_default_bg(r, c))
        if not (self._sel_start and self._sel_end):
            return
        r1 = min(self._sel_start[0], self._sel_end[0])
        r2 = max(self._sel_start[0], self._sel_end[0])
        c1 = min(self._sel_start[1], self._sel_end[1])
        c2 = max(self._sel_start[1], self._sel_end[1])
        if r1 == r2 and c1 == c2:
            return
        SEL = "#b3d9ff"
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                e = self._entry_at(r, c)
                if e:
                    e.config(bg=SEL)

    def _cell_value_at(self, r, c):
        e = self._entry_at(r, c)
        return e.get() if e else ""

    def _copy_selected(self, event=None):
        if not (self._sel_start and self._sel_end):
            return None
        r1 = min(self._sel_start[0], self._sel_end[0])
        r2 = max(self._sel_start[0], self._sel_end[0])
        c1 = min(self._sel_start[1], self._sel_end[1])
        c2 = max(self._sel_start[1], self._sel_end[1])
        if r1 == r2 and c1 == c2:
            return None
        lines = []
        for r in range(r1, r2 + 1):
            lines.append("\t".join(self._cell_value_at(r, c) for c in range(c1, c2 + 1)))
        self._entry_frame().clipboard_clear()
        self._entry_frame().clipboard_append("\n".join(lines))
        return "break"

    def _cut_selected(self, event=None):
        result = self._copy_selected()
        if result != "break":
            return result
        self._delete_selected()
        return "break"

    def _delete_selected(self, event=None):
        if not (self._sel_start and self._sel_end):
            return None
        r1 = min(self._sel_start[0], self._sel_end[0])
        r2 = max(self._sel_start[0], self._sel_end[0])
        c1 = min(self._sel_start[1], self._sel_end[1])
        c2 = max(self._sel_start[1], self._sel_end[1])
        if r1 == r2 and c1 == c2:
            return None
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                e = self._entry_at(r, c)
                if e:
                    try: e.delete(0, "end")
                    except Exception: pass
        self._sel_start = self._sel_end = None
        self._highlight_sel()
        return "break"

    def _bind_cell(self, entry, r, c):
        """给一个 Entry 绑定选区快捷键"""
        entry.bind("<ButtonPress-1>",  lambda ev, r=r, c=c: self._sel_click(r, c, False))
        entry.bind("<Shift-Button-1>", lambda ev, r=r, c=c: self._sel_click(r, c, True) or "break")
        entry.bind("<B1-Motion>",      self._sel_drag)
        entry.bind("<Control-c>",      self._copy_selected)
        entry.bind("<Control-x>",      self._cut_selected)
        entry.bind("<Delete>",         self._delete_selected)


# ══════════════════════════════════════════════════════
#  首页
# ══════════════════════════════════════════════════════
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
    TAB_DOT = "#5b8796"
    BORDER = "#bfb6a9"
    BODY_TEXT = "#1c2328"

    def __init__(self, master, controller):
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
        for idx, item in enumerate(("兰州大学管理学院", "运筹学课程", "宗胜亮 教授")):
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
            [("正常情况下超常发挥是 ", self.BODY_TEXT), ("优秀", self.TITLE_RED), ("，靠的是 ", self.BODY_TEXT), ("计划工作", self.TAB_BG)],
            [("超常情况下正常发挥是 ", self.BODY_TEXT), ("卓越", self.TITLE_RED), ("，靠的是 ", self.BODY_TEXT), ("工作计划", self.TAB_BG)],
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
            text="课程内容及模型方法来源：兰州大学管理学院 宗胜亮 教授 | Python复刻：陈士成 苏云 何丽红 罗云中",
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

    def _create_badge(self, parent):
        badge = tk.Canvas(parent, width=54, height=54, bg=self.HERO_BG,
                          highlightthickness=0)
        badge.create_oval(4, 4, 50, 50, outline=self.GOLD, width=1)
        badge.create_text(27, 20, text="兰州", fill=self.GOLD,
                          font=("微软雅黑", 9, "bold"))
        badge.create_text(27, 33, text="大学", fill=self.GOLD,
                          font=("微软雅黑", 9, "bold"))
        return badge

    def _draw_hero_art(self, parent):
        art = tk.Canvas(parent, width=240, height=118, bg=self.HERO_BG,
                        highlightthickness=0)
        art.create_line(
            24, 86, 46, 48, 62, 64, 76, 32, 94, 60, 112, 58,
            136, 78, 156, 58, 174, 64,
            smooth=True, fill=self.HERO_LINE, width=2
        )
        art.create_line(
            18, 88, 58, 82, 86, 80, 124, 85, 166, 84,
            fill=self.HERO_LINE, width=1, dash=(3, 4)
        )
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

            blue = "#f5f1e6"
            orange = self.GOLD
            center = width // 2
            y = 32

            left_text = "《数据、模型与决策》"
            right_text = "《运筹学》"
            canvas.create_text(center - 170, y, text=left_text,
                               fill=blue, font=("微软雅黑", 19, "bold"))
            canvas.create_text(center + 230, y, text=right_text,
                               fill=blue, font=("微软雅黑", 19, "bold"))
            canvas.create_text(center + 25, y, text="⇔",
                               fill=orange, font=("微软雅黑", 28, "bold"))

            for offset, radius in [(-235, 26), (-152, 28), (-64, 28)]:
                x = center + offset
                canvas.create_oval(x - radius, y - 23, x + radius, y + 23,
                                   outline=orange, width=2, dash=(3, 3))

        canvas.bind("<Configure>", redraw)
        return canvas

    def _create_action_card(self, parent, title, subtitle, command, accent):
        outer = tk.Frame(parent, bg=self.PAPER_BG, width=160, height=60)
        outer.pack_propagate(False)

        shadow = tk.Frame(outer, bg=accent, height=2)
        shadow.pack(fill="x", side="bottom")

        card = tk.Frame(
            outer,
            bg="#fffdf8",
            highlightthickness=1,
            highlightbackground=self.BORDER,
            bd=0,
            cursor="hand2",
        )
        card.pack(fill="both", expand=True)

        inner = tk.Frame(card, bg="#fffdf8")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        title_label = tk.Label(
            inner,
            text=title,
            font=("微软雅黑", 11, "bold"),
            bg="#fffdf8",
            fg="#171717",
            cursor="hand2",
        )
        title_label.pack()

        subtitle_label = tk.Label(
            inner,
            text=subtitle,
            font=("微软雅黑", 8),
            bg="#fffdf8",
            fg="#ddd7cb" if subtitle else "#fffdf8",
            cursor="hand2",
        )
        subtitle_label.pack(pady=(2, 0))

        def set_card_style(bg, border, title_fg, sub_fg):
            card.configure(bg=bg, highlightbackground=border)
            inner.configure(bg=bg)
            title_label.configure(bg=bg, fg=title_fg)
            subtitle_label.configure(bg=bg, fg=sub_fg)

        def on_enter(_event):
            set_card_style("#ffffff", accent, "#102f3b", "#bdb4a8" if subtitle else "#ffffff")

        def on_leave(_event):
            set_card_style("#fffdf8", self.BORDER, "#171717", "#ddd7cb" if subtitle else "#fffdf8")

        def on_click(_event):
            command()

        for widget in (outer, card, inner, title_label, subtitle_label):
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        return outer

    def _excel_tip(self):
        messagebox.showinfo("提示", "请直接用Excel打开模板库中的对应模板文件手工操作。")


# ══════════════════════════════════════════════════════
#  功能菜单页
# ══════════════════════════════════════════════════════
class MenuPage(tk.Frame):
    MENU = {
        "决策分析": [
            "最大最小准则","最大最大准则","乐观系数准则",
            "等可能性准则","后悔值准则","期望值准则",
            "全情报准则","部分情报准则","效用值准则",
        ],
        "线性规划": [
            "线性规划问题","表格式线性规划","连续投资问题",
            "产品自制与外协","生产安排问题","合理排班问题",
            "已穷举套材下料","待穷举套材下料","灰色线性规划",
        ],
        "整数规划": [
            "纯整数规划","0-1整数规划","混合整数规划",
            "投资与选址","整数连续投资",
        ],
        "运输问题": [
            "产销平衡问题","产大于销问题","销大于产问题","指派问题",
        ],
        "目标规划": [
            "优先级目标","加权目标规划",
        ],
        "网络优化": [
            "最短路问题","最大流问题","最小费用流",
            "最小费最大流","最小支撑树","循环最短路",
        ],
        "预测问题": [
            "移动平均法","指数平滑法","加权移动平均",
            "趋势投影法","趋势季节因素","回归分析法",
        ],
    }

    # 哪些功能已实现
    IMPLEMENTED = {
        "线性规划问题", "纯整数规划", "0-1整数规划", "混合整数规划",
        "产销平衡问题", "产大于销问题", "销大于产问题", "指派问题",
        "最大最小准则", "最大最大准则", "后悔值准则", "期望值准则",
        "乐观系数准则", "等可能性准则",
        "最短路问题", "移动平均法", "指数平滑法", "回归分析法",
        "合理排班问题",
    }

    COL_COLORS = {
        "决策分析": BTN_PINK,
        "线性规划": "#ce93d8",
        "整数规划": "#80cbc4",
        "运输问题": "#80deea",
        "目标规划": "#a5d6a7",
        "网络优化": "#b0bec5",
        "预测问题": "#ffcc80",
    }

    def __init__(self, master, controller):
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
                btn = tk.Button(
                    grid, text=item, width=12, font=FONT_SMALL,
                    bg="#e8f5e9" if state == "normal" else "#dddddd",
                    fg="#222" if state == "normal" else "#888",
                    relief="groove", bd=1,
                    state=state,
                    cursor="hand2" if state == "normal" else "arrow",
                    command=lambda i=item: self.controller.open_solver(i)
                )
                btn.grid(row=row, column=col, padx=4, pady=2)

        # 底部按钮
        bot = tk.Frame(self, bg=BG_DARK)
        bot.pack(pady=14)
        make_btn(bot, "返回首页", self.controller.show_home, bg=BTN_PINK, fg="#333").pack(side="left", padx=20)


# ══════════════════════════════════════════════════════
#  线性规划求解页
# ══════════════════════════════════════════════════════
class LPPage(tk.Frame, _TableEditMixin):
    SUBS = "₁₂₃₄₅₆₇₈₉"  # Unicode下标字符

    def __init__(self, master, controller, title="线性规划问题",
                 integer_vars=None, binary_vars=False):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.title_text = title
        self.integer_vars = integer_vars   # None=连续, list=指定整数变量, True=全整数
        self.binary_vars  = binary_vars    # True=0-1整数
        self.n_vars = tk.IntVar(value=2)
        self.n_cons = tk.IntVar(value=2)
        self.obj_type = tk.StringVar(value="最大化")
        self.entries_built = False
        self._build_header()

    def _build_header(self):
        # ── 顶部控制栏（仿原工具紧凑布局）──
        hdr = tk.Frame(self, bg="#c8b89a", relief="raised", bd=1)
        hdr.pack(fill="x")

        # 标题居中
        tk.Label(hdr, text=f"运筹学模型求解系统———{self.title_text}",
                 font=("宋体", 13, "bold"), bg="#c8b89a", fg="#222").pack(pady=4)

        # 控制行
        ctrl = tk.Frame(hdr, bg="#c8b89a")
        ctrl.pack(pady=(0,4))
        tk.Label(ctrl, text="决策变量个数:", bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(8,0))
        tk.Spinbox(ctrl, from_=1, to=20, textvariable=self.n_vars, width=4,
                   font=FONT_SMALL, relief="sunken").pack(side="left", padx=2)
        tk.Label(ctrl, text="约束条件个数:", bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(12,0))
        tk.Spinbox(ctrl, from_=1, to=30, textvariable=self.n_cons, width=4,
                   font=FONT_SMALL, relief="sunken").pack(side="left", padx=2)
        tk.Radiobutton(ctrl, text="最大化", variable=self.obj_type, value="最大化",
                       bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(12,2))
        tk.Radiobutton(ctrl, text="最小化", variable=self.obj_type, value="最小化",
                       bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=2)
        tk.Button(ctrl, text="确  定", command=self._build_table,
                  bg="#dddddd", font=FONT_SMALL, width=7, relief="raised").pack(side="left", padx=8)
        tk.Button(ctrl, text="求  解", command=self._solve,
                  bg="#dddddd", font=FONT_SMALL, width=7, relief="raised").pack(side="left", padx=2)
        tk.Button(ctrl, text="返  回", command=self.controller.show_menu,
                  bg="#dddddd", font=FONT_SMALL, width=7, relief="raised").pack(side="left", padx=2)
        tk.Button(ctrl, text="存  盘", command=self._save,
                  bg="#dddddd", font=FONT_SMALL, width=7, relief="raised").pack(side="left", padx=2)
        tk.Button(ctrl, text="导  入", command=self._load,
                  bg="#dddddd", font=FONT_SMALL, width=7, relief="raised").pack(side="left", padx=2)
        tk.Button(ctrl, text="恢复历史", command=self._prompt_auto_load,
                  bg="#ffd700", font=FONT_SMALL, width=8, relief="raised").pack(side="left", padx=6)



        # ══════ 四象限布局（PanedWindow可拖动分隔）══════
        main_pane = tk.PanedWindow(self, orient="horizontal", bg="#888",
                                    sashwidth=5, sashrelief="raised",
                                    sashpad=2)
        main_pane.pack(fill="both", expand=True)

        # ── 左侧面板 ──
        left_pane = tk.Frame(main_pane, bg="#e8e0d0")
        main_pane.add(left_pane, minsize=400, width=750)

        # 左侧上下也用PanedWindow（可拖动）
        left_pw = tk.PanedWindow(left_pane, orient="vertical", bg="#888",
                                  sashwidth=5, sashrelief="raised", sashpad=2)
        left_pw.pack(fill="both", expand=True)

        # 左上：表达式输入区
        expr_input_frame = tk.Frame(left_pw, bg="#f5f0e0", relief="groove", bd=1)
        left_pw.add(expr_input_frame, minsize=80, height=220)
        top_row = tk.Frame(expr_input_frame, bg="#f5f0e0")
        top_row.pack(fill="x", padx=6, pady=(4,2))
        tk.Label(top_row, text="模型表达式（输入或粘贴）:",
                 bg="#f5f0e0", font=("宋体",9,"bold")).pack(side="left")
        tk.Button(top_row, text="解析填入表格",
                  command=self._expr_to_table,
                  bg="#90ee90", font=("宋体",9), relief="raised", width=12).pack(side="left", padx=6)
        tk.Button(top_row, text="从表格刷新",
                  command=self._table_to_expr,
                  bg="#87ceeb", font=("宋体",9), relief="raised", width=10).pack(side="left", padx=2)
        tk.Button(top_row, text="清  空",
                  command=lambda: self.main_expr_text.delete("1.0","end"),
                  bg="#ffcccc", font=("宋体",9), relief="raised", width=6).pack(side="left", padx=2)
        self.main_expr_text = tk.Text(expr_input_frame,
                                      font=("Consolas", 10), bg="#fffff0",
                                      relief="sunken", bd=1)
        self.main_expr_text.pack(fill="both", expand=True, padx=6, pady=(0,4))
        self.main_expr_text.insert("1.0",
            "max  Z = 15x1 + 10x2 + 7x3\ns.t.\n  5x1 + 10x2 + 7x3 <= 8000\n  x1 >= 0")

        # 左下：表格+结果区（带滚动）
        left_bottom = tk.Frame(left_pw, bg="#e8e0d0")
        left_pw.add(left_bottom, minsize=200)
        vsb = tk.Scrollbar(left_bottom, orient="vertical")
        hsb = tk.Scrollbar(left_bottom, orient="horizontal")
        canvas = tk.Canvas(left_bottom, bg="#e8e0d0", width=700,
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=canvas.yview)
        hsb.config(command=canvas.xview)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(canvas, bg="#e8e0d0")
        canvas.create_window((4, 4), window=self.body, anchor="nw")
        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self.body.bind("<Configure>", _on_configure)

        # ── 右侧面板 ──
        right_pane = tk.Frame(main_pane, bg="#f5f5f0", relief="groove", bd=1)
        main_pane.add(right_pane, minsize=300)

        # 右侧上下PanedWindow
        right_pw = tk.PanedWindow(right_pane, orient="vertical", bg="#888",
                                   sashwidth=5, sashrelief="raised", sashpad=2)
        right_pw.pack(fill="both", expand=True)

        # 右上：求解步骤区
        step_top = tk.Frame(right_pw, bg="#f5f5f0")
        right_pw.add(step_top, minsize=80, height=220)
        tk.Label(step_top, text="── 求解步骤 ──",
                 bg="#f5f5f0", font=("宋体",10,"bold")).pack(pady=(4,2))
        step_outer = tk.Frame(step_top, bg="#f5f5f0")
        step_outer.pack(fill="both", expand=True)
        vsb3 = tk.Scrollbar(step_outer, orient="vertical")
        self.step_text = tk.Text(step_outer, font=("Consolas",10),
                                 bg="#fffff0", yscrollcommand=vsb3.set,
                                 wrap="none", state="disabled")
        vsb3.config(command=self.step_text.yview)
        vsb3.pack(side="right", fill="y")
        self.step_text.pack(fill="both", expand=True)

        # 右下：图形区
        self.chart_frame = tk.Frame(right_pw, bg="#f5f5f0",
                                    relief="groove", bd=1)
        right_pw.add(self.chart_frame, minsize=200)
        hint = "求解后自动显示图形\n【2个变量】可行域图  |  【2个以上变量】灵敏度区间图"
        tk.Label(self.chart_frame, text=hint,
                 bg="#f5f5f0", fg="#888", font=("宋体",9), justify="center").pack(expand=True)


    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            n = len(self.obj_entries)
            m = len(self.rhs_entries)
            if r == 0 and c < n:
                return self.obj_entries[c]
            if 1 <= r <= m and c < n:
                return self.con_entries[r-1][c]
            if 1 <= r <= m and c == n:
                return self.rhs_entries[r-1]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        try:
            n = len(self.obj_entries)
            if r == 0: return "#ffff99"
            if c < n:  return "#ccffcc"
            return "#ccccff"
        except AttributeError:
            return "#ffffff"

    def _all_entries(self):
        try:
            n = len(self.obj_entries)
            for j, e in enumerate(self.obj_entries):
                yield (0, j, e)
            for i, row in enumerate(self.con_entries):
                for j, e in enumerate(row):
                    yield (i+1, j, e)
            for i, e in enumerate(self.rhs_entries):
                yield (i+1, n, e)
        except AttributeError:
            return

    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        n = self.n_vars.get()
        m = self.n_cons.get()
        BG   = "#e8e0d0"
        YELL = "#ffff99"
        GRN  = "#ccffcc"
        PINK = "#ff9999"
        CYAN = "#ccffff"
        HDR  = "#ffcc99"
        W    = 7

        # ── 目标函数系数 ──
        tk.Label(self.body, text="目标函数系数", bg=BG,
                 font=("宋体",10,"bold")).grid(row=0, column=0, sticky="w",
                 padx=4, pady=(4,0), columnspan=n+2)
        # 目标函数表头
        subs = "₁₂₃₄₅₆₇₈₉"
        for j in range(n):
            vname = f"x{subs[j]}" if j < len(subs) else f"x{j+1}"
            tk.Label(self.body, text=vname, bg=HDR, font=("宋体",10),
                     relief="ridge", width=W).grid(row=1, column=j+1, padx=1, pady=1)
        # 目标函数输入行
        self.obj_entries = []
        for j in range(n):
            e = tk.Entry(self.body, width=W, font=("宋体",10), bg=YELL, relief="sunken", bd=1)
            e.grid(row=2, column=j+1, padx=1, pady=1)
            self._bind_cell(e, 0, j)
            self.obj_entries.append(e)

        # ── 约束条件系数 ──
        tk.Label(self.body, text="约束条件系数", bg=BG,
                 font=("宋体",10,"bold")).grid(row=3, column=0, sticky="w",
                 padx=4, pady=(6,0), columnspan=n+4)
        # 约束表头（row=4）
        tk.Label(self.body, text="", bg=BG, width=3).grid(row=4, column=0)
        for j in range(n):
            vname = f"x{subs[j]}" if j < len(subs) else f"x{j+1}"
            tk.Label(self.body, text=vname, bg=HDR, font=("宋体",10),
                     relief="ridge", width=W).grid(row=4, column=j+1, padx=1, pady=1)
        tk.Label(self.body, text="约束条件实际值", bg=HDR, font=("宋体",10),
                 relief="ridge", width=14).grid(row=4, column=n+1, padx=1, pady=1)
        tk.Label(self.body, text="约束关系", bg=HDR, font=("宋体",10),
                 relief="ridge", width=10).grid(row=4, column=n+2, padx=1, pady=1)
        tk.Label(self.body, text="约束条件常数项", bg=HDR, font=("宋体",10),
                 relief="ridge", width=14).grid(row=4, column=n+3, padx=1, pady=1)

        # 约束输入行（row=5,6,...,5+m-1）
        self.con_entries   = []
        self.rel_vars      = []
        self.rhs_entries   = []
        self.actual_labels = []
        for i in range(m):
            row = 5 + i
            tk.Label(self.body, text=str(i+1), bg=BG,
                     font=("宋体",10), width=3).grid(row=row, column=0, padx=2)
            row_e = []
            for j in range(n):
                e = tk.Entry(self.body, width=W, font=("宋体",10), bg=GRN, relief="sunken", bd=1)
                e.grid(row=row, column=j+1, padx=1, pady=1)
                self._bind_cell(e, i+1, j)
                row_e.append(e)
            self.con_entries.append(row_e)
            al = tk.Label(self.body, text="0", bg=PINK, font=("宋体",10),
                          relief="sunken", width=14)
            al.grid(row=row, column=n+1, padx=1, pady=1)
            self.actual_labels.append(al)
            rv = tk.StringVar(value="≤")
            cb = ttk.Combobox(self.body, textvariable=rv,
                              values=["≤", "≥", "=", "<", ">"], width=4,
                              font=("宋体",10), state="readonly")
            cb.grid(row=row, column=n+2, padx=1, pady=1)
            self.rel_vars.append(rv)
            rhs = tk.Entry(self.body, width=14, font=("宋体",10), bg="#ccccff", relief="sunken", bd=1)
            rhs.grid(row=row, column=n+3, padx=1, pady=1)
            self._bind_cell(rhs, i+1, n)
            self.rhs_entries.append(rhs)

        # ── 变量类型行（仅混合整数规划显示）──
        VAR_ROW = 5 + m + 1
        self.var_type_vars = []
        if self.title_text == "混合整数规划":
            tk.Label(self.body, text="变量类型", bg=BG,
                     font=("宋体",9,"bold")).grid(row=VAR_ROW, column=0, sticky="w", padx=4, pady=(6,2))
            tk.Label(self.body, text="(C=连续 I=整数 B=0-1)",
                     bg=BG, font=("宋体",8), fg="#666").grid(
                     row=VAR_ROW, column=1, columnspan=min(n,6), sticky="w")
            VAR_ROW += 1
            for j in range(n):
                vt = tk.StringVar(value="C")
                cb2 = ttk.Combobox(self.body, textvariable=vt,
                                   values=["C","I","B"], width=3,
                                   font=("宋体",9), state="readonly")
                cb2.grid(row=VAR_ROW, column=j+1, padx=1, pady=1)
                self.var_type_vars.append(vt)
            VAR_ROW += 2
        else:
            VAR_ROW += 1

        # ── 最优解 / 最优值 ──
        R0 = VAR_ROW
        tk.Label(self.body, text="最优解", bg=BG,
                 font=("宋体",10,"bold"), width=6).grid(row=R0, column=0, sticky="w", padx=4)
        subs = "₁₂₃₄₅₆₇₈₉"
        self.result_labels = []
        for j in range(n):
            rl = tk.Label(self.body, text="", bg=CYAN, font=("宋体",10),
                          relief="sunken", width=W)
            rl.grid(row=R0, column=j+1, padx=1, pady=1)
            self.result_labels.append(rl)
        tk.Label(self.body, text="最优值", bg=BG,
                 font=("宋体",10,"bold")).grid(row=R0, column=n+2, sticky="e", padx=2)
        self.opt_label = tk.Label(self.body, text="", bg=PINK,
                                  font=("宋体",11,"bold"), relief="sunken", width=W)
        self.opt_label.grid(row=R0, column=n+3, padx=1, pady=1)

        # ── 灵敏度分析：最优方案 ──
        R1 = R0 + 2
        tk.Label(self.body, text="最优方案", bg=BG,
                 font=("宋体",10,"bold")).grid(row=R1, column=0, sticky="w", padx=4, pady=(6,0))
        tk.Label(self.body, text="目标函数变量系数", bg=BG,
                 font=("宋体",9,"bold")).grid(row=R1, column=3, columnspan=3, padx=1)
        R1 += 1
        for k, h in enumerate(["变量","最优解","相差值","下限","当前值","上限"]):
            tk.Label(self.body, text=h, bg=HDR, font=("宋体",9),
                     relief="ridge", width=W).grid(row=R1, column=k+1, padx=1, pady=1)
        R1 += 1
        self.sens_var_rows = []
        for j in range(n):
            row_lbls = []
            for k in range(6):
                bg = [BG, CYAN, YELL, "#e0e0ff", YELL, "#e0e0ff"][k]
                ll = tk.Label(self.body, text="-", bg=bg, font=("宋体",9),
                              relief="sunken", width=W)
                ll.grid(row=R1+j, column=k+1, padx=1, pady=1)
                row_lbls.append(ll)
            self.sens_var_rows.append(row_lbls)

        # ── 灵敏度分析：约束条件 ──
        R2 = R1 + n + 1
        tk.Label(self.body, text="约束条件", bg=BG,
                 font=("宋体",10,"bold")).grid(row=R2, column=0, sticky="w", padx=4, pady=(4,0))
        tk.Label(self.body, text="约束条件常数项", bg=BG,
                 font=("宋体",9,"bold")).grid(row=R2, column=5, columnspan=3, padx=1)
        R2 += 1
        for k, h in enumerate(["约束","实际值","松弛剩余","对偶价格","下限","当前值","上限"]):
            tk.Label(self.body, text=h, bg=HDR, font=("宋体",9),
                     relief="ridge", width=W).grid(row=R2, column=k+1, padx=1, pady=1)
        R2 += 1
        self.sens_con_rows = []
        for i in range(m):
            row_lbls = []
            for k in range(7):
                bg = [BG, PINK, YELL, "#ffe0e0", "#e0e0ff", YELL, "#e0e0ff"][k]
                ll = tk.Label(self.body, text="-", bg=bg, font=("宋体",9),
                              relief="sunken", width=W)
                ll.grid(row=R2+i, column=k+1, padx=1, pady=1)
                row_lbls.append(ll)
            self.sens_con_rows.append(row_lbls)

        self.conclusion_label = tk.Label(self.body, text="", bg=BG,
                                         font=("宋体",10), fg="#cc0000")
        self.conclusion_label.grid(row=R2+m+1, column=0, columnspan=10,
                                   sticky="w", padx=4, pady=(4,2))

        self.entries_built = True

    def _parse_expr(self):
        """解析表达式，自动填入表格"""
        import re
        def parse_poly(s):
            """解析多项式，返回系数字典 {var_index: coef}"""
            s = s.strip().replace(" ", "").replace("－", "-").replace("＋", "+")
            # 统一格式：确保每项前有符号
            if s and s[0] not in "+-":
                s = "+" + s
            coefs = {}
            # 匹配: 可选符号 + 可选系数 + x + 数字
            for m in re.finditer(r"([+-])([0-9.]*)[xX]([0-9]+)", s):
                sign = 1 if m.group(1) == "+" else -1
                c_str = m.group(2)
                c = float(c_str) if c_str else 1.0
                idx = int(m.group(3)) - 1  # 0-based
                coefs[idx] = sign * c
            return coefs

        try:
            # 解析目标函数
            obj_raw = self.expr_obj.get().strip()
            # 去掉 max/min 前缀
            obj_raw = re.sub(r"^(max|min|maximize|minimize)\s*", "", obj_raw, flags=re.I)
            obj_coefs = parse_poly(obj_raw)
            if not obj_coefs:
                messagebox.showwarning("解析失败", "目标函数解析失败，请检查格式")
                return

            # 解析约束
            cons_raw = self.expr_cons_text.get("1.0", "end").strip().split("\n")
            cons_raw = [l.strip() for l in cons_raw if l.strip() and not l.startswith("例")]
            if not cons_raw:
                messagebox.showwarning("解析失败", "未检测到约束条件")
                return

            parsed_cons = []
            for line in cons_raw:
                line = line.replace(" ", "").replace("＜＝","<=").replace("＞＝",">=")
                # 找约束关系符号
                rel = None
                for sym, mapped in [("<=","≤"),(">=","≥"),("<","≤"),(">","≥"),("=","=")]:
                    if sym in line:
                        rel = mapped
                        parts = line.split(sym, 1)
                        break
                if rel is None:
                    messagebox.showwarning("解析失败", f"约束 '{line}' 未找到关系符号")
                    return
                lhs_coefs = parse_poly(parts[0])
                try:
                    rhs = float(parts[1])
                except:
                    messagebox.showwarning("解析失败", f"约束右端项 '{parts[1]}' 不是数字")
                    return
                parsed_cons.append((lhs_coefs, rel, rhs))

            # 确定变量数量
            all_vars = set(obj_coefs.keys())
            for coefs, _, _ in parsed_cons:
                all_vars |= set(coefs.keys())
            n = max(all_vars) + 1
            m = len(parsed_cons)

            # 更新spinbox
            self.n_vars.set(n)
            self.n_cons.set(m)

            # 重建表格
            self._build_table()

            # 填入目标函数系数
            for j in range(n):
                v = obj_coefs.get(j, 0)
                self.obj_entries[j].delete(0, "end")
                self.obj_entries[j].insert(0, str(int(v) if v == int(v) else v))

            # 填入约束系数
            for i, (coefs, rel, rhs) in enumerate(parsed_cons):
                for j in range(n):
                    v = coefs.get(j, 0)
                    self.con_entries[i][j].delete(0, "end")
                    if v != 0:
                        self.con_entries[i][j].insert(0, str(int(v) if v == int(v) else v))
                self.rel_vars[i].set(rel)
                self.rhs_entries[i].delete(0, "end")
                self.rhs_entries[i].insert(0, str(int(rhs) if rhs == int(rhs) else rhs))

            messagebox.showinfo("解析成功", f"已解析 {n} 个变量，{m} 个约束，已填入表格")

        except Exception as e:
            messagebox.showerror("解析错误", str(e))

    def _get_data(self):
        n = self.n_vars.get()
        m = self.n_cons.get()
        c, A, b, rels = [], [], [], []
        for e in self.obj_entries:
            c.append(float(e.get() or 0))
        REL_MAP = {"<":"≤", ">":"≥", "=":"=", "≤":"≤", "≥":"≥"}
        for i in range(m):
            row = [float(e.get() or 0) for e in self.con_entries[i]]
            A.append(row)
            b.append(float(self.rhs_entries[i].get() or 0))
            rels.append(REL_MAP.get(self.rel_vars[i].get(), "≤"))
        return c, A, b, rels

    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        try:
            from scipy.optimize import linprog
            import numpy as np
            c, A, b, rels = self._get_data()
            n = len(c)
            maximize = (self.obj_type.get() == "最大化")
            obj = [-ci for ci in c] if maximize else c[:]

            # 整数规划分支
            if self.binary_vars or self.integer_vars or self.title_text == "混合整数规划":
                self._solve_integer(c, A, b, rels, maximize)
                return

            A_ub, b_ub, A_eq, b_eq = [], [], [], []
            ub_idx, eq_idx = [], []  # 记录原约束下标
            for i, rel in enumerate(rels):
                if rel == "≤":
                    A_ub.append(A[i]); b_ub.append(b[i]); ub_idx.append(i)
                elif rel == "≥":
                    A_ub.append([-a for a in A[i]]); b_ub.append(-b[i]); ub_idx.append(i)
                else:
                    A_eq.append(A[i]); b_eq.append(b[i]); eq_idx.append(i)

            bounds = [(0, None)] * n

            res = linprog(obj,
                          A_ub=A_ub or None, b_ub=b_ub or None,
                          A_eq=A_eq or None, b_eq=b_eq or None,
                          bounds=bounds, method="highs")

            if not res.success:
                messagebox.showerror("求解失败", f"无可行解或无界\n{res.message}")
                return

            x = res.x
            opt = -res.fun if maximize else res.fun

            # 更新主界面结果
            def nfmt(v):
                if abs(v) < 1e-8: return "0"
                if abs(v - round(v)) < 1e-6: return str(int(round(v)))
                return f"{v:.2f}"
            for j, lbl in enumerate(self.result_labels):
                lbl.config(text=nfmt(x[j]))
            self.opt_label.config(text=nfmt(opt))
            for i in range(len(A)):
                val = sum(A[i][j] * x[j] for j in range(n))
                self.actual_labels[i].config(text=nfmt(val))
            self._auto_save()  # 求解成功后自动保存

            # ── 精确灵敏度分析（单纯形基矩阵法）────────
            INF = 1e+30

            # 对偶价格（shadow price）
            # scipy返回的marginals：对最小化问题，≤约束marginal<=0，≥约束marginal<=0
            # 原工具显示规则：直接显示marginal值（最小化时≥约束为负，最大化时≤约束为负）
            shadow = []
            ub_dual = list(res.ineqlin.marginals) if (hasattr(res,'ineqlin') and res.ineqlin is not None) else [0]*len(A_ub)
            eq_dual = list(res.eqlin.marginals)   if (hasattr(res,'eqlin')   and res.eqlin  is not None) else [0]*len(A_eq)
            ui, ei = 0, 0
            for i, rel in enumerate(rels):
                if rel in ("<=","≤","<"):
                    sp = ub_dual[ui] if ui < len(ub_dual) else 0
                    ui += 1
                    # 最大化：对≤约束，shadow=marginal取反（正值表示有价值）
                    # 最小化：对≤约束，marginal<=0，显示原值
                    shadow.append(-sp if maximize else sp)
                elif rel in (">=","≥",">"):
                    sp = ub_dual[ui] if ui < len(ub_dual) else 0
                    ui += 1
                    # ≥约束转为≤时取负，marginal对应原约束的shadow=sp（已是负值）
                    # 最小化时直接显示sp（负值），最大化时取反
                    shadow.append(sp if maximize else sp)
                else:
                    sp = eq_dual[ei] if ei < len(eq_dual) else 0
                    ei += 1
                    shadow.append(-sp if maximize else sp)

            # 构建标准形（仅处理≤约束加松弛，简化处理）
            try:
                A_np = np.array(A_ub, dtype=float)
                b_np = np.array(b_ub, dtype=float)
                ms = len(A_ub)
                # 标准形：[A|I]，目标用最小化形式
                A_std = np.hstack([A_np, np.eye(ms)])
                c_std = np.array(obj + [0.0]*ms)
                n_std = n + ms

                # 计算松弛变量值
                s_vals = b_np - A_np @ x
                all_vals = np.concatenate([x, s_vals])

                # 找基变量（值>0）
                basic_idx = sorted([j for j in range(n_std) if all_vals[j] > 1e-6])
                # 若基的大小不足m，补入近似0的松弛变量
                if len(basic_idx) < ms:
                    cands = sorted(range(n_std), key=lambda j: -all_vals[j])
                    for j in cands:
                        if j not in basic_idx:
                            basic_idx.append(j)
                        if len(basic_idx) == ms:
                            break
                basic_idx = sorted(basic_idx[:ms])

                B     = A_std[:, basic_idx]
                B_inv = np.linalg.inv(B)
                c_B   = c_std[basic_idx]
                x_B   = B_inv @ b_np

                # Reduced costs（最小化视角，rc>=0为最优）
                rc = np.array([c_std[k] - float(c_B @ (B_inv @ A_std[:,k]))
                               for k in range(n_std)])
                non_basic = [k for k in range(n_std) if k not in basic_idx]

                # ── 目标函数系数范围 ──
                c_lo, c_hi, c_diff = [], [], []
                for j in range(n):
                    if j in basic_idx:
                        bi = basic_idx.index(j)
                        r_lo, r_hi = [], []
                        for k in non_basic:
                            y = float((B_inv @ A_std[:,k])[bi])
                            rck = rc[k]
                            if abs(y) < 1e-10: continue
                            # 改变c[j]+d，obj[j]=-c[j]-d
                            # rc_k新 = rc_k + d*y >= 0 => d >= -rc_k/y(y>0), d<=-rc_k/y(y<0)
                            ratio = -rck / y
                            if y > 0: r_lo.append(ratio)
                            else:     r_hi.append(ratio)
                        d_lo = max(r_lo) if r_lo else -INF
                        d_hi = min(r_hi) if r_hi else  INF
                        c_lo.append(c[j] + d_lo if d_lo > -INF else -INF)
                        c_hi.append(c[j] + d_hi if d_hi <  INF else  INF)
                        c_diff.append(0.0)
                    else:
                        # 非基：rc[j]>=0，改变c[j]+d后 rc_new=rc[j]-d>=0 => d<=rc[j]
                        c_lo.append(-INF)
                        c_hi.append(c[j] + rc[j])
                        c_diff.append(rc[j])   # 相差值=reduced cost（正值）

                # ── 约束右端项范围（对偶价格保持不变的范围）──
                # 通过扰动法：找使对偶价格不变的b[i]范围
                orig_duals = list(res.ineqlin.marginals)
                b_lo2, b_hi2 = [], []
                for i in range(len(b)):
                    # 向下搜索下限
                    lo_d, hi_d = -1e8, 0.0
                    found_lo = None
                    for _ in range(60):
                        mid = (lo_d + hi_d) / 2
                        bt = list(b_ub)
                        bt[i] = b_ub[i] + mid
                        r2 = linprog(obj, A_ub=bt and [A_ub[k] for k in range(len(A_ub))],
                                     b_ub=bt,
                                     A_eq=A_eq or None, b_eq=b_eq or None,
                                     bounds=bounds, method="highs")
                        if r2.success and hasattr(r2,'ineqlin') and r2.ineqlin is not None:
                            if np.allclose(r2.ineqlin.marginals, orig_duals, atol=1e-4):
                                found_lo = mid; lo_d = mid
                            else:
                                hi_d = mid
                        else:
                            hi_d = mid
                    b_lo2.append(b[i] + found_lo if found_lo is not None else -INF)

                    # 向上搜索上限
                    lo_d, hi_d = 0.0, 1e8
                    found_hi = None
                    for _ in range(60):
                        mid = (lo_d + hi_d) / 2
                        bt = list(b_ub)
                        bt[i] = b_ub[i] + mid
                        r2 = linprog(obj, A_ub=[A_ub[k] for k in range(len(A_ub))],
                                     b_ub=bt,
                                     A_eq=A_eq or None, b_eq=b_eq or None,
                                     bounds=bounds, method="highs")
                        if r2.success and hasattr(r2,'ineqlin') and r2.ineqlin is not None:
                            if np.allclose(r2.ineqlin.marginals, orig_duals, atol=1e-4):
                                found_hi = mid; lo_d = mid
                            else:
                                hi_d = mid
                        else:
                            hi_d = mid
                    b_hi2.append(b[i] + found_hi if found_hi is not None else INF)

                self._show_sensitivity(x, c, A, b, rels, opt, shadow,
                                       c_lo, c_hi, b_lo2, b_hi2, maximize,
                                       c_diff=c_diff)
            except Exception as e:
                c_lo = [-INF]*n; c_hi = [INF]*n
                b_lo2 = [-INF]*len(b); b_hi2 = [INF]*len(b)
                self._show_sensitivity(x, c, A, b, rels, opt, shadow,
                                       c_lo, c_hi, b_lo2, b_hi2, maximize)

        except ValueError as e:
            messagebox.showerror("输入错误", f"请检查数据格式\n{e}")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _show_sensitivity(self, x, c, A, b, rels, opt, shadow,
                          c_lo, c_hi, b_lo, b_hi, maximize, c_diff=None):
        """直接更新页面内灵敏度分析标签"""
        INF = 1e+30
        subs = "₁₂₃₄₅₆₇₈₉"
        def fmt(v):
            if v is None: return "-"
            if abs(v) >= INF*0.9: return "1E+30" if v > 0 else "-1E+30"
            if abs(v) < 1e-8: return "0"
            if abs(v - round(v)) < 1e-6 and abs(v) < 1e10: return str(int(round(v)))
            return f"{v:.5g}"

        n = len(x)
        m = len(b)

        # 变量灵敏度行
        for j in range(n):
            cur = c[j]
            lo  = c_lo[j]
            hi  = c_hi[j]
            if c_diff is not None:
                diff = c_diff[j]
            else:
                diff = 0.0 if abs(x[j]) > 1e-6 else (cur - lo if lo > -INF else INF)
            xval = fmt(x[j])
            vname = f"X{subs[j]}" if j<len(subs) else f"X{j+1}"
            vals = [vname, xval, fmt(diff), fmt(lo), fmt(cur), fmt(hi)]
            for k, v in enumerate(vals):
                self.sens_var_rows[j][k].config(text=v)

        # 约束灵敏度行
        for i in range(m):
            actual = sum(A[i][j]*x[j] for j in range(n))
            slack  = b[i] - actual if rels[i] != "≥" else actual - b[i]
            sp     = shadow[i] if i < len(shadow) else 0
            lo     = b_lo[i]
            hi     = b_hi[i]
            vals = [str(i+1), fmt(actual), fmt(slack),
                    fmt(sp), fmt(lo), fmt(b[i]), fmt(hi)]
            for k, v in enumerate(vals):
                self.sens_con_rows[i][k].config(text=v)

        # 结论
        zero_slack = sum(1 for j in range(n) if abs(x[j]) < 1e-6)
        conclusion = "本模型存在唯一解，且存在对应的唯一对偶价格" if zero_slack > 0 else "本模型最优解已求得"
        self.conclusion_label.config(text=conclusion)

        # 绘制图形
        try:
            self._draw_chart(x, c, A, b, rels, opt, c_lo, c_hi, b_lo, b_hi, maximize)
        except Exception:
            pass

        # ── 更新模型表达式 ──
        def coef_str(v, j, first=False):
            if v == 0: return ""
            vn = xname(j)
            s = f"{abs(v):g}{vn}"
            if first: return f"-{s}" if v < 0 else s
            return f" - {s}" if v < 0 else f" + {s}"

        obj_type = "max" if maximize else "min"
        obj_parts = [coef_str(c[j], j, j==0) for j in range(n)]
        obj_parts = [p for p in obj_parts if p]
        obj_expr = "  ".join(obj_parts) if obj_parts else "0"
        lines = [f"{obj_type}  Z = {obj_expr}", ""]
        lines.append("s.t.")
        for i in range(m):
            parts = [coef_str(A[i][j], j, j==0) for j in range(n)]
            parts = [p for p in parts if p]
            lhs = "  ".join(parts) if parts else "0"
            lines.append(f"  {lhs}  {rels[i]}  {b[i]:g}")
        lines.append("")
        for j in range(n):
            lines.append(f"  x{j+1} >= 0")
        lines.append("")
        lines.append("最优解: " + ",  ".join(
            (xname(j)) + f"={fmt(x[j])}" for j in range(n)))
        lines.append(f"最优值: Z = {fmt(opt)}")

        # 把求解结果追加到步骤框末尾
        try:
            self.step_text.config(state="normal")
            self.step_text.insert("end", "\n" + "─"*50 + "\n", "sep")
            self.step_text.insert("end", "【求解结果】\n", "title")
            self.step_text.insert("end", "  " + "\n  ".join(lines) + "\n", "vars")
            self.step_text.config(state="disabled")
            self.step_text.see("end")
        except Exception:
            pass

    def _solve_integer(self, c, A, b, rels, maximize):
        """使用PuLP求解整数规划"""
        try:
            import pulp
        except ImportError:
            try:
                import subprocess, sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pulp", "-q"])
                import pulp
            except Exception:
                messagebox.showerror("缺少依赖", "请在命令行运行: pip install pulp")
                return

        sense = pulp.LpMaximize if maximize else pulp.LpMinimize
        prob = pulp.LpProblem("IP", sense)
        n = len(c)

        if self.binary_vars:
            xs = [pulp.LpVariable(f"x{j+1}", cat="Binary") for j in range(n)]
        elif self.integer_vars is True:
            xs = [pulp.LpVariable(f"x{j+1}", lowBound=0, cat="Integer") for j in range(n)]
        elif self.title_text == "混合整数规划" and hasattr(self, 'var_type_vars') and self.var_type_vars:
            # 根据用户选择的变量类型
            xs = []
            for j in range(n):
                vtype = self.var_type_vars[j].get() if j < len(self.var_type_vars) else "C"
                if vtype == "B":
                    xs.append(pulp.LpVariable(f"x{j+1}", cat="Binary"))
                elif vtype == "I":
                    xs.append(pulp.LpVariable(f"x{j+1}", lowBound=0, cat="Integer"))
                else:
                    xs.append(pulp.LpVariable(f"x{j+1}", lowBound=0, cat="Continuous"))
        else:
            int_set = set(self.integer_vars or [])
            xs = [pulp.LpVariable(f"x{j+1}", lowBound=0,
                  cat="Integer" if j in int_set else "Continuous") for j in range(n)]

        prob += pulp.lpSum(c[j] * xs[j] for j in range(n))
        for i, rel in enumerate(rels):
            expr = pulp.lpSum(A[i][j] * xs[j] for j in range(n))
            if rel == "≤":   prob += expr <= b[i]
            elif rel == "≥": prob += expr >= b[i]
            else:             prob += expr == b[i]

        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        if pulp.LpStatus[prob.status] == "Optimal":
            xvals = [pulp.value(xs[j]) for j in range(n)]
            for j, lbl in enumerate(self.result_labels):
                v = xvals[j]
                lbl.config(text=str(int(round(v))) if abs(v-round(v))<1e-4 else f"{v:.4f}")
            opt_v = pulp.value(prob.objective)
            self.opt_label.config(text=str(int(round(opt_v))) if abs(opt_v-round(opt_v))<1 else f"{opt_v:.4f}")
            for i in range(len(A)):
                val = sum(A[i][j] * xvals[j] for j in range(n))
                self.actual_labels[i].config(text=f"{val:.1f}")
            # 写步骤
            try:
                self.step_text.config(state="normal")
                self.step_text.delete("1.0","end")
                self.step_text.insert("end","【混合整数规划求解结果】\n\n","title")
                for j in range(n):
                    vt = self.var_type_vars[j].get() if hasattr(self,"var_type_vars") and j<len(self.var_type_vars) else "?"
                    self.step_text.insert("end",
                        f"  x{j+1}({vt}) = {xvals[j]:.4g}\n","vars")
                self.step_text.insert("end",f"\n  最优值 Z = {opt_v:.4g}\n","result")
                self.step_text.config(state="disabled")
                self._auto_save()
            except Exception:
                pass
        else:
            messagebox.showerror("求解失败", f"状态: {pulp.LpStatus[prob.status]}")

    def _table_to_expr(self):
        """从表格生成表达式填入文本框"""
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成表格"); return
        try:
            c, A, b, rels = self._get_data()
            n, m = len(c), len(b)
            maximize = (self.obj_type.get() == "最大化")

            def term(v, j, first=False):
                if v == 0: return ""
                vstr = str(int(v)) if v == int(v) else str(v)
                xstr = xname(j)
                if first:
                    return f"-{vstr}{xstr}" if v < 0 else f"{vstr}{xstr}"
                return f" - {vstr}{xstr}" if v < 0 else f" + {vstr}{xstr}"

            obj_terms = [term(c[j], j, j==0) for j in range(n)]
            obj_str = "".join(t for t in obj_terms if t) or "0"
            prefix = "max" if maximize else "min"
            lines = [f"{prefix}  Z = {obj_str}", "", "s.t."]
            for i in range(m):
                parts = [term(A[i][j], j, j==0) for j in range(n)]
                lhs = "".join(t for t in parts if t) or "0"
                rel = rels[i].replace("≤","<=").replace("≥",">=")
                rhs = str(int(b[i])) if b[i]==int(b[i]) else str(b[i])
                lines.append(f"  {lhs} {rel} {rhs}")
            lines += [""] + [xname(j) + " >= 0" for j in range(n)]

            # 只更新表达式框（模型部分）
            self.main_expr_text.delete("1.0", "end")
            self.main_expr_text.insert("end", "\n".join(lines))
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _expr_to_table(self):
        """从表达式文本框解析并填入表格"""
        import re
        try:
            raw = self.main_expr_text.get("1.0", "end").strip()
            # 只取求解结果分隔线之前的内容
            if "# ── 求解结果" in raw:
                raw = raw[:raw.index("# ── 求解结果")].strip()
            raw = _normalize_expr(raw)
            lines = [l.strip() for l in raw.split("\n") if l.strip()]

            def parse_poly(s):
                s = s.strip().replace(" ","")
                if s and s[0] not in "+-": s = "+" + s
                coefs = {}
                for m in re.finditer(r"([+-])([0-9.]*)[xX]([0-9]+)", s):
                    sign = 1 if m.group(1)=="+" else -1
                    c_str = m.group(2)
                    c = float(c_str) if c_str else 1.0
                    coefs[int(m.group(3))-1] = sign * c
                return coefs

            # 找目标函数行
            obj_line = next((l for l in lines
                             if re.match(r"(max|min|MAX|MIN)", l, re.I)), None)
            if not obj_line:
                messagebox.showwarning("解析失败", "找不到目标函数行(需含max或min)"); return

            if re.match(r"(max|MAX)", obj_line, re.I):
                self.obj_type.set("最大化")
            else:
                self.obj_type.set("最小化")
            obj_part = re.sub(r"^(max|min)[^=]*=\s*", "", obj_line, flags=re.I)
            obj_coefs = parse_poly(obj_part)

            # 找约束行（含 <= >= = 的行，排除非负约束和目标函数行）
            REL_RE = re.compile(r"(<=|>=|<|>|=)")
            con_lines = []
            for l in lines:
                if not REL_RE.search(l): continue
                # 跳过 s.t. 行
                if re.match(r"s\.?t\.?", l, re.I): continue
                # 跳过目标函数行（含max/min）
                if re.match(r"\s*(max|min)", l, re.I): continue
                # 跳过注释行和结果行
                if l.strip().startswith("#"): continue
                if re.match(r"\s*(最优|Z\s*=)", l): continue
                # 跳过非负约束：xi>=0（含空格版本）
                l_clean = l.replace(" ","")
                if re.match(r"x\d+>=0$", l_clean): continue
                if re.match(r"x\d+<=0$", l_clean): continue
                con_lines.append(l)

            if not con_lines:
                messagebox.showwarning("解析失败", "找不到约束条件"); return

            parsed_cons = []
            REL_MAP = {"<=":"≤",">=":"≥","<":"≤",">":"≥","=":"="}
            for l in con_lines:
                l_clean = l.replace(" ","")
                matched = False
                for sym in ["<=",">=","<",">","="]:
                    if sym in l_clean:
                        parts = l_clean.split(sym, 1)
                        try: rhs = float(parts[1])
                        except: continue
                        parsed_cons.append((parse_poly(parts[0]),
                                            REL_MAP[sym], rhs))
                        matched = True
                        break
                if not matched:
                    messagebox.showwarning("解析失败", f"无法解析约束行：{l}")
                    return

            all_vars = set(obj_coefs.keys())
            for coefs,_,_ in parsed_cons: all_vars |= set(coefs.keys())
            if not all_vars:
                messagebox.showwarning("解析失败", "未识别到变量(格式应为x1,x2...)"); return
            n = max(all_vars) + 1
            m = len(parsed_cons)

            self.n_vars.set(n)
            self.n_cons.set(m)
            # 强制重建表格，清空所有旧数据
            self.entries_built = False
            self._build_table()

            for j in range(n):
                v = obj_coefs.get(j, 0)
                self.obj_entries[j].delete(0,"end")
                self.obj_entries[j].insert(0, str(int(v) if v==int(v) else v))

            for i,(coefs,rel,rhs) in enumerate(parsed_cons):
                for j in range(n):
                    v = coefs.get(j, 0)
                    self.con_entries[i][j].delete(0,"end")
                    if v != 0:
                        self.con_entries[i][j].insert(0, str(int(v) if v==int(v) else v))
                self.rel_vars[i].set(rel)
                self.rhs_entries[i].delete(0,"end")
                self.rhs_entries[i].insert(0, str(int(rhs) if rhs==int(rhs) else rhs))

            messagebox.showinfo("解析成功", f"已填入：{n}个变量，{m}个约束")
        except Exception as e:
            messagebox.showerror("解析错误", str(e))

    def _simplex_steps(self, c_orig, A, b, maximize=True):
        """记录单纯形法求解步骤"""
        import numpy as np
        n = len(c_orig)
        m = len(b)
        steps = []
        c = [-v for v in c_orig] if maximize else list(c_orig)
        tab = np.zeros((m+1, n+m+1))
        tab[:m, :n] = np.array(A, dtype=float)
        tab[:m, n:n+m] = np.eye(m)
        tab[:m, -1] = np.array(b, dtype=float)
        tab[m, :n] = c
        basic = list(range(n, n+m))
        vn = [(xname(j)) for j in range(n)] + [f"s{i+1}" for i in range(m)]

        x_B0 = list(tab[:m,-1])
        steps.append({"title":"初始基可行解",
            "note":f"初始基变量：{', '.join(vn[b] for b in basic)}",
            "basic":[vn[b] for b in basic],
            "x_B":[round(v,4) for v in x_B0], "obj":0})

        for it in range(50):
            obj_row = tab[m, :n+m]
            pc = int(np.argmin(obj_row))
            if obj_row[pc] >= -1e-8:
                steps.append({"title":"✅ 达到最优",
                    "note":"所有检验数 ≥ 0，当前解即为最优解"})
                break
            col = tab[:m, pc]
            ratios = [(tab[i,-1]/col[i] if col[i]>1e-10 else float('inf'), i)
                      for i in range(m)]
            pr = min(ratios, key=lambda r: r[0])[1]
            ev, lv = vn[pc], vn[basic[pr]]
            rv = tab[pr,-1]/col[pr]
            pivot = tab[pr, pc]
            tab[pr] /= pivot
            for i in range(m+1):
                if i != pr:
                    tab[i] -= tab[i,pc]*tab[pr]
            basic[pr] = pc
            obj_val = -tab[m,-1] if maximize else tab[m,-1]
            steps.append({"title":f"第{it+1}次迭代",
                "note":f"入基：{ev}  出基：{lv}  最小比值={rv:.4g}",
                "basic":[vn[b] for b in basic],
                "x_B":[round(float(v),4) for v in tab[:m,-1]],
                "obj":round(float(obj_val),4)})
        return steps

    def _draw_chart(self, x, c, A, b, rels, opt, c_lo, c_hi, b_lo, b_hi, maximize):
        """右下：图形；右上：求解步骤"""
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np

        # 清空图形区
        for w in self.chart_frame.winfo_children():
            w.destroy()

        top_chart = self.chart_frame
        top_chart.config(height=0)
        step_text = self.step_text

        # 填写求解步骤（带颜色标记）
        step_text.config(state="normal")
        step_text.delete("1.0", "end")
        step_text.tag_config("title",   foreground="#1a5276", font=("宋体",10,"bold"))
        step_text.tag_config("note",    foreground="#333333", font=("Courier New",10))
        step_text.tag_config("vars",    foreground="#196F3D", font=("Courier New",10))
        step_text.tag_config("obj",     foreground="#922B21", font=("Courier New",10,"bold"))
        step_text.tag_config("sep",     foreground="#aaaaaa", font=("Courier New",9))
        step_text.tag_config("optimal", foreground="#1a5276", font=("宋体",11,"bold"))
        try:
            A_ub_only = [A[i] for i in range(len(A)) if rels[i] in ("≤","<=","<")]
            b_ub_only = [b[i] for i in range(len(b)) if rels[i] in ("≤","<=","<")]
            steps = self._simplex_steps(c, A_ub_only, b_ub_only, maximize)
            n_v = len(c)
            for s in steps:
                step_text.insert("end", "─"*50+"\n", "sep")
                step_text.insert("end", f"【{s['title']}】\n", "title")
                step_text.insert("end", f"  {s['note']}\n", "note")
                if "basic" in s:
                    xvals = {s['basic'][k]: s['x_B'][k] for k in range(len(s['basic']))}
                    xline = "   ".join(
                        (xname(j)) + f"={'★' if xvals.get(f'x{j+1}',0)!=0 else '0':>1} = {xvals.get(f'x{j+1}',0):.4g}"
                        for j in range(n_v))
                    step_text.insert("end", f"  决策变量: {xline}\n", "vars")
                    bline = "   ".join(f"{s['basic'][k]}={s['x_B'][k]:.4g}"
                                       for k in range(len(s['basic'])))
                    step_text.insert("end", f"  基变量:   {bline}\n", "vars")
                if "obj" in s and s["obj"] != 0:
                    step_text.insert("end", f"  目标值:   Z = {s['obj']:.6g}\n", "obj")
            step_text.config(state="disabled")
        except Exception as e:
            step_text.insert("end", f"步骤计算出错: {e}")
            step_text.config(state="disabled")

        n = len(c)
        INF = 1e+30
        fig, axes = plt.subplots(1, 1 if n != 2 else 1,
                                  figsize=(5.5, 4.0), dpi=90)
        fig.patch.set_facecolor("#f5f5f0")

        if n == 2:
            # ── 可行域图 ──
            ax = axes
            ax.set_facecolor("white")
            ax.legend_ = None  # 清除残留图例
            ax.set_title("可行域", fontsize=13, fontweight="bold", fontfamily="SimHei")
            ax.set_xlabel("$x_1$", fontsize=13)
            ax.set_ylabel("$x_2$", fontsize=13, rotation=0, labelpad=12)

            # 坐标范围
            x1_max = max([b[i]/A[i][0] for i in range(len(b)) if A[i][0]>1e-10] + [x[0]*2+1])
            x2_max = max([b[i]/A[i][1] for i in range(len(b)) if A[i][1]>1e-10] + [x[1]*2+1])
            x1_max *= 1.08; x2_max *= 1.08
            x1v = np.linspace(0, x1_max, 600)
            colors = ["#e74c3c","#2980b9","#27ae60","#8e44ad","#e67e22"]

            # 计算可行域顶点（用scipy）
            from scipy.spatial import ConvexHull
            from itertools import combinations
            m_con = len(b)
            # 建立约束矩阵（含非负约束）
            A_full = [list(row) for row in A] + [[-1,0],[0,-1]]
            b_full = list(b) + [0, 0]
            rels_full = list(rels) + ["≥","≥"]

            # 求所有约束边界交点
            vertices = []
            n_con = len(A_full)
            for i,j in combinations(range(n_con), 2):
                a = np.array([[A_full[i][0],A_full[i][1]],
                              [A_full[j][0],A_full[j][1]]], dtype=float)
                bv = np.array([b_full[i], b_full[j]], dtype=float)
                try:
                    pt = np.linalg.solve(a, bv)
                    if pt[0] < -1e-6 or pt[1] < -1e-6: continue
                    # 检查是否满足所有约束
                    ok = True
                    for k in range(m_con):
                        lhs = A[k][0]*pt[0] + A[k][1]*pt[1]
                        if rels[k] in ("≤","<=","<") and lhs > b[k]+1e-6: ok=False; break
                        if rels[k] in ("≥",">=",">") and lhs < b[k]-1e-6: ok=False; break
                    if ok: vertices.append(pt)
                except np.linalg.LinAlgError:
                    pass

            # 填充可行域（凸包）
            if len(vertices) >= 3:
                verts = np.array(vertices)
                try:
                    hull = ConvexHull(verts)
                    hull_pts = verts[hull.vertices]
                    # 按角度排序
                    cx, cy = hull_pts.mean(0)
                    angles = np.arctan2(hull_pts[:,1]-cy, hull_pts[:,0]-cx)
                    hull_pts = hull_pts[np.argsort(angles)]
                    from matplotlib.patches import Polygon as MplPolygon
                    poly = MplPolygon(hull_pts, closed=True,
                                      facecolor="#f1948a", alpha=0.7,
                                      edgecolor="none", zorder=1)
                    ax.add_patch(poly)
                except Exception:
                    pass

            # 画约束线并标注
            for i in range(m_con):
                a1, a2 = A[i][0], A[i][1]
                col = colors[i % len(colors)]
                # 约束表达式（数学格式）
                terms = []
                if abs(a1) > 1e-10:
                    c1 = int(a1) if a1==int(a1) else round(a1,3)
                    terms.append(("" if c1==1 else str(c1)) + "$x_1$")
                if abs(a2) > 1e-10:
                    c2 = int(a2) if a2==int(a2) else round(a2,3)
                    sign = "+" if a2>0 and terms else ""
                    terms.append(sign + ("" if c2==1 else str(c2)) + "$x_2$")
                rhs = int(b[i]) if b[i]==int(b[i]) else round(b[i],3)
                expr_str = "".join(terms) + f"={rhs}"

                if abs(a2) > 1e-10:
                    x2v = (b[i] - a1*x1v) / a2
                    mask = (x2v >= -x2_max*0.05) & (x2v <= x2_max*1.05) & (x1v >= 0)
                    if mask.sum() > 1:
                        ax.plot(x1v[mask], x2v[mask], color=col,
                                linewidth=2, zorder=3)
                        # 标注位置：线的右端
                        idx = np.where(mask)[0]
                        tx, ty = x1v[idx[-1]]*0.7, x2v[idx[-1]]*0.7
                        # 找个合适的标注位置
                        mid_idx = idx[len(idx)*2//3]
                        tx, ty = x1v[mid_idx], x2v[mid_idx]
                        ax.text(tx+x1_max*0.01, ty+x2_max*0.01,
                                expr_str, fontsize=8.5, color=col,
                                fontweight="bold", zorder=5)
                elif abs(a1) > 1e-10:
                    xv = b[i]/a1
                    ax.axvline(xv, color=col, linewidth=2, zorder=3)
                    rhs2 = int(b[i]) if b[i]==int(b[i]) else round(b[i],3)
                    ax.text(xv+x1_max*0.01, x2_max*0.6,
                            f"$x_1$={rhs2}", fontsize=8.5, color=col, fontweight="bold")

            # 标注所有顶点
            ALPHA = "ABCDEFGHIJ"
            verts_sorted = sorted(vertices, key=lambda p: (round(p[0],1), round(p[1],1)))
            for idx2, pt in enumerate(verts_sorted):
                ax.plot(pt[0], pt[1], "o", color="#333", markersize=6, zorder=6)
                lbl = f"{ALPHA[idx2]}({int(pt[0]) if abs(pt[0]-round(pt[0]))<0.01 else pt[0]:.3g},"
                lbl += f"{int(pt[1]) if abs(pt[1]-round(pt[1]))<0.01 else pt[1]:.3g})"
                ax.annotate(lbl, xy=(pt[0], pt[1]),
                            xytext=(6, 4), textcoords="offset points",
                            fontsize=8, color="#333", fontweight="bold", zorder=7)

            # 标最优点（红星）
            ax.plot(x[0], x[1], "*", color="red", markersize=16, zorder=8)
            opt_lbl = f"最优点({int(x[0]) if abs(x[0]-round(x[0]))<0.01 else x[0]:.3g},"
            opt_lbl += f"{int(x[1]) if abs(x[1]-round(x[1]))<0.01 else x[1]:.3g})"
            opt_lbl += f"\nZ={opt:.4g}"
            ax.annotate(opt_lbl,
                        xy=(x[0], x[1]),
                        xytext=(x[0]+x1_max*0.04, x[1]+x2_max*0.04),
                        fontsize=9, color="red", fontweight="bold", zorder=9,
                        arrowprops=dict(arrowstyle="->", color="red", lw=1.5),
                        fontfamily="SimHei")

            ax.set_xlim(-x1_max*0.02, x1_max*1.02)
            ax.set_ylim(-x2_max*0.02, x2_max*1.02)
            ax.spines["left"].set_position("zero")
            ax.spines["bottom"].set_position("zero")
            ax.spines["right"].set_visible(False)
            ax.spines["top"].set_visible(False)
            # 坐标轴箭头
            ax.plot(x1_max*1.04, 0, ">k", markersize=6, clip_on=False, zorder=10)
            ax.plot(0, x2_max*1.04, "^k", markersize=6, clip_on=False, zorder=10)
            ax.grid(True, alpha=0.25, linestyle="--")
            # 轴标签放在箭头旁
            ax.text(x1_max*1.03, -x2_max*0.05, "$x_1$", fontsize=12, ha="center")
            ax.text(-x1_max*0.04, x2_max*1.03, "$x_2$", fontsize=12, va="center")
            # 原点标注
            ax.text(-x1_max*0.04, -x2_max*0.05, "O", fontsize=10, color="#555")

        else:
            # ── 灵敏度区间图（多变量）──
            ax = axes
            ax.set_facecolor("#fafafa")
            fig.set_size_inches(5.5, 3.2)

            # 上半部分：目标函数系数范围
            labels = [f"$x_{{{j+1}}}$" for j in range(n)]
            cur_vals = np.array(c, dtype=float)
            lo_vals  = np.array([v if v>-INF*0.9 else cur_vals[j]-cur_vals[j]*2
                                  for j,v in enumerate(c_lo)])
            hi_vals  = np.array([v if v< INF*0.9 else cur_vals[j]+cur_vals[j]*2
                                  for j,v in enumerate(c_hi)])

            y_pos = np.arange(n)
            ax.barh(y_pos, hi_vals - lo_vals, left=lo_vals,
                    color="#aed6f1", edgecolor="#2980b9", height=0.5, alpha=0.8)
            ax.scatter(cur_vals, y_pos, color="red", zorder=5, s=50, label="Current")
            ax.scatter(np.array(x), y_pos-0.25, color="green",
                       zorder=5, s=40, marker="D", label="Optimal")

            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=10)
            ax.set_title("Sensitivity Range of Objective Coefficients",
                         fontsize=10, fontweight="bold")
            ax.set_xlabel("系数值", fontsize=9)
            ax.grid(True, alpha=0.3, axis="x")
            ax.axvline(0, color="gray", linewidth=0.5)

            # 标注当前值和最优解
            for j in range(n):
                lo_str = f"{c_lo[j]:.4g}" if c_lo[j]>-INF*0.9 else "-∞"
                hi_str = f"{c_hi[j]:.4g}" if c_hi[j]< INF*0.9 else "+∞"
                ax.text(lo_vals[j], y_pos[j]+0.28,
                        f"[{lo_str}, {hi_str}]",
                        fontsize=7, color="#333", va="bottom")

        plt.tight_layout(pad=0.3)

        # 嵌入tkinter（不显示工具栏）
        canvas_widget = FigureCanvasTkAgg(fig, master=top_chart)
        canvas_widget.draw()
        canvas_widget.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)
        # 隐藏matplotlib导航工具栏
        try:
            canvas_widget.toolbar.pack_forget()
        except Exception:
            pass

    def _auto_save(self):
        """自动保存到程序同目录的autosave文件"""
        if not self.entries_built:
            return
        try:
            import os
            save_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(save_dir, f"autosave_{self.title_text}.json")
            c, A, b, rels = self._get_data()
            data = {"title": self.title_text,
                    "n_vars": self.n_vars.get(), "n_cons": self.n_cons.get(),
                    "obj_type": self.obj_type.get(),
                    "c": c, "A": A, "b": b, "rels": rels}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 自动保存失败不提示

    def _prompt_auto_load(self):
        """点击恢复历史按钮时加载上次数据"""
        try:
            import os
            save_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(save_dir, f"autosave_{self.title_text}.json")
            if not os.path.exists(path):
                messagebox.showinfo("恢复历史", "暂无历史数据")
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.n_vars.set(data["n_vars"])
            self.n_cons.set(data["n_cons"])
            self.obj_type.set(data.get("obj_type", "最大化"))
            self.entries_built = False
            self._build_table()
            for j, v in enumerate(data["c"]):
                self.obj_entries[j].delete(0, "end")
                self.obj_entries[j].insert(0, str(v))
            for i in range(data["n_cons"]):
                for j, v in enumerate(data["A"][i]):
                    self.con_entries[i][j].delete(0, "end")
                    if v != 0:
                        self.con_entries[i][j].insert(0, str(v))
                self.rhs_entries[i].delete(0, "end")
                self.rhs_entries[i].insert(0, str(data["b"][i]))
                self.rel_vars[i].set(data["rels"][i])
            # 同步刷新表达式框，避免重复解析
            self._table_to_expr()
            messagebox.showinfo("恢复历史", "历史数据已恢复")
        except Exception as e:
            messagebox.showerror("恢复失败", str(e))

    def _save(self):
        if not self.entries_built:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")],
            title="存盘")
        if not path:
            return
        c, A, b, rels = self._get_data()
        data = {"title": self.title_text,
                "n_vars": self.n_vars.get(), "n_cons": self.n_cons.get(),
                "obj_type": self.obj_type.get(),
                "c": c, "A": A, "b": b, "rels": rels}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("存盘", f"已保存到 {path}")

    def _load(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json")],
            title="导入")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.n_vars.set(data["n_vars"])
        self.n_cons.set(data["n_cons"])
        self.obj_type.set(data["obj_type"])
        self._build_table()
        for j, v in enumerate(data["c"]):
            self.obj_entries[j].delete(0, "end")
            self.obj_entries[j].insert(0, str(v))
        for i in range(data["n_cons"]):
            for j, v in enumerate(data["A"][i]):
                self.con_entries[i][j].delete(0, "end")
                if v != 0:
                    self.con_entries[i][j].insert(0, str(v))
            self.rhs_entries[i].delete(0, "end")
            self.rhs_entries[i].insert(0, str(data["b"][i]))
            self.rel_vars[i].set(data["rels"][i])
        messagebox.showinfo("导入", "数据导入成功")


# ══════════════════════════════════════════════════════
#  运输问题求解页
# ══════════════════════════════════════════════════════
class TransportPage(tk.Frame, _TableEditMixin):
    def __init__(self, master, controller, mode="平衡"):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.mode = mode  # 平衡/产大于销/销大于产/指派
        self.n_src = tk.IntVar(value=3)
        self.n_dst = tk.IntVar(value=3)
        self.entries_built = False
        self._build_header()

    def _build_header(self):
        title_map = {
            "平衡": "产销平衡问题", "产大于销": "产大于销问题",
            "销大于产": "销大于产问题", "指派": "指派问题"
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
            tk.Label(ctrl, text="销地数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left", padx=(8,0))
            tk.Spinbox(ctrl, from_=1, to=15, textvariable=self.n_dst, width=4,
                       font=FONT_SMALL).pack(side="left", padx=4)

        make_btn(hdr, "确  定", self._build_table, bg=BTN_GREEN, width=8).pack(side="left", padx=6)
        make_btn(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=4)
        make_btn(hdr, "返  回", self.controller.show_menu, bg=BTN_GRAY, width=8).pack(side="left", padx=4)

        # ── 表达式输入区 ──
        expr_frame = tk.Frame(self, bg="#f0ece4", relief="groove", bd=1)
        expr_frame.pack(fill="x", padx=10, pady=(4, 0))
        expr_top = tk.Frame(expr_frame, bg="#f0ece4")
        expr_top.pack(fill="x", padx=6, pady=(4, 2))
        tk.Label(expr_top, text="模型表达式（输入或粘贴）:",
                 bg="#f0ece4", font=("宋体", 9, "bold")).pack(side="left")
        tk.Button(expr_top, text="解析填入表格", command=self._expr_to_table,
                  bg="#90ee90", font=("宋体", 9), relief="raised", width=12).pack(side="left", padx=6)
        tk.Button(expr_top, text="从表格刷新", command=self._table_to_expr,
                  bg="#87ceeb", font=("宋体", 9), relief="raised", width=10).pack(side="left", padx=2)
        tk.Button(expr_top, text="清  空",
                  command=lambda: self.expr_text.delete("1.0", "end"),
                  bg="#ffcccc", font=("宋体", 9), relief="raised", width=6).pack(side="left", padx=2)
        self.expr_text = tk.Text(expr_frame, font=("Consolas", 10), bg="#fffff0",
                                 relief="sunken", bd=1, height=4)
        self.expr_text.pack(fill="x", padx=6, pady=(0, 4))
        if self.mode == "指派":
            _placeholder = "# 费用矩阵（每行一个工人，空格分隔）\n3 2 4\n5 3 6\n8 7 2"
        else:
            _placeholder = "# 费用矩阵（每行一个产地，空格分隔）\n3 2 4\n5 3 6\n产量: 100 150\n销量: 80 90 80"
        self.expr_text.insert("1.0", _placeholder)

        self.body = tk.Frame(self, bg="#f5f0e8")
        self.body.pack(fill="both", expand=True, padx=10, pady=6)

    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        m = self.n_src.get()
        n = self.n_dst.get() if self.mode != "指派" else m

        # 费用矩阵
        tk.Label(self.body, text="费用矩阵 (单位运费)", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).grid(
                 row=0, column=0, sticky="w", columnspan=n+2)

        for j in range(n):
            lbl = "任务" if self.mode == "指派" else f"销地{j+1}"
            tk.Label(self.body, text=lbl, bg="#ffe0b2", font=FONT_SMALL,
                     relief="ridge", width=8).grid(row=1, column=j+2, padx=1, pady=1)

        if self.mode != "指派":
            tk.Label(self.body, text="产量", bg="#ffe0b2", font=FONT_SMALL,
                     relief="ridge", width=8).grid(row=1, column=n+2, padx=2)

        self.cost_entries = []
        self.supply_entries = []
        for i in range(m):
            lbl = f"工人{i+1}" if self.mode == "指派" else f"产地{i+1}"
            tk.Label(self.body, text=lbl, bg="#f5f0e8",
                     font=FONT_SMALL).grid(row=i+2, column=1, padx=4)
            row_e = []
            for j in range(n):
                e = tk.Entry(self.body, width=8, font=FONT_SMALL, bg="#e8f5e9")
                e.grid(row=i+2, column=j+2, padx=1, pady=0)
                self._bind_cell(e, i, j)
                e.bind("<Control-v>", lambda ev, r=i, c=j: self._paste_from_clipboard(ev, r, c, "cost"))
                row_e.append(e)
            self.cost_entries.append(row_e)
            if self.mode != "指派":
                se = tk.Entry(self.body, width=8, font=FONT_SMALL, bg="#fff9c4")
                se.grid(row=i+2, column=n+2, padx=1, pady=0)
                self._bind_cell(se, i, n)
                se.bind("<Control-v>", lambda ev, r=i: self._paste_from_clipboard(ev, r, 0, "supply"))
                self.supply_entries.append(se)

        self.demand_entries = []
        if self.mode != "指派":
            tk.Label(self.body, text="销量", bg="#f5f0e8",
                     font=FONT_SMALL).grid(row=m+2, column=1, padx=2)
            for j in range(n):
                de = tk.Entry(self.body, width=8, font=FONT_SMALL, bg="#e3f2fd")
                de.grid(row=m+2, column=j+2, padx=1, pady=0)
                self._bind_cell(de, m, j)
                de.bind("<Control-v>", lambda ev, c=j: self._paste_from_clipboard(ev, 0, c, "demand"))
                self.demand_entries.append(de)

        self.result_text = tk.Text(self.body, height=8, width=60,
                                   font=FONT_SMALL, bg="#fffde7")
        self.result_text.grid(row=m+4, column=1, columnspan=n+3, pady=8, sticky="w")
        self.entries_built = True

    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        try:
            from scipy.optimize import linear_sum_assignment
            import numpy as np
            m = self.n_src.get()
            n = self.n_dst.get() if self.mode != "指派" else m

            BIG_M = 1e7  # 大M法禁止路线用极大值代替
            def _parse_cost(s):
                s = s.strip()
                if not s: return 0.0
                if s.upper() == 'M': return BIG_M
                return float(s)
            cost = np.array([[_parse_cost(self.cost_entries[i][j].get())
                               for j in range(n)] for i in range(m)])

            if self.mode == "指派":
                row_ind, col_ind = linear_sum_assignment(cost)
                total = cost[row_ind, col_ind].sum()
                self.result_text.delete("1.0", "end")
                self.result_text.insert("end", f"最优指派方案（最小总费用 = {total:.2f}）\n\n")
                for i, j in zip(row_ind, col_ind):
                    self.result_text.insert("end", f"  工人{i+1} → 任务{j+1}  费用={cost[i,j]}\n")
                return

            supply = np.array([float(self.supply_entries[i].get() or 0) for i in range(m)])
            demand = np.array([float(self.demand_entries[j].get() or 0) for j in range(n)])

            # 处理不平衡（无论何种模式，只要供需不等则自动补虚拟行/列）
            total_s, total_d = supply.sum(), demand.sum()
            if total_s > total_d:
                demand = np.append(demand, total_s - total_d)
                cost   = np.hstack([cost, np.zeros((m, 1))])
                n += 1
            elif total_d > total_s:
                supply = np.append(supply, total_d - total_s)
                cost   = np.vstack([cost, np.zeros((1, n))])
                m += 1

            self._solve_transport(cost, supply, demand,
                                  self.n_src.get(), self.n_dst.get() if self.mode != "指派" else m)
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))

    def _populate_table(self, cost_matrix, supply, demand):
        """重建表格并填入费用矩阵、产量、销量数据"""
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

    def _cell_value(self, r, c):
        """获取逻辑坐标 (r,c) 处单元格的值（alias for _cell_value_at）"""
        return self._cell_value_at(r, c)

    def _entry_frame(self):
        return self.body

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
        if r < m and c < n:  return "#e8f5e9"
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

    def _paste_from_clipboard(self, event, start_r=0, start_c=0, area="cost"):
        """Ctrl+V 从剪贴板粘贴 TSV/多行数据到表格（兼容 Excel 完整表格含标题）"""
        try:
            text = self.body.clipboard_get()
        except Exception:
            return None
        # 单值：手动插入（保持正常粘贴语义）
        if '\t' not in text and '\n' not in text.strip():
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

        raw_rows = [ln.split('\t') for ln in text.strip().splitlines() if ln.strip()]
        if not raw_rows:
            return "break"

        # 自动跳过标题行（首行含非数字非空单元格）
        skip_row = 0
        if any(not _is_num(c) and c.strip() for c in raw_rows[0]):
            skip_row = 1

        # 自动跳过标签列（各数据行首列含非数字非空）
        skip_col = 0
        for row in raw_rows[skip_row:]:
            if row and not _is_num(row[0]) and row[0].strip():
                skip_col = 1
                break

        # 提取纯数字数据块
        data = []
        for row in raw_rows[skip_row:]:
            cells = [row[ci] for ci in range(skip_col, len(row))]
            data.append(cells)

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
        else:  # cost
            # 检测需求行：
            # 1) 末行产量列为空而前一行非空
            # 2) 末行原始标签含"用量"/"销量"/"demand"等关键词
            demand_row_idx = None
            if (self.mode != "指派" and start_r == 0 and start_c == 0
                    and len(data) > 1):
                last = data[-1]
                prev = data[-2]
                last_supply = last[-1].strip() if len(last) > n else ""
                prev_supply = prev[-1].strip() if len(prev) > n else ""
                supply_match = (last_supply == "" and prev_supply != "")
                # 检查末行原始标签
                last_label = ""
                if skip_col == 1 and raw_rows:
                    last_raw = raw_rows[skip_row + len(data) - 1]
                    last_label = last_raw[0].strip() if last_raw else ""
                label_match = any(kw in last_label
                                  for kw in ["用量", "销量", "需求", "demand", "Demand"])
                if supply_match or label_match:
                    demand_row_idx = len(data) - 1

            # 整表粘贴时自动校正产地数/销地数（防止 m×n 设反导致数据错位）
            if (start_r == 0 and start_c == 0 and self.mode != "指派"
                    and demand_row_idx is not None):
                n_cost_rows = demand_row_idx          # 产地行数 = 销量行之前的行数
                # 判断是否含供应量列：末行末格空、其余行末格均为有效数值
                d_last = data[demand_row_idx][-1].strip() if data[demand_row_idx] else ""
                c_lasts = [data[ri][-1].strip() for ri in range(n_cost_rows) if data[ri]]
                has_supply_col = (not d_last and bool(c_lasts)
                                  and all(_is_num(v) and v for v in c_lasts))
                new_m = n_cost_rows
                new_n = (len(data[0]) - 1) if has_supply_col else len(data[0])
                if new_m > 0 and new_n > 0 and (new_m != m or new_n != n):
                    self.n_src.set(new_m)
                    self.n_dst.set(new_n)
                    self._build_table()
                    m, n = new_m, new_n

            for ri, row in enumerate(data):
                r = start_r + ri
                if demand_row_idx is not None and ri == demand_row_idx:
                    # 销量行：先清空全部销量格，再填入（防止旧数据残留）
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

    def _solve_transport(self, cost, supply, demand, orig_m, orig_n):
        from scipy.optimize import linprog
        import numpy as np
        m, n = cost.shape
        c = cost.flatten()
        # 等式约束：每行之和=supply, 每列之和=demand
        A_eq = []
        b_eq = []
        for i in range(m):
            row = [0]*(m*n)
            for j in range(n):
                row[i*n+j] = 1
            A_eq.append(row); b_eq.append(supply[i])
        for j in range(n):
            row = [0]*(m*n)
            for i in range(m):
                row[i*n+j] = 1
            A_eq.append(row); b_eq.append(demand[j])

        res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=[(0,None)]*(m*n), method="highs")
        self.result_text.delete("1.0", "end")
        if res.success:
            x = res.x.reshape(m, n)
            self.result_text.insert("end", f"最优运输方案  最小总费用 = {res.fun:.2f}")
            self._show_lp_result(
                cost[:orig_m, :orig_n],
                [float(supply[i]) for i in range(orig_m)],
                [float(demand[j]) for j in range(orig_n)],
                x[:orig_m, :orig_n],
                res.fun
            )
        else:
            self.result_text.insert("end", f"求解失败：{res.message}")

    def _show_lp_result(self, cost_orig, supply, demand, x_opt, opt_val):
        """以 LP 表格形式展示运输问题求解结果（精确仿线性规划图2样式）"""
        if hasattr(self, '_lp_result_frame') and self._lp_result_frame.winfo_exists():
            self._lp_result_frame.destroy()

        # 过滤零产量虚拟产地行（为不平衡问题自动补的虚拟产地）
        real_src = [i for i in range(len(supply)) if supply[i] > 0] or list(range(len(supply)))
        n = len(demand)
        m = len(real_src)
        total_vars = m * n
        total_cons = m + n

        c_flat = [float(cost_orig[i][j]) for i in real_src for j in range(n)]
        x_flat = [float(x_opt[i][j])     for i in real_src for j in range(n)]
        supply_f = [supply[i] for i in real_src]

        A, b_vec, rels = [], [], []
        for ii in range(m):
            row = [0] * total_vars
            for j in range(n):  row[ii * n + j] = 1
            A.append(row); b_vec.append(supply_f[ii]); rels.append("=")
        for j in range(n):
            row = [0] * total_vars
            for ii in range(m):  row[ii * n + j] = 1
            A.append(row); b_vec.append(demand[j]); rels.append("=")

        HDR  = "#ffff99"
        RHS  = "#ffcccc"
        OPT  = "#b0d0ff"
        BG   = "#f5f0e8"
        W    = 7

        def L(p, text, bg, font=("宋体", 10), **kw):
            return tk.Label(p, text=text, bg=bg, font=font, relief="ridge", **kw)

        outer = tk.Frame(self.body, bg=BG, relief="groove", bd=1)
        # row offset: input table uses rows 0..(m+n+3), result goes below
        outer.grid(row=m + n + 5, column=0,
                   columnspan=n + 6, pady=6, sticky="w", padx=2)
        self._lp_result_frame = outer

        r = 0
        tk.Label(outer, text="目标函数系数", bg=BG,
                 font=("宋体", 10, "bold")).grid(
                 row=r, column=0, sticky="w",
                 columnspan=total_vars + 5, padx=4, pady=(4, 0))
        r += 1

        # 变量名行（无右侧列标题）
        tk.Label(outer, text="", bg=BG, width=3, relief="flat").grid(row=r, column=0)
        for k in range(total_vars):
            L(outer, xname(k), HDR, width=W).grid(row=r, column=k+1, padx=1, pady=1)
        r += 1

        # 目标函数系数行 + 右侧列标题（图2：标题与系数同行）
        tk.Label(outer, text="", bg=BG, width=3, relief="flat").grid(row=r, column=0)
        for k in range(total_vars):
            v = c_flat[k]
            L(outer, str(int(v) if v == int(v) else v), HDR, width=W).grid(
                row=r, column=k+1, padx=1, pady=1)
        L(outer, "约束条件实际值", RHS, width=14).grid(row=r, column=total_vars+1, padx=1, pady=1)
        L(outer, "约束关系",       RHS, width=8 ).grid(row=r, column=total_vars+2, padx=1, pady=1)
        L(outer, "约束条件常数项", RHS, width=14).grid(row=r, column=total_vars+3, padx=1, pady=1)
        r += 1

        tk.Label(outer, text="约束条件系数", bg=BG,
                 font=("宋体", 10, "bold")).grid(
                 row=r, column=0, sticky="w",
                 columnspan=total_vars + 5, padx=4, pady=(6, 0))
        r += 1

        for ci in range(total_cons):
            L(outer, str(ci+1), HDR, width=3).grid(row=r, column=0, padx=1, pady=1)
            for k in range(total_vars):
                v = A[ci][k]
                # 不区分0/1颜色，统一白底，与图2一致
                L(outer, str(int(v)) if v else "", "#ffffff",
                  width=W).grid(row=r, column=k+1, padx=1, pady=1)
            actual = sum(A[ci][k] * x_flat[k] for k in range(total_vars))
            a_str = str(int(round(actual)) if abs(actual - round(actual)) < 1e-6 else f"{actual:.2f}")
            b_str = str(int(b_vec[ci]) if b_vec[ci] == int(b_vec[ci]) else b_vec[ci])
            L(outer, a_str,   RHS, width=14).grid(row=r, column=total_vars+1, padx=1, pady=1)
            L(outer, rels[ci],RHS, width=8 ).grid(row=r, column=total_vars+2, padx=1, pady=1)
            L(outer, b_str,   RHS, width=14).grid(row=r, column=total_vars+3, padx=1, pady=1)
            r += 1

        # 最优解：标签黄色（同行号），数值蓝色，最优值粉色（同右侧列）
        L(outer, "最优解", HDR, font=("宋体", 10, "bold"), width=3).grid(
            row=r, column=0, padx=1, pady=(6, 2))
        for k in range(total_vars):
            v = x_flat[k]
            txt = str(int(round(v)) if abs(v - round(v)) < 1e-6 else round(v, 2))
            L(outer, txt, OPT, width=W).grid(row=r, column=k+1, padx=1, pady=(6, 2))
        opt_str = str(int(round(opt_val)) if abs(opt_val - round(opt_val)) < 1 else f"{opt_val:.2f}")
        L(outer, f"最优值\n{opt_str}", RHS,
          font=("宋体", 10, "bold"), width=14).grid(
          row=r, column=total_vars+3, padx=1, pady=(6, 2))

    def _expr_to_table(self):
        """从表达式文本解析费用矩阵/产量/销量，自动填入表格"""
        import re
        try:
            raw = self.expr_text.get("1.0", "end").strip()
            # LP 格式（含 min/max 目标函数）走专用解析
            if re.search(r'^\s*(min|max)\b', raw, re.I | re.M):
                self._parse_lp_to_table(raw)
                return
            lines = [l.strip() for l in raw.split("\n")
                     if l.strip() and not l.strip().startswith("#")]

            supply, demand, cost_rows = [], [], []
            for line in lines:
                if re.match(r"产量\s*[:：]", line):
                    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+",
                                      re.split(r"[:：]", line, 1)[-1])
                    supply = [float(x) for x in nums]
                elif re.match(r"销量\s*[:：]", line):
                    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+",
                                      re.split(r"[:：]", line, 1)[-1])
                    demand = [float(x) for x in nums]
                else:
                    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", line)
                    if nums:
                        cost_rows.append([float(x) for x in nums])

            if not cost_rows:
                messagebox.showwarning("解析失败", "未找到费用矩阵数据（请每行填写一个产地的运费，空格分隔）")
                return

            m = len(cost_rows)
            n = max(len(r) for r in cost_rows)

            self._populate_table(cost_rows, supply, demand)

            detail = f"已解析：{m}×{n} 费用矩阵"
            if supply: detail += f"，产量 {[int(v) if v==int(v) else v for v in supply]}"
            if demand: detail += f"，销量 {[int(v) if v==int(v) else v for v in demand]}"
            messagebox.showinfo("解析成功", detail)

        except Exception as e:
            messagebox.showerror("解析错误", str(e))

    def _parse_lp_to_table(self, raw):
        """解析 LP 格式运输问题表达式，自动推断 m×n 并填入表格"""
        import re
        # 全角符号统一为 ASCII
        raw = _normalize_expr(raw)

        lines = [l.strip() for l in raw.split("\n") if l.strip()]

        def parse_poly(s):
            s = s.strip().replace(" ", "")
            if s and s[0] not in "+-":
                s = "+" + s
            coefs = {}
            for m in re.finditer(r"([+-])([0-9.]*)[xX]([0-9]+)", s):
                sign = 1 if m.group(1) == "+" else -1
                c_str = m.group(2)
                coefs[int(m.group(3)) - 1] = sign * (float(c_str) if c_str else 1.0)
            return coefs

        # 目标函数
        obj_line = next((l for l in lines if re.match(r"(min|max)\b", l, re.I)), None)
        if not obj_line:
            messagebox.showwarning("解析失败", "找不到目标函数行（需含 min 或 max）")
            return
        obj_part = re.sub(r"^(min|max)\s*\w?\s*=\s*", "", obj_line, flags=re.I)
        cost_coefs = parse_poly(obj_part)
        if not cost_coefs:
            messagebox.showwarning("解析失败", "目标函数解析失败，请检查变量格式（x1,x2,...）")
            return
        total_vars = max(cost_coefs.keys()) + 1

        # 等式约束（跳过目标行和注释行；s.t. 前缀只剥离，不丢弃整行）
        eq_cons = []
        for line in lines:
            if re.match(r"(min|max)\b", line, re.I): continue
            if line.startswith("#"): continue
            # 剥离 s.t. 前缀，保留同行约束内容
            line = re.sub(r"^s\.?\s*t\.?\s*", "", line, flags=re.I).strip()
            if not line: continue
            lc = line.replace(" ", "")
            # 跳过非负约束行（xi>=0 等）
            if re.match(r"x[^0-9]*[0-9,，…\s]*\s*>=?\s*0", lc, re.I): continue
            if "=" not in lc or ">=" in lc or "<=" in lc: continue
            parts = lc.split("=", 1)
            var_set = sorted({int(m.group(1)) - 1
                              for m in re.finditer(r"[xX]([0-9]+)", parts[0])})
            if not var_set: continue
            try:
                rhs = float(parts[1])
                eq_cons.append((var_set, rhs))
            except ValueError:
                pass

        if not eq_cons:
            messagebox.showwarning("解析失败", "未找到等式约束")
            return

        # 区分供应约束（连续变量）与需求约束（等步长变量）
        supply_cons, demand_cons, n_detected = [], [], None
        for var_set, rhs in eq_cons:
            if len(var_set) < 2:
                supply_cons.append((var_set, rhs))   # 单变量暂归入供应
                continue
            diffs = [var_set[k+1] - var_set[k] for k in range(len(var_set) - 1)]
            if all(d == 1 for d in diffs):            # 连续 → 供应约束
                supply_cons.append((var_set, rhs))
                if n_detected is None:
                    n_detected = len(var_set)
            elif len(set(diffs)) == 1:                # 等步长 → 需求约束
                demand_cons.append((var_set, rhs))

        # 推断 n（销地数）
        if n_detected is None:
            if demand_cons:
                n_detected = len(demand_cons)         # 需求约束数 = n
            else:
                messagebox.showwarning("解析失败", "无法推断销地数，请检查约束格式")
                return
        n = n_detected
        m_src = total_vars // n if total_vars % n == 0 else len(supply_cons)

        # 构造费用矩阵
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
        """从当前表格生成表达式填入文本框"""
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成表格")
            return
        try:
            m = self.n_src.get()
            n = self.n_dst.get() if self.mode != "指派" else m
            lines = []
            if self.mode == "指派":
                lines.append("# 费用矩阵（每行一个工人，空格分隔）")
            else:
                lines.append("# 费用矩阵（每行一个产地，空格分隔）")
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


# ══════════════════════════════════════════════════════
#  决策分析页（最大最小/最大最大/后悔值/期望值）
# ══════════════════════════════════════════════════════
class DecisionPage(tk.Frame, _TableEditMixin):
    def __init__(self, master, controller, mode="最大最小准则"):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.mode = mode
        self.n_alt = tk.IntVar(value=3)   # 方案数
        self.n_state = tk.IntVar(value=3) # 自然状态数
        self.entries_built = False
        self._build_header()

    def _build_header(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"运筹学模型求解系统———{self.mode}",
                 font=("微软雅黑", 13, "bold"), bg="#d7ccc8").pack(side="left", padx=10, pady=6)
        ctrl = tk.Frame(hdr, bg="#d7ccc8")
        ctrl.pack(side="left", padx=10)
        tk.Label(ctrl, text="方案数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left")
        tk.Spinbox(ctrl, from_=2, to=15, textvariable=self.n_alt, width=4,
                   font=FONT_SMALL).pack(side="left", padx=4)
        tk.Label(ctrl, text="自然状态数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left", padx=(8,0))
        tk.Spinbox(ctrl, from_=2, to=15, textvariable=self.n_state, width=4,
                   font=FONT_SMALL).pack(side="left", padx=4)
        make_btn(hdr, "确  定", self._build_table, bg=BTN_GREEN, width=8).pack(side="left", padx=6)
        make_btn(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=4)
        make_btn(hdr, "返  回", self.controller.show_menu, bg=BTN_GRAY, width=8).pack(side="left", padx=4)
        self.body = tk.Frame(self, bg="#f5f0e8")
        self.body.pack(fill="both", expand=True, padx=10, pady=6)
        self._build_table()

    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            if r == 0 and hasattr(self, 'prob_entries') and c < len(self.prob_entries):
                return self.prob_entries[c]
            if r >= 1 and hasattr(self, 'mat_entries') and r-1 < len(self.mat_entries):
                row = self.mat_entries[r-1]
                if c < len(row):
                    return row[c]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        if r == 0: return "#fce4ec"
        return "#e8f5e9"

    def _all_entries(self):
        try:
            if hasattr(self, 'prob_entries'):
                for j, e in enumerate(self.prob_entries):
                    yield (0, j, e)
            if hasattr(self, 'mat_entries'):
                for i, row in enumerate(self.mat_entries):
                    for j, e in enumerate(row):
                        yield (i+1, j, e)
        except AttributeError:
            return

    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        m = self.n_alt.get()
        n = self.n_state.get()

        main = tk.PanedWindow(
            self.body,
            orient="horizontal",
            bg="#c8b89a",
            sashwidth=8,
            sashrelief="raised",
            bd=0,
        )
        main.pack(fill="both", expand=True)

        work = tk.Frame(main, bg="#f8f4eb", relief="groove", bd=1)
        guide = tk.Frame(main, bg="#fffaf0", relief="groove", bd=1)
        main.add(work, minsize=520, stretch="always")
        main.add(guide, minsize=520, stretch="always")
        self._decision_sash_initialized = False

        def init_sash(_event=None):
            if self._decision_sash_initialized:
                return
            width = main.winfo_width()
            if width > 1040:
                main.sash_place(0, width // 2, 0)
                self._decision_sash_initialized = True

        main.bind("<Configure>", init_sash)
        main.after_idle(init_sash)
        self._build_guide_panel(guide)

        tk.Label(work, text="收益矩阵", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.prob_entries = []
        for j in range(n):
            tk.Label(work, text=f"状态{j+1}", bg="#ffe0b2",
                     font=FONT_SMALL, relief="ridge", width=8).grid(row=1, column=j+2, padx=2)
        if self.mode == "期望值准则":
            tk.Label(work, text="概率", bg="#ffe0b2",
                     font=FONT_SMALL, relief="ridge", width=8).grid(row=2, column=1)
            for j in range(n):
                pe = tk.Entry(work, width=8, font=FONT_SMALL, bg="#fce4ec")
                pe.insert(0, f"{1/n:.3f}")
                pe.grid(row=2, column=j+2, padx=2)
                self._bind_cell(pe, 0, j)
                self.prob_entries.append(pe)

        if self.mode == "乐观系数准则":
            alpha_frame = tk.Frame(work, bg="#f5f0e8")
            alpha_frame.grid(row=2, column=1, columnspan=n+2, sticky="w", pady=4)
            tk.Label(alpha_frame, text="乐观系数 α (0~1，越大越乐观):",
                     bg="#f5f0e8", font=FONT_SMALL).pack(side="left")
            self.alpha_var = tk.DoubleVar(value=0.6)
            tk.Scale(alpha_frame, variable=self.alpha_var, from_=0, to=1,
                     resolution=0.05, orient="horizontal", length=200,
                     bg="#f5f0e8", font=FONT_SMALL).pack(side="left", padx=8)
            tk.Label(alpha_frame, textvariable=self.alpha_var,
                     bg="#f5f0e8", font=FONT_SMALL, width=5).pack(side="left")

        self.mat_entries = []
        start_row = 3 if self.mode == "期望值准则" else 2
        for i in range(m):
            tk.Label(work, text=f"方案{i+1}", bg="#f5f0e8",
                     font=FONT_SMALL).grid(row=start_row+i, column=1, padx=4)
            row_e = []
            for j in range(n):
                e = tk.Entry(work, width=8, font=FONT_SMALL, bg="#e8f5e9")
                e.grid(row=start_row+i, column=j+2, padx=2, pady=1)
                self._bind_cell(e, i+1, j)
                row_e.append(e)
            self.mat_entries.append(row_e)

        self.result_frame = tk.Frame(work, bg="#f8f4eb")
        self.result_frame.grid(row=start_row+m+1, column=0, columnspan=n+3,
                               pady=14, sticky="w")
        self.result_text = None
        self.entries_built = True

    def _build_guide_panel(self, parent):
        spec = self._guide_content()

        head = tk.Frame(parent, bg="#fffaf0")
        head.pack(fill="x", padx=16, pady=(14, 10))
        tk.Label(head, text="准则定义与计算提示", bg="#fffaf0", fg="#9b1c1c",
                 font=("微软雅黑", 16, "bold")).pack(anchor="w")
        self._create_formula_canvas(head, spec).pack(fill="x")

        body_wrap = tk.Frame(parent, bg="#fffaf0")
        body_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        scrollbar = tk.Scrollbar(body_wrap)
        scrollbar.pack(side="right", fill="y")

        text = tk.Text(
            body_wrap,
            yscrollcommand=scrollbar.set,
            bg="#fffaf0",
            fg="#1c2328",
            font=("微软雅黑", 12),
            relief="flat",
            wrap="word",
            spacing1=5,
            spacing3=8,
        )
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)

        text.tag_config("section", foreground="#9b1c1c", font=("微软雅黑", 13, "bold"))
        text.tag_config("subhead", foreground="#0b2a78", font=("微软雅黑", 12, "bold"))
        text.tag_config("formula", foreground="#0a217f", font=("Consolas", 11, "bold"))
        text.tag_config("body", foreground="#1c2328", font=("微软雅黑", 11))
        text.insert("end", spec["body"] + "\n\n", "body")
        text.insert("end", "相关概念速览\n", "section")
        for name, ref_formula, summary in spec["refs"]:
            text.insert("end", f"{name}\n", "subhead")
            text.insert("end", f"  {ref_formula}\n", "formula")
            text.insert("end", f"  {summary}\n\n", "body")
        text.config(state="disabled")
        self.guide_text = text

    def _create_formula_canvas(self, parent, spec):
        canvas = tk.Canvas(parent, height=180, bg="#fff2c6",
                           highlightthickness=1, highlightbackground="#b8a97d")

        def draw(_event=None):
            canvas.delete("all")
            w = max(canvas.winfo_width(), 420)
            red = "#e21a1a"
            blue = "#211486"
            scale = min(max(w / 720, 0.62), 1.0)
            left = 22
            canvas.create_text(left, 24, anchor="w", text=spec["model_title"],
                               fill=red, font=("微软雅黑", 16, "bold"))

            for item in spec["formula_items"]:
                kind = item[0]
                if kind == "text":
                    _, x, y, text, font_size = item
                    canvas.create_text(left + x * scale, y, anchor="w",
                                       text=text, fill=blue,
                                       font=("Times New Roman", max(14, int(font_size * scale)), "italic"))
                elif kind == "sub":
                    _, x, y, text = item
                    canvas.create_text(left + x * scale, y, anchor="w",
                                       text=text, fill=blue,
                                       font=("Times New Roman", max(8, int(12 * scale))))
                elif kind == "line":
                    _, x1, y1, x2, y2 = item
                    canvas.create_line(left + x1 * scale, y1, left + x2 * scale, y2,
                                       fill=blue, width=2)

        canvas.bind("<Configure>", draw)
        return canvas

    def _guide_content(self):
        def model(title, model_title, formula_items, body):
            return {
                "title": title,
                "model_title": model_title,
                "formula_items": formula_items,
                "body": body,
            }

        guides = {
            "最大最小准则": model(
                "最大最小准则",
                "最大最小准则数学表述模型",
                [
                    ("text", 0, 95, "Z = max [ min ( aij ) ]", 30),
                    ("sub", 98, 125, "1<=i<=n"),
                    ("sub", 232, 125, "1<=j<=m"),
                ],
                "这个准则从最不利的角度看问题。"
                "先在每个方案所在行里找出最小收益，再从这些最小收益中选出最大值，"
                "最大值对应的方案就是最优方案。\n\n"
                "其中：a_ij 为收益表中第 i 个决策方案、"
                "第 j 个自然状态下的收益值。\n\n"
                "图中的红圈表示每个方案的最小收益，红箭头指向右侧最大的那个最小收益。\n\n"
                "计算步骤：\n"
                "1. 逐行寻找最小收益。\n"
                "2. 将每行最小收益列到右侧结果列。\n"
                "3. 在这些最小收益中取最大值。\n"
                "4. 对应方案即为最优行动方案。\n\n"
                "适用场景：风险偏保守，希望先保证最低收益。"
            ),
            "最大最大准则": model(
                "最大最大准则",
                "最大最大准则数学表述模型",
                [
                    ("text", 0, 95, "Z = max [ max ( aij ) ]", 30),
                    ("sub", 98, 125, "1<=i<=n"),
                    ("sub", 232, 125, "1<=j<=m"),
                ],
                "这个准则从最有利的角度看问题。"
                "先找每个方案的最大收益，再从这些最大收益中选择最大者。\n\n"
                "其中：a_ij 为收益表中第 i 个决策方案、"
                "第 j 个自然状态下的收益值。\n\n"
                "计算步骤：\n"
                "1. 逐行寻找最大收益。\n"
                "2. 比较各方案最大收益。\n"
                "3. 取其中最大的一个作为最优结果。\n\n"
                "适用场景：追求最好机会、偏乐观的决策。"
            ),
            "后悔值准则": model(
                "后悔值准则",
                "后悔值准则数学表述模型",
                [
                    ("text", 0, 78, "Z = min [ max ( a'ij ) ]", 27),
                    ("sub", 86, 107, "1<=i<=n"),
                    ("sub", 218, 107, "1<=j<=m"),
                    ("text", 32, 140, "a'ij = max ( aij ) - aij", 22),
                    ("sub", 138, 165, "1<=i<=n"),
                ],
                "先把收益矩阵转成后悔值矩阵。"
                "每个自然状态下，用该状态的最佳收益减去当前方案收益，得到后悔值，再比较各方案的最大后悔值。\n\n"
                "其中：a_ij 为原收益值，a'_ij 为后悔值。\n"
                "对每个自然状态 j，先找该列最大收益，再减去当前收益。\n\n"
                "计算步骤：\n"
                "1. 每个自然状态下找出最大收益。\n"
                "2. 用最大收益减去当前方案收益，得到后悔值。\n"
                "3. 每个方案取最大后悔值。\n"
                "4. 选择最大后悔值最小的方案。"
            ),
            "期望值准则": model(
                "期望值准则",
                "期望值准则数学表述模型",
                [
                    ("text", 0, 92, "Z = max [ E( Si ) ] = max [ Σ ( pj × aij ) ]", 23),
                    ("sub", 82, 119, "1<=i<=n"),
                    ("sub", 286, 119, "1<=i<=n"),
                    ("sub", 400, 128, "1<=j<=m"),
                ],
                "在自然状态概率已知时，计算每个方案的期望收益。"
                "概率越大，对结果的影响越大。\n\n"
                "其中：a_ij 为收益表中第 i 个决策方案、"
                "第 j 个自然状态下的收益值；p_j 为第 j 个自然状态的可能概率。\n\n"
                "计算步骤：\n"
                "1. 输入各自然状态概率。\n"
                "2. 每个方案按概率加权求和。\n"
                "3. 选择期望收益最大的方案。\n\n"
                "注意：概率应满足 Σp_j = 1。"
            ),
            "乐观系数准则": model(
                "乐观系数准则",
                "乐观系数准则数学表述模型",
                [
                    ("text", 0, 90, "Z = max [ α max(aij) + (1-α) min(aij) ]", 21),
                    ("sub", 78, 118, "1<=i<=n"),
                    ("sub", 180, 118, "1<=j<=m"),
                    ("sub", 365, 118, "1<=j<=m"),
                ],
                "用乐观系数 α 同时考虑最好收益和最坏收益。"
                "α 越大，越偏向乐观；α 越小，越偏向保守。\n\n"
                "其中：0<=α<=1。α=1 时为乐观准则，α=0 时为悲观准则。\n\n"
                "计算步骤：\n"
                "1. 每个方案找最大收益和最小收益。\n"
                "2. 按 H_i = α×最大收益 + (1-α)×最小收益 计算。\n"
                "3. 选择 H_i 最大的方案。"
            ),
            "等可能性准则": model(
                "等可能性准则",
                "等可能性准则数学表述模型",
                [
                    ("text", 0, 86, "Z = max [ E( Si ) ] = max [ Σ ( pj × aij ) ]", 23),
                    ("sub", 82, 113, "1<=i<=n"),
                    ("sub", 286, 113, "1<=i<=n"),
                    ("sub", 400, 122, "1<=j<=m"),
                    ("text", 300, 158, "pj = 1/m", 18),
                ],
                "在没有概率信息时，假设所有自然状态发生机会相同。"
                "每个方案取各状态收益的平均值，再比较平均收益大小。\n\n"
                "其中：a_ij 为收益表中第 i 个决策方案、"
                "第 j 个自然状态下的收益值；p_j 为各自然状态的相等概率。\n\n"
                "计算步骤：\n"
                "1. 对每个方案求各状态收益平均值。\n"
                "2. 比较各方案平均收益。\n"
                "3. 选择平均收益最大的方案。"
            ),
        }
        current = guides.get(self.mode, guides["最大最小准则"])
        refs = [
            ("最大最小准则", "Z = max(1<=i<=n)[min(1<=j<=m)(a_ij)]", "看最坏情况里最好的那个方案。"),
            ("最大最大准则", "Z = max(1<=i<=n)[max(1<=j<=m)(a_ij)]", "看最好情况里最好的那个方案。"),
            ("后悔值准则", "Z = min(1<=i<=n)[max(1<=j<=m)(a'_ij)]", "尽量减少选错后的最大后悔。"),
            ("期望值准则", "Z = max(1<=i<=n)[Σ(p_j*a_ij)]", "按给定概率加权，选择期望收益最大方案。"),
            ("乐观系数准则", "Z = max_i[α max_j(a_ij)+(1-α) min_j(a_ij)]", "在乐观和保守之间折中。"),
            ("等可能性准则", "Z = max(1<=i<=n)[Σ(p_j*a_ij)], p_j=1/m", "把各状态看成等概率事件。"),
        ]
        current["refs"] = refs
        return current

    def _clear_result(self):
        for child in self.result_frame.winfo_children():
            child.destroy()

    def _show_result_text(self, text):
        self._clear_result()
        self.result_text = tk.Text(self.result_frame, height=8, width=72,
                                   font=("微软雅黑", 11), bg="#fffde7",
                                   relief="ridge", bd=1)
        self.result_text.pack(anchor="w")
        self.result_text.insert("end", text)
        self.result_text.config(state="disabled")

    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        try:
            m = self.n_alt.get()
            n = self.n_state.get()
            mat = [[float(self.mat_entries[i][j].get() or 0)
                    for j in range(n)] for i in range(m)]

            if self.mode == "最大最小准则":
                scores = [min(row) for row in mat]
                best = max(scores)
                idx = scores.index(best)
                self._draw_maximin_result(mat, scores, best, idx)

            elif self.mode == "最大最大准则":
                scores = [max(row) for row in mat]
                best = max(scores)
                idx = scores.index(best)
                lines = ["各方案最大收益："]
                for i, s in enumerate(scores):
                    lines.append(f"  方案{i+1}: {s}")
                lines.append(f"\n最优方案: 方案{idx+1}，最大最大值 = {best}")
                self._show_result_text("\n".join(lines))

            elif self.mode == "后悔值准则":
                col_max = [max(mat[i][j] for i in range(m)) for j in range(n)]
                regret  = [[col_max[j]-mat[i][j] for j in range(n)] for i in range(m)]
                scores  = [max(row) for row in regret]
                best    = min(scores)
                idx     = scores.index(best)
                lines = ["后悔值矩阵："]
                for i, row in enumerate(regret):
                    lines.append(f"  方案{i+1}: {row}  最大后悔值={scores[i]}")
                lines.append(f"\n最优方案: 方案{idx+1}，最小最大后悔值 = {best}")
                self._show_result_text("\n".join(lines))

            elif self.mode == "期望值准则":
                probs = [float(self.prob_entries[j].get() or 0) for j in range(n)]
                ev = [sum(mat[i][j]*probs[j] for j in range(n)) for i in range(m)]
                best = max(ev)
                idx  = ev.index(best)
                lines = ["各方案期望值："]
                for i, v in enumerate(ev):
                    lines.append(f"  方案{i+1}: {v:.4f}")
                lines.append(f"\n最优方案: 方案{idx+1}，最大期望值 = {best:.4f}")
                self._show_result_text("\n".join(lines))

            elif self.mode == "乐观系数准则":
                # Hurwicz准则: H = α*max + (1-α)*min
                alpha = self.alpha_var.get()
                scores = [alpha*max(row) + (1-alpha)*min(row) for row in mat]
                best = max(scores)
                idx = scores.index(best)
                lines = [
                    f"乐观系数 α = {alpha}，(1-α) = {1-alpha:.2f}",
                    "",
                    "Hurwicz值 = α × 最大收益 + (1-α) × 最小收益",
                    "",
                ]
                for i, row in enumerate(mat):
                    h = scores[i]
                    lines.append(f"  方案{i+1}: α×{max(row)} + (1-α)×{min(row)} = {h:.4f}")
                lines.append(f"\n最优方案: 方案{idx+1}，Hurwicz值 = {best:.4f}")
                self._show_result_text("\n".join(lines))

            elif self.mode == "等可能性准则":
                # Laplace准则: 各自然状态概率相等 = 1/n
                p = 1.0 / n
                scores = [sum(row)*p for row in mat]
                best = max(scores)
                idx = scores.index(best)
                lines = [f"等可能性准则：假设各自然状态概率相等 = 1/{n} = {p:.4f}", ""]
                for i, row in enumerate(mat):
                    lines.append(f"  方案{i+1}: ({' + '.join(str(v) for v in row)}) × {p:.4f} = {scores[i]:.4f}")
                lines.append(f"\n最优方案: 方案{idx+1}，期望收益 = {best:.4f}")
                self._show_result_text("\n".join(lines))

        except ValueError as e:
            messagebox.showerror("输入错误", str(e))

    def _fmt_num(self, value):
        return str(int(value)) if float(value).is_integer() else f"{value:g}"

    def _draw_maximin_result(self, mat, scores, best, best_idx):
        self._clear_result()
        m = len(mat)
        n = len(mat[0]) if mat else 0
        left_w = 150
        cell_w = 92
        score_w = 230
        header_h = 76
        row_h = 46
        pad = 18
        table_w = left_w + n * cell_w + score_w
        table_h = header_h + m * row_h
        width = table_w + pad * 2
        height = table_h + 96

        canvas = tk.Canvas(self.result_frame, width=width, height=height,
                           bg="#fffdf1", highlightthickness=1,
                           highlightbackground="#b8b0a0")
        canvas.pack(anchor="w")

        navy = "#0b1d72"
        red = "#e21a1a"
        green = "#1eb34b"
        grid = "#333333"
        x0 = pad
        y0 = 54

        canvas.create_text(width // 2, 22, text=self.mode,
                           fill=red, font=("微软雅黑", 19, "bold"))

        for x in [x0, x0 + left_w] + [x0 + left_w + j * cell_w for j in range(1, n + 1)] + [x0 + table_w]:
            canvas.create_line(x, y0, x, y0 + table_h, fill=grid, width=1)
        for y in [y0, y0 + header_h] + [y0 + header_h + i * row_h for i in range(1, m + 1)]:
            canvas.create_line(x0, y, x0 + table_w, y, fill=grid, width=1)

        canvas.create_line(x0, y0, x0 + left_w, y0 + header_h, fill=grid, width=1)
        canvas.create_line(x0, y0 + 28, x0 + left_w, y0 + header_h, fill=grid, width=1)
        canvas.create_text(x0 + 52, y0 + 18, text="自然状态 Nⱼ",
                           fill=navy, font=("微软雅黑", 12, "bold"))
        canvas.create_text(x0 + 34, y0 + 48, text="aᵢⱼ",
                           fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(x0 + 62, y0 + 66, text="行动方案 Sᵢ",
                           fill=navy, font=("微软雅黑", 12, "bold"))

        for j in range(n):
            cx = x0 + left_w + j * cell_w + cell_w / 2
            canvas.create_text(cx, y0 + 30, text=f"N{j+1}",
                               fill=navy, font=("微软雅黑", 16, "bold"))
            canvas.create_text(cx, y0 + 58, text=f"状态{j+1}",
                               fill=navy, font=("微软雅黑", 10, "bold"))

        score_x = x0 + left_w + n * cell_w
        canvas.create_text(score_x + score_w / 2, y0 + 38,
                           text="Z = max [ min(aij) ]",
                           fill=navy, font=("Cambria Math", 15, "bold"))
        canvas.create_text(score_x + score_w / 2, y0 + 61,
                           text="1<=i<=n   1<=j<=m",
                           fill=navy, font=("Cambria Math", 10, "bold"))

        for i, row in enumerate(mat):
            y = y0 + header_h + i * row_h
            cy = y + row_h / 2
            canvas.create_text(x0 + 68, cy, text=f"S{i+1}（方案{i+1}）",
                               fill=navy, font=("微软雅黑", 12, "bold"))

            row_min = min(row)
            for j, value in enumerate(row):
                cx = x0 + left_w + j * cell_w + cell_w / 2
                canvas.create_text(cx, cy, text=self._fmt_num(value),
                                   fill=navy, font=("微软雅黑", 16, "bold"))
                if value == row_min:
                    canvas.create_oval(cx - 24, cy - 18, cx + 24, cy + 18,
                                       outline=red, width=3)

            score_text = self._fmt_num(scores[i])
            if i == best_idx:
                score_text = f"{score_text}（max）"
            canvas.create_text(score_x + score_w / 2 - 18, cy, text=score_text,
                               fill=green, font=("微软雅黑", 14, "bold"))
            if i == best_idx:
                canvas.create_line(score_x + score_w - 24, cy,
                                   score_x + score_w - 76, cy,
                                   fill=red, width=5, arrow=tk.LAST,
                                   arrowshape=(18, 20, 8))

        note_y = y0 + table_h + 28
        canvas.create_text(x0, note_y, anchor="w",
                           text=f"结论：最优方案为 方案{best_idx+1}，最大最小值 = {self._fmt_num(best)}",
                           fill="#9b1c1c", font=("微软雅黑", 12, "bold"))


# ══════════════════════════════════════════════════════
#  最短路求解页
# ══════════════════════════════════════════════════════
class ShortestPathPage(tk.Frame, _TableEditMixin):
    def __init__(self, master, controller):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.n_nodes = tk.IntVar(value=5)
        self.entries_built = False
        self._build_header()

    def _build_header(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        tk.Label(hdr, text="运筹学模型求解系统———最短路问题",
                 font=("微软雅黑", 13, "bold"), bg="#d7ccc8").pack(side="left", padx=10, pady=6)
        ctrl = tk.Frame(hdr, bg="#d7ccc8")
        ctrl.pack(side="left", padx=10)
        tk.Label(ctrl, text="节点数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left")
        tk.Spinbox(ctrl, from_=2, to=20, textvariable=self.n_nodes, width=4,
                   font=FONT_SMALL).pack(side="left", padx=4)
        make_btn(hdr, "确  定", self._build_table, bg=BTN_GREEN, width=8).pack(side="left", padx=6)
        make_btn(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=4)
        make_btn(hdr, "返  回", self.controller.show_menu, bg=BTN_GRAY, width=8).pack(side="left", padx=4)
        self.body = tk.Frame(self, bg="#f5f0e8")
        self.body.pack(fill="both", expand=True, padx=10, pady=6)

    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            if hasattr(self, 'dist_entries') and r < len(self.dist_entries) and c < len(self.dist_entries[r]):
                return self.dist_entries[r][c]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        return "#eeeeee" if r == c else "#e8f5e9"

    def _all_entries(self):
        try:
            if hasattr(self, 'dist_entries'):
                for i, row in enumerate(self.dist_entries):
                    for j, e in enumerate(row):
                        if i != j:  # skip readonly diagonal
                            yield (i, j, e)
        except AttributeError:
            return

    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        n = self.n_nodes.get()
        tk.Label(self.body, text="距离矩阵（无连接填 inf 或留空）",
                 bg="#f5f0e8", font=("微软雅黑", 10, "bold")).grid(row=0, column=0, columnspan=n+2, sticky="w")
        for j in range(n):
            tk.Label(self.body, text=f"节点{j+1}", bg="#ffe0b2",
                     font=FONT_SMALL, relief="ridge", width=7).grid(row=1, column=j+2, padx=2)
        self.dist_entries = []
        for i in range(n):
            tk.Label(self.body, text=f"节点{i+1}", bg="#f5f0e8",
                     font=FONT_SMALL).grid(row=i+2, column=1, padx=4)
            row_e = []
            for j in range(n):
                e = tk.Entry(self.body, width=7, font=FONT_SMALL,
                             bg="#eeeeee" if i==j else "#e8f5e9")
                if i == j:
                    e.insert(0, "0"); e.config(state="readonly")
                else:
                    self._bind_cell(e, i, j)
                e.grid(row=i+2, column=j+2, padx=2, pady=1)
                row_e.append(e)
            self.dist_entries.append(row_e)
        tk.Label(self.body, text="起点节点:", bg="#f5f0e8", font=FONT_SMALL).grid(
            row=n+3, column=1, pady=8)
        self.src_var = tk.IntVar(value=1)
        tk.Spinbox(self.body, from_=1, to=n, textvariable=self.src_var,
                   width=4, font=FONT_SMALL).grid(row=n+3, column=2)
        tk.Label(self.body, text="终点节点:", bg="#f5f0e8", font=FONT_SMALL).grid(
            row=n+3, column=3, pady=8)
        self.dst_var = tk.IntVar(value=n)
        tk.Spinbox(self.body, from_=1, to=n, textvariable=self.dst_var,
                   width=4, font=FONT_SMALL).grid(row=n+3, column=4)
        self.result_text = tk.Text(self.body, height=5, width=50, font=FONT_SMALL, bg="#fffde7")
        self.result_text.grid(row=n+4, column=1, columnspan=n+2, pady=4, sticky="w")
        self.entries_built = True

    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】"); return
        import heapq, math
        n = self.n_nodes.get()
        INF = math.inf
        dist = []
        for i in range(n):
            row = []
            for j in range(n):
                v = self.dist_entries[i][j].get().strip()
                if i == j:
                    row.append(0.0)
                elif v in ("", "inf", "∞"):
                    row.append(INF)
                else:
                    try:    row.append(float(v))
                    except: row.append(INF)
            dist.append(row)

        src = self.src_var.get() - 1
        dst = self.dst_var.get() - 1
        # Dijkstra
        d = [INF]*n; d[src] = 0; prev = [-1]*n
        pq = [(0, src)]
        while pq:
            dd, u = heapq.heappop(pq)
            if dd > d[u]: continue
            for v in range(n):
                if dist[u][v] < INF and d[u]+dist[u][v] < d[v]:
                    d[v] = d[u]+dist[u][v]; prev[v] = u
                    heapq.heappush(pq, (d[v], v))
        self.result_text.delete("1.0","end")
        if d[dst] == INF:
            self.result_text.insert("end", "节点间无通路")
        else:
            path = []; cur = dst
            while cur != -1: path.append(cur+1); cur = prev[cur]
            path.reverse()
            self.result_text.insert("end", f"最短路长度: {d[dst]}\n")
            self.result_text.insert("end", f"最短路径: {' → '.join(map(str,path))}")


# ══════════════════════════════════════════════════════
#  预测方法页（移动平均/指数平滑/回归）
# ══════════════════════════════════════════════════════
class ForecastPage(tk.Frame):
    def __init__(self, master, controller, mode="移动平均法"):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.mode = mode
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"运筹学模型求解系统———{self.mode}",
                 font=("微软雅黑", 13, "bold"), bg="#d7ccc8").pack(side="left", padx=10, pady=6)
        make_btn(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=10)
        make_btn(hdr, "返  回", self.controller.show_menu, bg=BTN_GRAY, width=8).pack(side="left", padx=4)

        body = tk.Frame(self, bg="#f5f0e8")
        body.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(body, text="历史数据（每行一个数值，按时间顺序）:",
                 bg="#f5f0e8", font=FONT_SMALL).grid(row=0, column=0, sticky="w")
        self.data_text = tk.Text(body, height=10, width=20, font=FONT_SMALL)
        self.data_text.grid(row=1, column=0, rowspan=5, padx=4, pady=4, sticky="nw")

        param_frame = tk.Frame(body, bg="#f5f0e8")
        param_frame.grid(row=1, column=1, padx=20, sticky="nw")

        if self.mode == "移动平均法":
            tk.Label(param_frame, text="移动步数 N:", bg="#f5f0e8", font=FONT_SMALL).pack(anchor="w")
            self.param_n = tk.IntVar(value=3)
            tk.Spinbox(param_frame, from_=2, to=10, textvariable=self.param_n,
                       width=5, font=FONT_SMALL).pack(anchor="w")
        elif self.mode == "指数平滑法":
            tk.Label(param_frame, text="平滑系数 α (0~1):", bg="#f5f0e8", font=FONT_SMALL).pack(anchor="w")
            self.param_alpha = tk.DoubleVar(value=0.3)
            tk.Entry(param_frame, textvariable=self.param_alpha, width=8,
                     font=FONT_SMALL).pack(anchor="w")

        self.result_text = tk.Text(body, height=12, width=45, font=FONT_SMALL, bg="#fffde7")
        self.result_text.grid(row=1, column=2, rowspan=6, padx=10, pady=4, sticky="nw")

    def _solve(self):
        raw = self.data_text.get("1.0","end").strip().split()
        try:
            data = [float(v) for v in raw if v]
        except:
            messagebox.showerror("输入错误","数据格式不正确"); return
        if len(data) < 2:
            messagebox.showerror("输入错误","至少需要2个数据"); return

        self.result_text.delete("1.0","end")

        if self.mode == "移动平均法":
            N = self.param_n.get()
            preds = []
            for i in range(N-1, len(data)):
                preds.append(sum(data[i-N+1:i+1])/N)
            self.result_text.insert("end", f"移动平均预测（N={N}）：\n\n")
            for i, p in enumerate(preds):
                self.result_text.insert("end", f"  第{i+N}期预测值: {p:.4f}\n")
            self.result_text.insert("end", f"\n下一期预测值: {preds[-1]:.4f}")

        elif self.mode == "指数平滑法":
            alpha = self.param_alpha.get()
            s = data[0]
            preds = [s]
            for v in data[1:]:
                s = alpha*v + (1-alpha)*s
                preds.append(s)
            self.result_text.insert("end", f"指数平滑预测（α={alpha}）：\n\n")
            for i, p in enumerate(preds):
                self.result_text.insert("end", f"  第{i+1}期平滑值: {p:.4f}\n")
            self.result_text.insert("end", f"\n下一期预测值: {preds[-1]:.4f}")

        elif self.mode == "回归分析法":
            import numpy as np
            n = len(data)
            x = np.arange(1, n+1, dtype=float)
            y = np.array(data)
            a, b = np.polyfit(x, y, 1)
            pred_next = a*(n+1)+b
            ss_res = sum((y[i] - (a*x[i]+b))**2 for i in range(n))
            ss_tot = sum((v - y.mean())**2 for v in y)
            r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 1
            self.result_text.insert("end", f"线性回归分析：\n\n")
            self.result_text.insert("end", f"  回归方程: Y = {a:.4f}·t + {b:.4f}\n")
            self.result_text.insert("end", f"  拟合优度 R² = {r2:.4f}\n\n")
            self.result_text.insert("end", "  各期拟合值：\n")
            for i in range(n):
                self.result_text.insert("end", f"    第{i+1}期: 实际={data[i]}  预测={a*x[i]+b:.4f}\n")
            self.result_text.insert("end", f"\n下一期预测值（第{n+1}期）: {pred_next:.4f}")


# ══════════════════════════════════════════════════════
#  合理排班问题
# ══════════════════════════════════════════════════════
class SchedulingPage(tk.Frame, _TableEditMixin):
    """合理排班问题 - 四象限布局"""
    def __init__(self, master, controller):
        super().__init__(master, bg="#e8e0d0")
        self.controller = controller
        self.n_periods = tk.IntVar(value=7)
        self.work_days = tk.IntVar(value=5)
        self.built = False
        self._build()

    def _build(self):
        # ── 顶部控制栏 ──
        hdr = tk.Frame(self, bg="#c8b89a", relief="raised", bd=1)
        hdr.pack(fill="x")
        tk.Label(hdr, text="运筹学模型求解系统———合理排班问题",
                 font=("宋体",13,"bold"), bg="#c8b89a").pack(pady=4)
        ctrl = tk.Frame(hdr, bg="#c8b89a")
        ctrl.pack(pady=(0,4))
        tk.Label(ctrl, text="时间段数:", bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(8,0))
        tk.Spinbox(ctrl, from_=2, to=14, textvariable=self.n_periods,
                   width=4, font=FONT_SMALL).pack(side="left", padx=2)
        tk.Label(ctrl, text="每人连续工作天数:", bg="#c8b89a", font=FONT_SMALL).pack(side="left", padx=(12,0))
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

        # ── 四象限主布局 ──
        main_pane = tk.Frame(self, bg="#e8e0d0")
        main_pane.pack(fill="both", expand=True)

        # 左侧
        left_pane = tk.Frame(main_pane, bg="#e8e0d0")
        left_pane.pack(side="left", fill="both", expand=False)

        # 左上：模型表达式框
        expr_frame = tk.Frame(left_pane, bg="#f5f0e0", relief="groove", bd=1, height=200)
        expr_frame.pack(fill="x", padx=2, pady=(2,0))
        expr_frame.pack_propagate(False)
        top_row = tk.Frame(expr_frame, bg="#f5f0e0")
        top_row.pack(fill="x", padx=6, pady=(4,2))
        tk.Label(top_row, text="模型表达式（自动生成/可复制）:",
                 bg="#f5f0e0", font=("宋体",9,"bold")).pack(side="left")
        tk.Button(top_row, text="清  空",
                  command=lambda: self.expr_text.delete("1.0","end"),
                  bg="#ffcccc", font=("宋体",9), width=6).pack(side="left", padx=4)
        self.expr_text = tk.Text(expr_frame, font=("Consolas",10), bg="#fffff0",
                                 relief="sunken", bd=1)
        self.expr_text.pack(fill="both", expand=True, padx=6, pady=(0,4))

        # 左下：表格+结果
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
        canvas.create_window((4,4), window=self.body, anchor="nw")
        def _cfg(e): canvas.configure(scrollregion=canvas.bbox("all"))
        self.body.bind("<Configure>", _cfg)

        # 右侧
        right_pane = tk.Frame(main_pane, bg="#f5f5f0", relief="groove", bd=1)
        right_pane.pack(side="left", fill="both", expand=True, padx=4, pady=2)

        # 右上：求解步骤
        tk.Label(right_pane, text="── 求解步骤 ──",
                 bg="#f5f5f0", font=("宋体",10,"bold")).pack(pady=(4,2))
        step_outer = tk.Frame(right_pane, bg="#f5f5f0")
        step_outer.pack(fill="both", expand=True, padx=4, pady=(0,2))
        vsb3 = tk.Scrollbar(step_outer, orient="vertical")
        self.step_text = tk.Text(step_outer, font=("Consolas",10),
                                 bg="#fffff0", yscrollcommand=vsb3.set,
                                 wrap="none", state="disabled")
        vsb3.config(command=self.step_text.yview)
        vsb3.pack(side="right", fill="y")
        self.step_text.pack(fill="both", expand=True)

        # 右下：图形区
        self.chart_frame = tk.Frame(right_pane, bg="#f5f5f0",
                                    relief="groove", bd=1, height=300)
        self.chart_frame.pack(fill="x", padx=4, pady=(0,4))
        self.chart_frame.pack_propagate(False)
        tk.Label(self.chart_frame, text="求解后自动显示排班图",
                 bg="#f5f5f0", fg="#888", font=("宋体",9)).pack(expand=True)

        # 加载默认例题
        self.after(100, self._load_example)

    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            if c == 0 and hasattr(self, 'period_entries') and r < len(self.period_entries):
                return self.period_entries[r]
            if c == 1 and hasattr(self, 'need_entries') and r < len(self.need_entries):
                return self.need_entries[r]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        return "#fffff0" if c == 0 else "#ffff99"

    def _all_entries(self):
        try:
            if hasattr(self, 'period_entries'):
                for i, e in enumerate(self.period_entries):
                    yield (i, 0, e)
            if hasattr(self, 'need_entries'):
                for i, e in enumerate(self.need_entries):
                    yield (i, 1, e)
        except AttributeError:
            return

    def _load_example(self):
        self.n_periods.set(7)
        self.work_days.set(5)
        self._build_table()
        defaults = [20,24,25,20,28,32,34]
        labels = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
        for i,(v,lbl) in enumerate(zip(defaults,labels)):
            self.need_entries[i].delete(0,"end")
            self.need_entries[i].insert(0,str(v))
            self.period_entries[i].delete(0,"end")
            self.period_entries[i].insert(0,lbl)

    def _load_history(self):
        import os, json
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "autosave_合理排班.json")
        if not os.path.exists(path):
            messagebox.showinfo("恢复历史","暂无历史数据"); return
        with open(path,"r",encoding="utf-8") as f:
            data = json.load(f)
        self.n_periods.set(data["n"])
        self.work_days.set(data["k"])
        self._build_table()
        for i,(nm,nd) in enumerate(zip(data["names"],data["demands"])):
            self.period_entries[i].delete(0,"end")
            self.period_entries[i].insert(0,nm)
            self.need_entries[i].delete(0,"end")
            self.need_entries[i].insert(0,str(nd))
        messagebox.showinfo("恢复历史","历史数据已恢复")

    def _auto_save(self, names, demands):
        import os, json
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "autosave_合理排班.json")
        data = {"n":self.n_periods.get(),"k":self.work_days.get(),
                "names":names,"demands":demands}
        try:
            with open(path,"w",encoding="utf-8") as f:
                json.dump(data,f,ensure_ascii=False)
        except Exception:
            pass

    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        n = self.n_periods.get()
        BG="#e8e0d0"; HDR="#ffcc99"; YELL="#ffff99"
        W=12
        # 表头
        for k2,h in enumerate(["时段编号","时段名称","最少需求人数","开班人数(xi)"]):
            tk.Label(self.body, text=h, bg=HDR, font=("宋体",9),
                     relief="ridge", width=W).grid(row=0, column=k2, padx=1, pady=1)
        self.period_entries=[]
        self.need_entries=[]
        self.result_labels=[]
        subs="₁₂₃₄₅₆₇₈₉"
        for i in range(n):
            tk.Label(self.body, text=f"第{i+1}段", bg=BG,
                     font=("宋体",9), width=W).grid(row=i+1, column=0, padx=1, pady=1)
            pe=tk.Entry(self.body, width=W, font=("宋体",9), bg="#fffff0")
            pe.insert(0,f"时段{i+1}")
            pe.grid(row=i+1, column=1, padx=1, pady=1)
            self._bind_cell(pe, i, 0)
            self.period_entries.append(pe)
            ne=tk.Entry(self.body, width=W, font=("宋体",9), bg=YELL)
            ne.grid(row=i+1, column=2, padx=1, pady=1)
            self._bind_cell(ne, i, 1)
            self.need_entries.append(ne)
            vn=f"x{subs[i]}" if i<len(subs) else f"x{i+1}"
            rl=tk.Label(self.body, text=vn, bg="#b2dfdb",
                        font=("宋体",9), relief="sunken", width=W)
            rl.grid(row=i+1, column=3, padx=1, pady=1)
            self.result_labels.append(rl)

        # 最优值行
        res_row = n+2
        tk.Label(self.body, text="最少总人数", bg=BG,
                 font=("宋体",10,"bold")).grid(row=res_row, column=0, columnspan=3,
                 sticky="e", padx=4, pady=(8,2))
        self.total_label = tk.Label(self.body, text="", bg="#ef9a9a",
                                     font=("宋体",11,"bold"), relief="sunken", width=W)
        self.total_label.grid(row=res_row, column=3, padx=1, pady=2)
        self.built = True

    def _solve(self):
        if not self.built:
            messagebox.showwarning("提示","请先点击【确定】"); return
        try:
            from scipy.optimize import linprog
            import numpy as np
            n = self.n_periods.get()
            k = self.work_days.get()
            rest = n - k
            demands=[float(e.get() or 0) for e in self.need_entries]
            names=[e.get() for e in self.period_entries]
            self._auto_save(names, demands)

            # 约束矩阵
            A_ub=[]
            for i in range(n):
                row=[0.0]*n
                for j in range(k):
                    row[(i-j)%n]=1.0
                A_ub.append([-v for v in row])
            b_ub=[-d for d in demands]
            res=linprog([1.0]*n, A_ub=A_ub, b_ub=b_ub,
                        bounds=[(0,None)]*n, method="highs")

            if not res.success:
                messagebox.showerror("求解失败", res.message); return

            x=res.x
            total=sum(x)
            subs="₁₂₃₄₅₆₇₈₉"

            # 更新表格结果列
            for i,rl in enumerate(self.result_labels):
                rl.config(text=str(round(x[i])))
            self.total_label.config(text=str(round(total)))

            # 生成模型表达式
            self.expr_text.delete("1.0","end")
            vnames=[f"x{subs[i]}" if i<len(subs) else f"x{i+1}" for i in range(n)]
            self.expr_text.insert("end", f"min  Z = {' + '.join(vnames)}\n\n")
            self.expr_text.insert("end", "s.t.\n")
            for i in range(n):
                vs=sorted([(i-j)%n for j in range(k)])
                lhs=" + ".join(vnames[v] for v in vs)
                self.expr_text.insert("end", f"  {lhs} >= {int(demands[i])}  ({names[i]})\n")
            self.expr_text.insert("end", "\n")
            for v in vnames:
                self.expr_text.insert("end", f"  {v} >= 0\n")

            # 求解步骤
            self.step_text.config(state="normal")
            self.step_text.delete("1.0","end")
            self.step_text.tag_config("title", foreground="#1a5276", font=("宋体",10,"bold"))
            self.step_text.tag_config("data",  foreground="#196F3D", font=("Consolas",10))
            self.step_text.tag_config("result",foreground="#922B21", font=("Consolas",10,"bold"))

            self.step_text.insert("end", "【问题描述】\n", "title")
            self.step_text.insert("end",
                f"  共{n}个时间段，每人连续工作{k}天，休息{rest}天\n", "data")
            self.step_text.insert("end", "  各时段需求：\n", "data")
            for i in range(n):
                self.step_text.insert("end",
                    f"    {names[i]}：需要 {int(demands[i])} 人\n", "data")

            self.step_text.insert("end", "\n【约束矩阵】\n", "title")
            self.step_text.insert("end", "  每段在班人员 = 该段及之前k段开始上班的人\n", "data")

            self.step_text.insert("end", "\n【最优解】\n", "title")
            for i in range(n):
                od=sum(x[(i-j)%n] for j in range(k))
                self.step_text.insert("end",
                    f"  {names[i]}：开班{round(x[i])}人，实际在班{od:.0f}人"
                    f"（需求{int(demands[i])}人，{'✓' if od>=demands[i]-1e-6 else '✗'}）\n", "data")
            self.step_text.insert("end", f"\n  最少总人数：{round(total)} 人\n", "result")
            self.step_text.config(state="disabled")
            self.step_text.see("end")

            # 排班图
            self._draw_schedule(names, demands, x, k, n)

        except Exception as e:
            messagebox.showerror("错误", str(e))

    def _draw_schedule(self, names, demands, x, k, n):
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import numpy as np

            for w in self.chart_frame.winfo_children():
                w.destroy()

            fig, ax = plt.subplots(figsize=(5.5,3.5), dpi=90)
            fig.patch.set_facecolor("#f5f5f0")
            ax.set_facecolor("#fafafa")

            idx = np.arange(n)
            bars_d = ax.bar(idx-0.2, demands, 0.35,
                            label="需求人数", color="#aed6f1", edgecolor="#2980b9")
            bars_x = ax.bar(idx+0.2, [round(v) for v in x], 0.35,
                            label="开班人数", color="#f1948a", edgecolor="#c0392b")

            ax.set_xticks(idx)
            ax.set_xticklabels(names, fontfamily="SimHei", fontsize=8, rotation=30)
            ax.set_ylabel("人数", fontfamily="SimHei", fontsize=9)
            ax.set_title("各时段需求与开班人数对比", fontfamily="SimHei",
                         fontsize=11, fontweight="bold")
            ax.legend(prop={"family":"SimHei","size":8})
            ax.grid(True, alpha=0.3, axis="y")

            # 标数值
            for bar in bars_d:
                h=bar.get_height()
                if h>0: ax.text(bar.get_x()+bar.get_width()/2, h+0.3,
                                str(int(h)), ha="center", fontsize=7, color="#2980b9")
            for bar in bars_x:
                h=bar.get_height()
                if h>0: ax.text(bar.get_x()+bar.get_width()/2, h+0.3,
                                str(int(h)), ha="center", fontsize=7, color="#c0392b")

            plt.tight_layout(pad=0.3)
            cw=FigureCanvasTkAgg(fig, master=self.chart_frame)
            cw.draw()
            cw.get_tk_widget().pack(fill="both", expand=True)
            plt.close(fig)
        except Exception:
            pass

# ══════════════════════════════════════════════════════
#  主控制器
# ══════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("运筹学模型求解工具")
        self.geometry("1300x800")
        self.resizable(True, True)
        self.configure(bg=BG_DARK)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass
        self._current = None
        self.show_home()

    def _show(self, frame):
        if self._current:
            self._current.destroy()
        self._current = frame
        frame.pack(fill="both", expand=True)

    def show_home(self):
        self._show(HomePage(self, self))

    def show_menu(self):
        self._show(MenuPage(self, self))

    def open_solver(self, name):
        pages = {
            "线性规划问题":  lambda: LPPage(self, self, "线性规划问题"),
            "纯整数规划":    lambda: LPPage(self, self, "纯整数规划",   integer_vars=True),
            "0-1整数规划":   lambda: LPPage(self, self, "0-1整数规划",  binary_vars=True),
            "混合整数规划":  lambda: LPPage(self, self, "混合整数规划", integer_vars=[]),
            "产销平衡问题":  lambda: TransportPage(self, self, "平衡"),
            "产大于销问题":  lambda: TransportPage(self, self, "产大于销"),
            "销大于产问题":  lambda: TransportPage(self, self, "销大于产"),
            "指派问题":      lambda: TransportPage(self, self, "指派"),
            "最大最小准则":  lambda: DecisionPage(self, self, "最大最小准则"),
            "最大最大准则":  lambda: DecisionPage(self, self, "最大最大准则"),
            "后悔值准则":    lambda: DecisionPage(self, self, "后悔值准则"),
            "期望值准则":    lambda: DecisionPage(self, self, "期望值准则"),
            "乐观系数准则": lambda: DecisionPage(self, self, "乐观系数准则"),
            "等可能性准则": lambda: DecisionPage(self, self, "等可能性准则"),
            "最短路问题":    lambda: ShortestPathPage(self, self),
            "移动平均法":    lambda: ForecastPage(self, self, "移动平均法"),
            "指数平滑法":    lambda: ForecastPage(self, self, "指数平滑法"),
            "回归分析法":    lambda: ForecastPage(self, self, "回归分析法"),
            "合理排班问题":  lambda: SchedulingPage(self, self),
        }
        if name in pages:
            self._show(pages[name]())
        else:
            messagebox.showinfo("提示", f"【{name}】功能正在开发中...")

    def quit_app(self):
        if messagebox.askyesno("退出", "确认退出系统？"):
            self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
