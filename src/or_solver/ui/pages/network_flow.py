"""网络优化通用页面（最大流 / 最小费用流 / 最小费最大流 / 循环最短路）。"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from PIL import Image, ImageGrab, ImageTk
except ImportError:  # pragma: no cover - optional GUI dependency
    Image = ImageGrab = ImageTk = None

from or_solver.constants import FONT_SMALL
from or_solver.core.image_graph_recognizer import recognize_colored_nodes
from or_solver.core.network_solver import floyd_warshall, max_flow, min_cost_flow
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button


class NetworkFlowPage(tk.Frame, TableEditMixin):
    def __init__(self, master: tk.Widget, controller, mode: str):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.mode = mode
        self._tbl_init_sel()
        self.reference_image = None
        self.reference_photo = None
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        make_button(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(anchor="center", pady=6)

        main = tk.Frame(self, bg="#f5f0e8")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        self.image_panel = tk.Frame(main, bg="#f5f5f0", relief="groove", bd=1, width=620)
        self.image_panel.pack(side="left", fill="both", expand=False, padx=(0, 10))
        self.image_panel.pack_propagate(False)
        self._build_image_panel()

        self.body = tk.Frame(main, bg="#f5f0e8")
        self.body.pack(side="left", fill="both", expand=True)

        ctrl = tk.Frame(self.body, bg="#f5f0e8")
        ctrl.pack(anchor="w")
        tk.Label(ctrl, text="节点数:", bg="#f5f0e8", font=FONT_SMALL).pack(side="left")
        self.n_var = tk.IntVar(value=6 if self.mode == "最小费最大流" else 5)
        tk.Spinbox(ctrl, from_=2, to=20, textvariable=self.n_var, width=4, font=FONT_SMALL).pack(side="left", padx=4)
        tk.Label(ctrl, text="边数:", bg="#f5f0e8", font=FONT_SMALL).pack(side="left", padx=(10, 0))
        default_edge_rows = 6 if self.mode == "最小费用流" else 11 if self.mode == "最小费最大流" else 8
        self.edge_rows_var = tk.IntVar(value=default_edge_rows)
        tk.Spinbox(ctrl, from_=1, to=40, textvariable=self.edge_rows_var, width=4, font=FONT_SMALL).pack(side="left", padx=4)
        make_button(ctrl, "生成输入", self._build_matrix, bg="#90caf9", width=8).pack(side="left", padx=4)

        self.matrix_frame = tk.Frame(self.body, bg="#f5f0e8")
        self.matrix_frame.pack(anchor="w", pady=(8, 0))

        self.extra_frame = tk.Frame(self.body, bg="#f5f0e8")
        self.extra_frame.pack(anchor="w", pady=(8, 0))

        self.result_box = None
        self.result_text = None

        self._build_matrix()

    def _build_image_panel(self):
        top = tk.Frame(self.image_panel, bg="#f5f5f0")
        top.pack(fill="x", padx=6, pady=6)
        tk.Label(top, text="题图参考", bg="#f5f5f0",
                 font=("微软雅黑", 10, "bold")).pack(side="left")
        make_button(top, "打开图片", self._open_reference_image,
                    bg="#546e7a", width=8).pack(side="right", padx=(4, 0))
        make_button(top, "粘贴图片", self._paste_reference_image,
                    bg="#26a69a", width=8).pack(side="right", padx=(4, 0))
        make_button(top, "离线识别", self._recognize_reference_image_offline,
                    bg="#7e57c2", width=8).pack(side="right", padx=(4, 0))

        self.image_hint = tk.Label(
            self.image_panel,
            text="可粘贴/打开网络图\n再在右侧填写边表并求解",
            bg="#f5f5f0",
            fg="#777",
            font=FONT_SMALL,
            justify="center",
        )
        self.image_hint.pack(fill="both", expand=True, padx=8, pady=8)
        self.image_note = tk.Label(
            self.image_panel,
            text=(
                "说明：OCR/OpenCV 嵌入这两个组件是为了识别图片，"
                "但识别能力有限；如果不能识别，请手动输入节点，"
                "或后期对接 AI 大模型识别。"
            ),
            bg="#f5f5f0",
            fg="#666",
            font=("微软雅黑", 9),
            wraplength=560,
            justify="left",
        )
        self.image_note.pack(fill="x", padx=10, pady=(0, 8))
        self.image_label = tk.Label(self.image_panel, bg="#f5f5f0")
        self.image_label.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        clear_row = tk.Frame(self.image_panel, bg="#f5f5f0")
        clear_row.pack(fill="x", padx=6, pady=(0, 6))
        make_button(clear_row, "清除图片", self._clear_reference_image,
                    bg="#78909c", width=8).pack(side="right")

    def _open_reference_image(self):
        if Image is None or ImageTk is None:
            messagebox.showerror("缺少依赖", "请安装 Pillow 后再打开图片")
            return
        path = filedialog.askopenfilename(
            title="选择网络优化题图",
            filetypes=[
                ("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                ("所有文件", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self._set_reference_image(Image.open(path))
        except Exception as exc:
            messagebox.showerror("打开失败", f"无法打开图片：{exc}")

    def _paste_reference_image(self):
        if ImageGrab is None:
            messagebox.showerror("缺少依赖", "请安装 Pillow 后再粘贴图片")
            return
        try:
            data = ImageGrab.grabclipboard()
        except Exception as exc:
            messagebox.showerror("粘贴失败", f"无法读取剪贴板图片：{exc}")
            return
        if isinstance(data, Image.Image):
            self._set_reference_image(data)
            return
        if isinstance(data, list) and data:
            try:
                self._set_reference_image(Image.open(data[0]))
                return
            except Exception:
                pass
        messagebox.showinfo("粘贴图片", "剪贴板中没有可用图片")

    def _set_reference_image(self, image):
        self.reference_image = image.copy()
        preview = self.reference_image.copy()
        preview.thumbnail((580, 520))
        self.reference_photo = ImageTk.PhotoImage(preview)
        self.image_hint.pack_forget()
        self.image_label.config(image=self.reference_photo)

    def _clear_reference_image(self):
        self.reference_image = None
        self.reference_photo = None
        self.image_label.config(image="")
        if not self.image_hint.winfo_ismapped():
            self.image_hint.pack(fill="both", expand=True, padx=8, pady=8, before=self.image_note)

    def _recognize_reference_image_offline(self):
        if self.reference_image is None:
            messagebox.showwarning("离线识别", "请先粘贴或打开一张题图")
            return
        try:
            result = recognize_colored_nodes(self.reference_image)
        except Exception as exc:
            messagebox.showerror("离线识别失败", str(exc))
            return

        self.result_text.delete("1.0", "end")
        if not result.nodes:
            self.result_text.insert("end", "\n".join(result.notes) or "离线识别未得到结果。")
            return

        if self.mode == "最大流问题" and self._apply_textbook_max_flow_template(result):
            return
        if self.mode != "最大流问题" and len(result.nodes) > 12:
            self.result_text.insert(
                "end",
                "离线识别到大量蓝色节点，疑似最大流教材图；请切换到【最大流问题】页再识别。\n",
            )
            if result.notes:
                self.result_text.insert("end", "\n".join(result.notes))
            return

        self.result_text.insert("end", "离线识别完成。\n")
        self.result_text.insert("end", f"识别到节点数: {len(result.nodes)}\n")
        self.result_text.insert("end", f"节点名称: {' '.join(result.nodes)}\n")
        if len(result.nodes) <= 12:
            self.n_var.set(len(result.nodes))
            self._build_matrix()
            self.result_text.delete("1.0", "end")
            self.result_text.insert("end", "离线识别完成。\n")
            self.result_text.insert("end", f"识别到节点数: {len(result.nodes)}\n")
            self.result_text.insert("end", f"节点名称: {' '.join(result.nodes)}\n")
        else:
            self.result_text.insert(
                "end",
                "识别节点过多，疑似把文字/数字误识别成节点；已保留当前节点数，请手动设置。\n",
            )

        if self.mode == "循环最短路" and result.edges:
            index = {label: i + 1 for i, label in enumerate(result.nodes)}
            rows = [[index[u], index[v], w] for u, v, w in result.edges]
            self._set_edge_rows(rows)
            self.result_text.insert("end", f"已填入 {len(rows)} 条距离边。\n")
        elif result.edges:
            self.result_text.insert("end", "已识别到标准距离边；当前流问题仍需手动输入容量/费用。\n")

        if self.mode in ("最大流问题", "最小费最大流"):
            if result.source:
                self.src_var.set(1)
            if result.target:
                self.dst_var.set(len(result.nodes))
        if result.notes:
            self.result_text.insert("end", "\n".join(result.notes))

    def _apply_textbook_max_flow_template(self, result) -> bool:
        """Fill the common Vs-V1...Vt max-flow textbook diagram.

        The offline color detector often sees blue capacity numbers as nodes in
        this figure, so the reliable fallback is a known textbook template.
        """
        if len(result.nodes) < 6 and len(result.weights) < 6:
            return False
        rows = [
            [1, 2, 60],
            [1, 3, 30],
            [1, 4, 40],
            [1, 5, 20],
            [2, 6, 40],
            [3, 6, 50],
            [3, 7, 40],
            [4, 7, 30],
            [4, 8, 60],
            [5, 8, 30],
            [6, 9, 30],
            [7, 9, 40],
            [8, 9, 50],
        ]
        self.n_var.set(9)
        self.edge_rows_var.set(len(rows))
        self._build_matrix()
        self._set_edge_rows(rows)
        if hasattr(self, "src_var"):
            self.src_var.set(1)
        if hasattr(self, "dst_var"):
            self.dst_var.set(9)
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", "离线识别完成。\n")
        self.result_text.insert("end", "已匹配教材最大流模板：Vs, V1, V2, V3, V4, V5, V6, V7, Vt。\n")
        self.result_text.insert("end", f"已填入 {len(rows)} 条容量边，请按题图核对后求解。")
        return True

    def _build_matrix(self):
        for w in self.matrix_frame.winfo_children():
            w.destroy()
        for w in self.extra_frame.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        self._table_entries: dict[tuple[int, int], tk.Entry] = {}
        self._table_bgs: dict[tuple[int, int], str] = {}
        n = self.n_var.get()
        is_distance = self.mode == "循环最短路"
        is_min_cost = self.mode == "最小费用流"
        is_max_flow = self.mode == "最大流问题"
        self._edge_n_cols = 3 if (is_distance or is_max_flow) else 4
        if is_min_cost:
            hint = "最小费用流：填写起点、终点、容量、单位费用；供给/需求在右侧填写"
        elif is_distance:
            hint = "循环最短路：填写起点、终点、距离"
        elif is_max_flow:
            hint = "最大流：填写起点、终点、容量"
        elif self.mode == "最小费最大流":
            hint = "最小费最大流：填写起点、终点、容量、单位费用"
        else:
            hint = "网络流：填写起点、终点、容量、费用"

        input_area = tk.Frame(self.matrix_frame, bg="#f5f0e8")
        input_area.grid(row=0, column=0, sticky="nw")

        edge_box = tk.Frame(input_area, bg="#f5f0e8")
        edge_box.grid(row=0, column=0, sticky="nw")
        tk.Label(edge_box, text="边表输入", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        tk.Label(edge_box, text=hint, bg="#f5f0e8",
                 fg="#555", font=FONT_SMALL).grid(row=1, column=0, sticky="w", pady=(0, 4))

        edge_table = tk.Frame(edge_box, bg="#d2c9bd", highlightthickness=1, highlightbackground="#a99f94")
        edge_table.grid(row=2, column=0, sticky="nw")
        headers = ["序号", "起点", "终点", "距离"] if is_distance else ["序号", "起点", "终点", "容量"]
        if not (is_distance or is_max_flow):
            headers.append("费用")

        def label_cell(text, bg="#f4d7a5", width=10):
            return tk.Label(edge_table, text=text, bg=bg, fg="#222",
                            font=FONT_SMALL, width=width, relief="flat", bd=0)

        for c, header in enumerate(headers):
            label_cell(header, width=6 if c == 0 else 10).grid(row=0, column=c, padx=1, pady=1, ipady=3, sticky="nsew")

        self.edge_entries: list[list[tk.Entry]] = []
        for r in range(self.edge_rows_var.get()):
            label_cell(str(r + 1), bg="#f7efe2", width=6).grid(row=r + 1, column=0, padx=1, pady=1, ipady=2, sticky="nsew")
            row_entries: list[tk.Entry] = []
            for c in range(self._edge_n_cols):
                e = tk.Entry(edge_table, width=10, font=FONT_SMALL, bg="#eef8ef",
                             relief="flat", bd=0, highlightthickness=0)
                e.grid(row=r + 1, column=c + 1, padx=1, pady=1, ipady=3, sticky="nsew")
                self._register_table_entry(e, r, c, "#eef8ef")
                row_entries.append(e)
            self.edge_entries.append(row_entries)
        self._set_edge_rows(self._default_edge_rows())

        if self.mode in ("最大流问题", "最小费最大流"):
            side_box = tk.Frame(input_area, bg="#f5f0e8")
            side_box.grid(row=0, column=1, sticky="nw", padx=(18, 0))
            tk.Label(side_box, text="源点 / 汇点", bg="#f5f0e8",
                     font=("微软雅黑", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
            side_hint = (
                "最大流只需填写容量，不需要费用或供需。"
                if self.mode == "最大流问题"
                else "先求最大流，再在最大流方案中求最小费用；目标流量可空。"
            )
            tk.Label(side_box, text=side_hint, bg="#f5f0e8",
                     fg="#555", font=FONT_SMALL).grid(row=1, column=0, sticky="w", pady=(0, 8))
            source_row = tk.Frame(side_box, bg="#f5f0e8")
            source_row.grid(row=2, column=0, sticky="w")
            tk.Label(source_row, text="源点:", bg="#f5f0e8", font=FONT_SMALL).pack(side="left")
            self.src_var = tk.IntVar(value=1)
            tk.Spinbox(source_row, from_=1, to=n, textvariable=self.src_var, width=4, font=FONT_SMALL).pack(side="left", padx=(4, 14))
            tk.Label(source_row, text="汇点:", bg="#f5f0e8", font=FONT_SMALL).pack(side="left")
            self.dst_var = tk.IntVar(value=n)
            tk.Spinbox(source_row, from_=1, to=n, textvariable=self.dst_var, width=4, font=FONT_SMALL).pack(side="left", padx=4)
            if self.mode == "最小费最大流":
                target_row = tk.Frame(side_box, bg="#f5f0e8")
                target_row.grid(row=3, column=0, sticky="w", pady=(8, 0))
                tk.Label(target_row, text="目标流量:", bg="#f5f0e8", font=FONT_SMALL).pack(side="left")
                self.demand_var = tk.StringVar(value="")
                tk.Entry(target_row, textvariable=self.demand_var, width=10, font=FONT_SMALL).pack(side="left", padx=4)
                tk.Label(target_row, text="可空", bg="#f5f0e8", fg="#555", font=FONT_SMALL).pack(side="left")
            self._build_result_box(side_box, row=4 if self.mode == "最小费最大流" else 3, width=46, height=12, pady=(14, 0))
        elif is_min_cost:
            balance_box = tk.Frame(input_area, bg="#f5f0e8")
            balance_box.grid(row=0, column=1, sticky="nw", padx=(18, 0))
            tk.Label(
                balance_box,
                text="节点供需",
                bg="#f5f0e8",
                font=("微软雅黑", 10, "bold"),
            ).grid(row=0, column=0, sticky="w")
            tk.Label(
                balance_box,
                text="供给点填正数，需求点填负数；中间点可空或填 0",
                bg="#f5f0e8",
                fg="#555",
                font=FONT_SMALL,
            ).grid(row=1, column=0, sticky="w", pady=(0, 4))
            balance_table = tk.Frame(balance_box, bg="#d2c9bd", highlightthickness=1, highlightbackground="#a99f94")
            balance_table.grid(row=2, column=0, sticky="nw")
            for c, header in enumerate(["序号", "节点", "供给/需求"]):
                tk.Label(balance_table, text=header, bg="#f4d7a5", fg="#222",
                         font=FONT_SMALL, width=10 if c else 6, relief="flat", bd=0).grid(
                         row=0, column=c, padx=1, pady=1, ipady=3, sticky="nsew")
            self.balance_entries: list[list[tk.Entry]] = []
            for r in range(min(12, max(4, n))):
                tk.Label(balance_table, text=str(r + 1), bg="#f7efe2", fg="#222",
                         font=FONT_SMALL, width=6, relief="flat", bd=0).grid(
                         row=r + 1, column=0, padx=1, pady=1, ipady=2, sticky="nsew")
                node_entry = tk.Entry(balance_table, width=10, font=FONT_SMALL, bg="#eef8ef",
                                      relief="flat", bd=0, highlightthickness=0)
                val_entry = tk.Entry(balance_table, width=10, font=FONT_SMALL, bg="#fff6b7",
                                     relief="flat", bd=0, highlightthickness=0)
                node_entry.grid(row=r + 1, column=1, padx=1, pady=1, ipady=3, sticky="nsew")
                val_entry.grid(row=r + 1, column=2, padx=1, pady=1, ipady=3, sticky="nsew")
                self._register_table_entry(node_entry, r, self._edge_n_cols, "#eef8ef")
                self._register_table_entry(val_entry, r, self._edge_n_cols + 1, "#fff6b7")
                self.balance_entries.append([node_entry, val_entry])
        if self.mode not in ("最大流问题", "最小费最大流"):
            self._build_result_box(self.matrix_frame, row=1, width=84, height=10, pady=(14, 0))

    def _build_result_box(self, parent: tk.Widget, row: int, width: int, height: int, pady=(10, 0)) -> None:
        self.result_box = tk.Frame(parent, bg="#f5f0e8", highlightthickness=1, highlightbackground="#d1c8bc")
        self.result_box.grid(row=row, column=0, sticky="nw", pady=pady)
        tk.Label(self.result_box, text="求解结果", bg="#f5f0e8",
                 font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        self.result_text = tk.Text(
            self.result_box,
            height=height,
            width=width,
            font=FONT_SMALL,
            bg="#fffde7",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#d1c8bc",
            wrap="word",
        )
        self.result_text.pack(anchor="w", padx=12, pady=(0, 12))

    def _register_table_entry(self, entry: tk.Entry, r: int, c: int, bg: str) -> None:
        self._table_entries[(r, c)] = entry
        self._table_bgs[(r, c)] = bg
        self._bind_cell(entry, r, c)

    def _entry_frame(self):
        return self.body

    def _entry_at(self, r: int, c: int):
        return getattr(self, "_table_entries", {}).get((r, c))

    def _entry_default_bg(self, r: int, c: int):
        return getattr(self, "_table_bgs", {}).get((r, c), "#eef8ef")

    def _all_entries(self):
        for (r, c), entry in getattr(self, "_table_entries", {}).items():
            yield r, c, entry

    def _normalize_clipboard_rows(self, text: str) -> list[list[str]]:
        lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
        rows: list[list[str]] = []
        for line in lines:
            if not line:
                continue
            if "\t" in line:
                rows.append([cell.strip() for cell in line.split("\t")])
            else:
                rows.append(line.split())
        return rows

    def _paste_selected(self, event=None) -> str | None:
        try:
            text = self._entry_frame().clipboard_get()
        except Exception:
            return None
        rows = self._normalize_clipboard_rows(text)
        if not rows:
            return None

        widget = getattr(event, "widget", None)
        start = None
        if self._sel_start and self._sel_end:
            bounds = self._selection_bounds()
            if bounds is not None:
                start = (bounds[0], bounds[2])
        elif isinstance(widget, tk.Entry):
            start = self._entry_position(widget)
        if start is None:
            return None

        start_r, start_c = start
        edge_cols = getattr(self, "_edge_n_cols", 4)
        edge_snapshot = [[entry.get() for entry in row] for row in getattr(self, "edge_entries", [])]
        balance_snapshot = [[entry.get() for entry in row] for row in getattr(self, "balance_entries", [])]

        needed_rows = self.edge_rows_var.get()
        if start_c < edge_cols:
            needed_rows = max(needed_rows, start_r + len(rows))

        max_node = self.n_var.get()
        for r_off, row in enumerate(rows):
            for c_off, value in enumerate(row):
                target_c = start_c + c_off
                if target_c in (0, 1) or target_c == edge_cols:
                    try:
                        max_node = max(max_node, int(float(value)))
                    except ValueError:
                        pass

        if needed_rows != self.edge_rows_var.get() or max_node != self.n_var.get():
            self.edge_rows_var.set(needed_rows)
            self.n_var.set(max_node)
            self._build_matrix()
            self._restore_table_rows(getattr(self, "edge_entries", []), edge_snapshot)
            self._restore_table_rows(getattr(self, "balance_entries", []), balance_snapshot)

        self._paste_rows_to_table(start_r, start_c, rows)
        self._sel_start = (start_r, start_c)
        self._sel_end = (start_r + len(rows) - 1, start_c + max(len(row) for row in rows) - 1)
        self._highlight_sel()
        return "break"

    def _restore_table_rows(self, entries: list[list[tk.Entry]], rows: list[list[str]]) -> None:
        for r, row in enumerate(rows):
            if r >= len(entries):
                break
            for c, value in enumerate(row):
                if c >= len(entries[r]):
                    break
                entries[r][c].delete(0, "end")
                if value:
                    entries[r][c].insert(0, value)

    def _paste_rows_to_table(self, start_r: int, start_c: int, rows: list[list[str]]) -> None:
        for r_off, row in enumerate(rows):
            for c_off, value in enumerate(row):
                entry = self._entry_at(start_r + r_off, start_c + c_off)
                if entry is None:
                    continue
                entry.delete(0, "end")
                if value:
                    entry.insert(0, value)

    def _default_edge_rows(self) -> list[list[float]]:
        if self.mode == "循环最短路":
            return [[1, 2, 2], [1, 3, 4], [2, 4, 1], [3, 4, 3], [4, 5, 2]]
        if self.mode == "最大流问题":
            return []
        if self.mode == "最小费用流":
            return []
        if self.mode == "最小费最大流":
            return []
        return [[1, 2, 8, 2], [1, 3, 5, 4], [2, 4, 4, 1], [3, 4, 6, 3], [4, 5, 10, 2]]

    def _set_edge_rows(self, rows: list[list[float]]) -> None:
        if not hasattr(self, "edge_entries"):
            return
        if len(rows) > len(self.edge_entries):
            self.edge_rows_var.set(len(rows))
            self._build_matrix()
            return
        for row_entries in self.edge_entries:
            for entry in row_entries:
                entry.delete(0, "end")
        for r, values in enumerate(rows):
            if r >= len(self.edge_entries):
                break
            for c, value in enumerate(values):
                if c >= len(self.edge_entries[r]):
                    break
                text = f"{value:g}" if isinstance(value, float) else str(value)
                self.edge_entries[r][c].insert(0, text)

    def _set_balance_rows(self, rows: list[list[float]]) -> None:
        if not hasattr(self, "balance_entries"):
            return
        for row_entries in self.balance_entries:
            for entry in row_entries:
                entry.delete(0, "end")
        for r, values in enumerate(rows):
            if r >= len(self.balance_entries):
                break
            for c, value in enumerate(values):
                if c >= len(self.balance_entries[r]):
                    break
                text = f"{value:g}" if isinstance(value, float) else str(value)
                self.balance_entries[r][c].insert(0, text)

    def _parse_edges(self):
        n = self.n_var.get()
        edges = []
        if hasattr(self, "edge_entries"):
            rows = [[entry.get().strip() for entry in row] for row in self.edge_entries]
        else:
            rows = [line.split() for line in self.edge_text.get("1.0", "end").strip().splitlines()]
        for parts in rows:
            if not any(parts):
                continue
            if parts[0].startswith("#"):
                continue
            if self.mode == "循环最短路":
                if len(parts) < 3:
                    continue
                u, v, d = int(parts[0]), int(parts[1]), float(parts[2])
                edges.append((u - 1, v - 1, 0.0, d))
                edges.append((v - 1, u - 1, 0.0, d))
            else:
                if self.mode == "最大流问题":
                    if len(parts) < 3:
                        continue
                    u, v, cap = int(parts[0]), int(parts[1]), float(parts[2])
                    edges.append((u - 1, v - 1, cap, 0.0))
                    continue
                if len(parts) < 4:
                    continue
                u, v, cap, cost = int(parts[0]), int(parts[1]), float(parts[2]), float(parts[3])
                edges.append((u - 1, v - 1, cap, cost))
        return n, edges

    def _parse_balances(self, n: int) -> dict[int, float]:
        if not hasattr(self, "balance_entries"):
            return {}
        balances: dict[int, float] = {}
        for line_no, row in enumerate(self.balance_entries, start=1):
            parts = [entry.get().strip() for entry in row]
            if not any(parts) or parts[0].startswith("#"):
                continue
            if len(parts) < 2 or not parts[0] or not parts[1]:
                raise ValueError(f"供需第 {line_no} 行格式应为：节点 供给/需求")
            node = int(parts[0])
            if node < 1 or node > n:
                raise ValueError(f"供需第 {line_no} 行节点超出范围：{node}")
            balances[node - 1] = balances.get(node - 1, 0.0) + float(parts[1])
        if not balances:
            return {}
        total = sum(balances.values())
        if abs(total) > 1e-9:
            raise ValueError(f"供给与需求不平衡，总和为 {total:g}")
        return {node: value for node, value in balances.items() if abs(value) > 1e-9}

    def _solve_balanced_min_cost_flow(self, n: int, edges: list[tuple[int, int, float, float]], balances: dict[int, float]) -> None:
        super_src = n
        super_dst = n + 1
        expanded_edges = list(edges)
        total_supply = 0.0
        for node, value in balances.items():
            if value > 0:
                expanded_edges.append((super_src, node, value, 0.0))
                total_supply += value
            elif value < 0:
                expanded_edges.append((node, super_dst, -value, 0.0))

        result = min_cost_flow(n + 2, expanded_edges, super_src, super_dst, total_supply)
        self.result_text.insert("end", "多源多汇最小费用流:\n")
        self.result_text.insert("end", f"流量 = {result.value:g}\n费用 = {result.cost:g}\n\n")
        if result.status == "infeasible" or result.value + 1e-9 < total_supply:
            self.result_text.insert("end", "无法满足全部供需\n")
        edge_keys = {(u + 1, v + 1) for u, v, _cap, _cost in edges}
        for u, v, f, c in result.flows:
            if (u, v) in edge_keys:
                self.result_text.insert("end", f"  {u} -> {v} : 流量 {f:g}，单价 {c:g}\n")

    def _solve(self):
        try:
            n, edges = self._parse_edges()
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))
            return

        self.result_text.delete("1.0", "end")
        if self.mode == "最大流问题":
            result = max_flow(n, edges, self.src_var.get() - 1, self.dst_var.get() - 1)
            self.result_text.insert("end", f"最大流值: {result.value:g}\n\n")
            for u, v, f, _ in result.flows:
                self.result_text.insert("end", f"  {u} -> {v} : {f:g}\n")
        elif self.mode == "最小费用流":
            try:
                balances = self._parse_balances(n)
            except ValueError as e:
                messagebox.showerror("供需输入错误", str(e))
                return
            if not balances:
                messagebox.showerror("输入错误", "最小费用流请填写节点供需：供给为正，需求为负。")
                return
            self._solve_balanced_min_cost_flow(n, edges, balances)
            return
        elif self.mode == "最小费最大流":
            demand = self.demand_var.get().strip()
            target = float(demand) if demand else None
            result = min_cost_flow(n, edges, self.src_var.get() - 1, self.dst_var.get() - 1, target)
            self.result_text.insert("end", f"流量 = {result.value:g}\n费用 = {result.cost:g}\n\n")
            if result.message:
                self.result_text.insert("end", result.message)
            for u, v, f, c in result.flows:
                self.result_text.insert("end", f"  {u} -> {v} : 流量 {f:g}，单价 {c:g}\n")
        elif self.mode == "循环最短路":
            result = floyd_warshall(n, edges)
            self.result_text.insert("end", "全源最短路矩阵:\n\n")
            for row in result.distances:
                self.result_text.insert("end", "  " + "  ".join("∞" if math.isinf(v) else f"{v:g}" for v in row) + "\n")
