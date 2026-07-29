"""最小支撑树求解页。"""
from __future__ import annotations

import math
import re
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from PIL import Image, ImageGrab, ImageTk
except ImportError:  # pragma: no cover - optional GUI dependency
    Image = ImageGrab = ImageTk = None

from or_solver.constants import BTN_GREEN, FONT_SMALL
from or_solver.core.image_graph_recognizer import recognize_colored_nodes
from or_solver.core.network_solver import prim_mst
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button


class MSTPage(tk.Frame, TableEditMixin):
    def __init__(self, master: tk.Widget, controller):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.n_nodes = tk.IntVar(value=5)
        self.node_labels_var = tk.StringVar(value="1 2 3 4 5")
        self.entries_built = False
        self.reference_image = None
        self.reference_photo = None
        self._build_header()

    def _build_header(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        ctrl = tk.Frame(hdr, bg="#d7ccc8")
        ctrl.pack(anchor="center", pady=6)
        tk.Label(ctrl, text="节点数:", bg="#d7ccc8", font=FONT_SMALL).pack(side="left")
        tk.Spinbox(ctrl, from_=2, to=20, textvariable=self.n_nodes,
                   width=4, font=FONT_SMALL).pack(side="left", padx=4)
        make_button(ctrl, "确  定", self._build_table, bg=BTN_GREEN, width=8).pack(side="left", padx=6)
        make_button(ctrl, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(side="left", padx=4)

        main = tk.Frame(self, bg="#f5f0e8")
        main.pack(fill="both", expand=True, padx=10, pady=6)

        self.image_panel = tk.Frame(main, bg="#f5f5f0", relief="groove", bd=1, width=420)
        self.image_panel.pack(side="left", fill="both", expand=False, padx=(0, 10))
        self.image_panel.pack_propagate(False)
        self._build_image_panel()

        body_shell = tk.Frame(main, bg="#f5f0e8")
        body_shell.pack(side="left", fill="both", expand=True)
        self.body_canvas = tk.Canvas(body_shell, bg="#f5f0e8", highlightthickness=0)
        self.body_canvas.pack(side="left", fill="both", expand=True)
        body_ysb = tk.Scrollbar(body_shell, orient="vertical", command=self.body_canvas.yview)
        body_ysb.pack(side="right", fill="y")
        body_xsb = tk.Scrollbar(body_shell, orient="horizontal", command=self.body_canvas.xview)
        body_xsb.pack(side="bottom", fill="x")
        self.body_canvas.configure(xscrollcommand=body_xsb.set, yscrollcommand=body_ysb.set)
        self.body = tk.Frame(self.body_canvas, bg="#f5f0e8")
        self.body_window = self.body_canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind(
            "<Configure>",
            lambda event: self.body_canvas.configure(scrollregion=self.body_canvas.bbox("all")),
        )
        self.body_canvas.bind(
            "<Configure>",
            lambda event: self.body_canvas.itemconfigure(self.body_window, width=event.width),
        )

        self.after(100, self._build_table)

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
            text="可粘贴/打开网络图\n再在右侧填写权重矩阵并求解",
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
            wraplength=360,
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
            title="选择最小支撑树题图",
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
        preview.thumbnail((380, 520))
        self.reference_photo = ImageTk.PhotoImage(preview)
        self.image_hint.pack_forget()
        self.image_label.config(image=self.reference_photo)

    def _clear_reference_image(self):
        self.reference_image = None
        self.reference_photo = None
        self.image_label.config(image="")
        if not self.image_hint.winfo_ismapped():
            self.image_hint.pack(fill="both", expand=True, padx=8, pady=8, before=self.image_label)

    def _recognize_reference_image_offline(self):
        if self.reference_image is None:
            messagebox.showwarning("离线识别", "请先粘贴或打开一张题图")
            return
        try:
            result = recognize_colored_nodes(self.reference_image)
        except Exception as exc:
            messagebox.showerror("离线识别失败", str(exc))
            return
        if result.nodes:
            self.n_nodes.set(len(result.nodes))
            self._build_table()
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", "离线识别完成。\n")
        if result.nodes:
            self.result_text.insert("end", f"识别到节点数: {len(result.nodes)}\n")
            self.result_text.insert("end", "请根据题图核对并填写权重矩阵或边表。\n")
        if result.notes:
            self.result_text.insert("end", "\n".join(result.notes))

    # ── TableEditMixin 接口 ──────────────────────────────
    def _entry_frame(self): return self.body

    def _entry_at(self, r, c):
        try:
            if hasattr(self, "dist_entries") and r < len(self.dist_entries) and c < len(self.dist_entries[r]):
                return self.dist_entries[r][c]
        except (IndexError, AttributeError):
            pass
        return None

    def _entry_default_bg(self, r, c):
        return "#f0f0f0" if r == c else "#eef8ef"

    def _all_entries(self):
        try:
            if hasattr(self, "dist_entries"):
                for i, row in enumerate(self.dist_entries):
                    for j, e in enumerate(row):
                        if i != j:
                            yield (i, j, e)
        except AttributeError:
            return

    # ── 建表 ────────────────────────────────────────────
    def _build_table(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._tbl_init_sel()
        n = self.n_nodes.get()
        self._sync_default_node_labels(n)

        top_row = tk.Frame(self.body, bg="#f5f0e8")
        top_row.grid(row=0, column=0, sticky="nw")

        table_box = tk.Frame(top_row, bg="#f5f0e8")
        table_box.grid(row=0, column=0, sticky="nw")
        tk.Label(
            table_box,
            text="权重矩阵（无连接填 inf 或留空，矩阵应对称）",
            bg="#f5f0e8",
            fg="#111",
            font=("微软雅黑", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        matrix_box = tk.Frame(table_box, bg="#d2c9bd", highlightthickness=1, highlightbackground="#a99f94")
        matrix_box.grid(row=1, column=0, sticky="nw")

        def cell_label(parent, text, bg, width=10, font=FONT_SMALL, fg="#222"):
            return tk.Label(parent, text=text, bg=bg, fg=fg, font=font,
                            width=width, relief="flat", bd=0)

        labels = self._node_labels(n)
        if n >= 10:
            cell_width = 4
            row_label_width = 3
        elif n >= 8:
            cell_width = 5
            row_label_width = 4
        else:
            cell_width = 6 if n >= 7 else 9
            row_label_width = 5 if n >= 7 else 8
        cell_label(matrix_box, "", "#f7efe2", width=row_label_width).grid(
            row=0, column=0, padx=1, pady=1, ipady=2, sticky="nsew"
        )
        for j, label in enumerate(labels):
            cell_label(matrix_box, label, "#f4d7a5", width=cell_width).grid(
                row=0, column=j + 1, padx=1, pady=1, ipady=2, sticky="nsew"
            )

        self.dist_entries: list[list[tk.Entry]] = []
        for i, label in enumerate(labels):
            cell_label(matrix_box, label, "#f7efe2", width=row_label_width).grid(
                row=i + 1, column=0, padx=1, pady=1, ipady=2, sticky="nsew"
            )
            row_e = []
            for j in range(n):
                e = tk.Entry(
                    matrix_box,
                    width=cell_width,
                    font=("微软雅黑", 8 if n >= 10 else 9),
                    justify="left",
                    relief="flat",
                    bd=0,
                    bg="#f0f0f0" if i == j else "#eef8ef",
                    highlightthickness=0,
                )
                if i == j:
                    e.insert(0, "0")
                    e.config(state="readonly")
                else:
                    self._bind_cell(e, i, j)
                    e.bind("<Control-v>", self._paste_from_clipboard)
                    e.bind("<Control-V>", self._paste_from_clipboard)
                e.grid(row=i + 1, column=j + 1, padx=1, pady=1, ipady=2, sticky="nsew")
                row_e.append(e)
            self.dist_entries.append(row_e)

        result_box = tk.Frame(
            top_row,
            bg="#f5f0e8",
            highlightthickness=1,
            highlightbackground="#d1c8bc",
        )
        result_box.grid(row=0, column=1, sticky="nsw", padx=(14, 0), pady=(28, 0))
        tk.Label(result_box, text="求解结果", bg="#f5f0e8",
                 fg="#111", font=("微软雅黑", 10, "bold")).grid(
                 row=0, column=0, sticky="w", padx=14, pady=(12, 8))
        self.result_text = tk.Text(
            result_box,
            height=12 if n >= 9 else 8,
            width=36,
            font=FONT_SMALL,
            bg="#fffde7",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#d1c8bc",
            wrap="word",
        )
        self.result_text.grid(row=1, column=0, padx=14, pady=(0, 14))

        step_box = tk.Frame(
            self.body,
            bg="#f5f0e8",
            highlightthickness=1,
            highlightbackground="#d1c8bc",
        )
        step_box.grid(row=1, column=0, sticky="we", pady=(10, 0))
        step_box.grid_columnconfigure(0, weight=1)
        step_box.grid_columnconfigure(1, weight=1)
        tk.Label(step_box, text="求解步骤 / 图示", bg="#f5f0e8",
                 fg="#111", font=("微软雅黑", 10, "bold")).grid(
                 row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 8))
        step_text_frame = tk.Frame(step_box, bg="#f5f0e8")
        step_text_frame.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        step_vsb = tk.Scrollbar(step_text_frame, orient="vertical")
        self.step_text = tk.Text(
            step_text_frame,
            height=7,
            width=52,
            font=("Consolas", 10),
            bg="#fffff0",
            yscrollcommand=step_vsb.set,
            wrap="word",
            state="disabled",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#d1c8bc",
        )
        step_vsb.config(command=self.step_text.yview)
        step_vsb.pack(side="right", fill="y")
        self.step_text.pack(side="left", fill="both", expand=True)
        self.chart_frame = tk.Frame(step_box, bg="#f5f5f0", relief="groove", bd=1, width=420, height=220)
        self.chart_frame.grid(row=1, column=1, padx=(0, 14), pady=(0, 14), sticky="nsew")
        self.chart_frame.grid_propagate(False)
        tk.Label(self.chart_frame, text="求解后显示最小支撑树图",
                 bg="#f5f5f0", fg="#888", font=("宋体", 9)).pack(expand=True)
        self.entries_built = True

    def _split_labels(self) -> list[str]:
        text = self.node_labels_var.get().strip()
        return [p for p in re.split(r"[\s,，]+", text) if p]

    def _node_labels(self, n: int) -> list[str]:
        labels = self._split_labels()
        if len(labels) < n:
            labels.extend(str(i + 1) for i in range(len(labels), n))
        return labels[:n]

    def _sync_default_node_labels(self, n: int) -> None:
        labels = self._split_labels()
        numeric_default = labels == [str(i + 1) for i in range(len(labels))]
        if not labels or numeric_default:
            self.node_labels_var.set(" ".join(str(i + 1) for i in range(n)))

    def _label_to_index(self, token: str, labels: list[str]) -> int:
        token = token.strip()
        normalized = {label.lower(): idx for idx, label in enumerate(labels)}
        if token.lower() in normalized:
            return normalized[token.lower()]
        try:
            index = int(token) - 1
        except ValueError as exc:
            raise ValueError(f"未知节点：{token}") from exc
        if index < 0 or index >= len(labels):
            raise ValueError(f"节点编号超出范围：{token}")
        return index

    def _labels_for_edge_text(self, text: str) -> list[str]:
        labels = self._split_labels()
        max_numeric = 0
        named_tokens: list[str] = []
        seen_names = {label.lower() for label in labels}
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = [p for p in re.split(r"\s*(?:--|-|,|，|\s+)\s*", line) if p]
            if len(parts) < 2:
                continue
            for token in parts[:2]:
                try:
                    max_numeric = max(max_numeric, int(token))
                except ValueError:
                    key = token.lower()
                    if key not in seen_names:
                        named_tokens.append(token)
                        seen_names.add(key)
        if max_numeric > len(labels):
            labels.extend(str(i + 1) for i in range(len(labels), max_numeric))
        labels.extend(named_tokens)
        return labels

    def _parse_edge_lines(self, text: str, labels: list[str]) -> list[tuple[int, int, float]]:
        edges: list[tuple[int, int, float]] = []
        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = [p for p in re.split(r"\s*(?:--|-|,|，|\s+)\s*", line) if p]
            if len(parts) != 3:
                raise ValueError(f"第 {line_no} 行格式应为：节点1 节点2 权重")
            u = self._label_to_index(parts[0], labels)
            v = self._label_to_index(parts[1], labels)
            try:
                weight = float(parts[2])
            except ValueError as exc:
                raise ValueError(f"第 {line_no} 行权重不是数字：{parts[2]}") from exc
            if u == v:
                raise ValueError(f"第 {line_no} 行不能连接同一节点")
            if weight < 0:
                raise ValueError("最小支撑树权重不能为负")
            edges.append((u, v, weight))
        if not edges:
            raise ValueError("请先输入边表")
        return edges

    def _load_edges_to_matrix(self):
        edge_text = self.edge_text.get("1.0", "end") if hasattr(self, "edge_text") else ""
        labels = self._labels_for_edge_text(edge_text)
        if not labels:
            messagebox.showwarning("输入错误", "请先填写节点名称")
            return
        try:
            edges = self._parse_edge_lines(edge_text, labels)
        except ValueError as exc:
            messagebox.showerror("边表错误", str(exc))
            return

        n = len(labels)
        if self.n_nodes.get() != n:
            self.n_nodes.set(n)
            self.node_labels_var.set(" ".join(labels))
            self._build_table()
            self.edge_text.delete("1.0", "end")
            self.edge_text.insert("end", edge_text)

        for i in range(n):
            for j in range(n):
                if i != j:
                    self.dist_entries[i][j].delete(0, "end")
        for u, v, weight in edges:
            for a, b in ((u, v), (v, u)):
                e = self.dist_entries[a][b]
                e.delete(0, "end")
                e.insert(0, f"{weight:g}")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", f"已导入 {len(edges)} 条无向边，可直接求解。")

    def _snapshot_entries(self) -> list[list[str]]:
        if not self.entries_built:
            return []
        return [[e.get() for e in row] for row in self.dist_entries]

    def _restore_entries(self, data: list[list[str]]) -> None:
        for i, row in enumerate(data):
            if i >= len(self.dist_entries):
                break
            for j, value in enumerate(row):
                if j < len(self.dist_entries[i]) and i != j:
                    self.dist_entries[i][j].delete(0, "end")
                    self.dist_entries[i][j].insert(0, value)

    def _delete_selected_node(self) -> None:
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        if cell is None:
            messagebox.showinfo("删除节点", "请先选中要删除的节点所在行或列")
            return
        n = self.n_nodes.get()
        if n <= 2:
            messagebox.showinfo("删除节点", "至少保留 2 个节点")
            return
        remove_idx = cell[0] if cell[0] < n else cell[1]
        old = self._snapshot_entries()
        data = [
            [value for j, value in enumerate(row) if j != remove_idx]
            for i, row in enumerate(old)
            if i != remove_idx
        ]
        self.n_nodes.set(n - 1)
        self._build_table()
        self._restore_entries(data)
        self.result_text.delete("1.0", "end")
        self.step_text.config(state="normal")
        self.step_text.delete("1.0", "end")
        self.step_text.config(state="disabled")
        for child in self.chart_frame.winfo_children():
            child.destroy()
        tk.Label(self.chart_frame, text="求解后自动显示最小支撑树图",
                 bg="#f5f5f0", fg="#888", font=("宋体", 9)).pack(expand=True)

    def _insert_selected_node(self) -> None:
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】生成输入表格")
            return
        cell = self._selected_cell()
        n = self.n_nodes.get()
        insert_idx = n if cell is None else min(cell[0], n - 1) + 1
        old = self._snapshot_entries()
        data = []
        for i in range(n + 1):
            if i == insert_idx:
                data.append([""] * (n + 1))
                continue
            old_i = i if i < insert_idx else i - 1
            row = []
            for j in range(n + 1):
                if j == insert_idx:
                    row.append("")
                else:
                    old_j = j if j < insert_idx else j - 1
                    row.append(old[old_i][old_j])
            data.append(row)
        self.n_nodes.set(n + 1)
        self._build_table()
        self._restore_entries(data)
        self.result_text.delete("1.0", "end")
        self.step_text.config(state="normal")
        self.step_text.delete("1.0", "end")
        self.step_text.config(state="disabled")
        for child in self.chart_frame.winfo_children():
            child.destroy()
        tk.Label(self.chart_frame, text="求解后自动显示最小支撑树图",
                 bg="#f5f5f0", fg="#888", font=("宋体", 9)).pack(expand=True)

    _insert_selected_row = _insert_selected_node
    _insert_selected_col = _insert_selected_node
    _delete_selected_row = _delete_selected_node
    _delete_selected_col = _delete_selected_node

    # ── 剪贴板粘贴 ───────────────────────────────────────
    def _paste_from_clipboard(self, event=None):
        try:
            text = self.body.clipboard_get()
        except Exception:
            return None

        if "\t" not in text and "\n" not in text.strip():
            w = event.widget if event else None
            if w:
                try:
                    if w.selection_present():
                        w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except Exception:
                    pass
                w.insert(tk.INSERT, text.strip())
            return "break"

        def _is_num(s: str) -> bool:
            s = s.strip()
            if s in ("", "-", "—", "inf", "∞", "INF"):
                return True
            try:
                float(s); return True
            except ValueError:
                return False

        def _cell_val(s: str) -> str:
            s = s.strip()
            if s in ("-", "—", "inf", "∞", "INF", ""):
                return ""
            try:
                float(s); return s
            except ValueError:
                return ""

        raw_rows = [[cell.strip() for cell in ln.split("\t")]
                    for ln in text.splitlines() if ln.strip()]
        if not raw_rows:
            return "break"

        def _as_int(cell: str) -> int | None:
            try:
                value = float(cell.strip())
            except ValueError:
                return None
            if value.is_integer():
                return int(value)
            return None

        def _is_header_row(row: list[str]) -> bool:
            nums = [_as_int(c) for c in row if c.strip()]
            nums = [n for n in nums if n is not None]
            return len(nums) >= 2 and nums == list(range(1, len(nums) + 1))

        rows = raw_rows[1:] if _is_header_row(raw_rows[0]) else raw_rows
        data: list[list[str]] = []
        for row_index, row in enumerate(rows, start=1):
            cells = row[:]
            if cells and _as_int(cells[0]) == row_index:
                cells = cells[1:]
            data.append(cells)
        if not data:
            return "break"

        n_data_cols = max(len(r) for r in data)
        cur_n = self.n_nodes.get()
        start_row, start_col = (0, 0)
        if event is not None:
            for r, row in enumerate(self.dist_entries):
                for c, entry in enumerate(row):
                    if entry is event.widget:
                        start_row, start_col = r, c
                        break
                else:
                    continue
                break
        nonempty_counts = [sum(1 for cell in row if _cell_val(cell)) for row in data]
        row_count = len(data)
        compact_upper_triangle = (
            row_count >= 2
            and nonempty_counts == [max(n_data_cols - i, 0) for i in range(row_count)]
            and all(bool(row and _cell_val(row[0])) for row in data)
        )
        triangular_without_diag = (
            row_count >= 2
            and nonempty_counts == [max(row_count - i - 1, 0) for i in range(row_count)]
            and all(i == row_count - 1 or bool(row and _cell_val(row[0])) for i, row in enumerate(data))
        )
        triangular_with_diag_slots = (
            row_count >= 2
            and n_data_cols >= row_count
            and all(
                all(not _cell_val(cell) for cell in data[i][:i + 1])
                and sum(1 for cell in data[i][i + 1:] if _cell_val(cell)) == row_count - i - 1
                for i in range(row_count)
            )
        )
        if compact_upper_triangle:
            effective_n = max(cur_n, start_col + n_data_cols, start_row + row_count)
        elif triangular_without_diag or triangular_with_diag_slots:
            effective_n = row_count
        else:
            effective_n = max(cur_n, start_col + n_data_cols, start_row + row_count)
        if effective_n > cur_n:
            self.n_nodes.set(effective_n)
            self.node_labels_var.set(" ".join(str(i + 1) for i in range(effective_n)))
            self._build_table()
            cur_n = effective_n

        for i in range(cur_n):
            for j in range(cur_n):
                if i != j:
                    self.dist_entries[i][j].delete(0, "end")

        for i, row in enumerate(data):
            target_i = start_row + i
            if target_i >= cur_n:
                break
            for j, cell in enumerate(row):
                if compact_upper_triangle:
                    target_j = start_col + i + j
                elif triangular_without_diag:
                    target_j = i + 1 + j
                else:
                    target_j = start_col + j
                if target_j >= cur_n or target_i == target_j:
                    continue
                val = _cell_val(cell)
                if val:
                    for a, b in ((target_i, target_j), (target_j, target_i)):
                        e = self.dist_entries[a][b]
                        e.delete(0, "end")
                        e.insert(0, val)
        return "break"

    # ── 求解 ────────────────────────────────────────────
    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】")
            return
        n = self.n_nodes.get()
        INF = math.inf
        matrix: list[list[float]] = []
        for i in range(n):
            row = []
            for j in range(n):
                v = self.dist_entries[i][j].get().strip()
                if i == j:
                    row.append(0.0)
                elif v in ("", "inf", "∞"):
                    row.append(INF)
                else:
                    try:
                        row.append(float(v))
                    except ValueError:
                        row.append(INF)
            matrix.append(row)

        # 对称化：取 min(w[i][j], w[j][i])
        for i in range(n):
            for j in range(i + 1, n):
                w = min(matrix[i][j], matrix[j][i])
                matrix[i][j] = matrix[j][i] = w

        result = prim_mst(matrix)
        labels = self._node_labels(n)

        self.result_text.delete("1.0", "end")
        if result.status != "found":
            self.result_text.insert("end", result.message)
            return

        self.result_text.insert("end", f"最小支撑树总权重: {result.total_weight:g}\n\n")
        self.result_text.insert("end", "选中边：\n")
        for u, v, w in result.edges:
            self.result_text.insert("end", f"  ({labels[u - 1]}, {labels[v - 1]})  权重 = {w:g}\n")

        # 步骤面板
        self.step_text.config(state="normal")
        self.step_text.delete("1.0", "end")
        self.step_text.tag_config("title",  foreground="#1a5276", font=("宋体", 10, "bold"))
        self.step_text.tag_config("step",   foreground="#196F3D", font=("Consolas", 10))
        self.step_text.tag_config("result", foreground="#922B21", font=("Consolas", 10, "bold"))
        self.step_text.insert("end", "【Prim 算法求解步骤】\n\n", "title")
        for line in result.steps:
            tag = "result" if "总权重" in line else "step"
            self.step_text.insert("end", line + "\n", tag)
        self.step_text.config(state="disabled")
        self.step_text.see("end")

        self._draw_chart(n, matrix, result.edges, result.total_weight, labels)

    # ── 绘图 ────────────────────────────────────────────
    def _draw_chart(self, n, matrix, mst_edges, total_weight, labels):
        import math as _math
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        for w in self.chart_frame.winfo_children():
            w.destroy()

        fig, ax = plt.subplots(figsize=(5.5, 3.8), dpi=90)
        fig.patch.set_facecolor("#f5f5f0")
        ax.set_facecolor("#fafafa")
        ax.set_title(f"最小支撑树  总权重 = {total_weight:g}",
                     fontsize=11, fontweight="bold", fontfamily="SimHei")
        ax.axis("off")

        # 节点坐标：均匀分布在圆上
        angles = [2 * _math.pi * i / n - _math.pi / 2 for i in range(n)]
        pos = {i: (_math.cos(angles[i]), _math.sin(angles[i])) for i in range(n)}

        mst_set = {(u - 1, v - 1) for u, v, _ in mst_edges} | {(v - 1, u - 1) for u, v, _ in mst_edges}
        INF = _math.inf

        # 画非MST边（灰色细线）
        for i in range(n):
            for j in range(i + 1, n):
                if matrix[i][j] < INF and (i, j) not in mst_set:
                    x0, y0 = pos[i]; x1, y1 = pos[j]
                    ax.plot([x0, x1], [y0, y1], color="#cccccc", linewidth=1, zorder=1)
                    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                    ax.text(mx, my, f"{matrix[i][j]:g}", fontsize=7,
                            color="#aaaaaa", ha="center", va="center", zorder=2)

        # 画MST边（红色粗线）
        for u, v, w in mst_edges:
            i, j = u - 1, v - 1
            x0, y0 = pos[i]; x1, y1 = pos[j]
            ax.plot([x0, x1], [y0, y1], color="#e53935", linewidth=2.5, zorder=3)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            ax.text(mx, my, f"{w:g}", fontsize=9, fontweight="bold",
                    color="#b71c1c", ha="center", va="center",
                    bbox=dict(fc="white", ec="none", pad=1), zorder=4)

        # 画节点
        for i in range(n):
            x, y = pos[i]
            ax.plot(x, y, "o", markersize=18, color="#1565c0", zorder=5)
            ax.text(x, y, labels[i], fontsize=9, fontweight="bold",
                    color="white", ha="center", va="center", zorder=6)

        ax.set_xlim(-1.35, 1.35)
        ax.set_ylim(-1.35, 1.35)
        plt.tight_layout(pad=0.3)

        canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas_widget.draw()
        canvas_widget.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    # ── 示例数据 ─────────────────────────────────────────
    def _load_example(self):
        self.n_nodes.set(6)
        self._build_table()
        # 经典6节点MST示例
        INF = ""
        data = [
            [INF, "6",  "1",  "5",  INF,  INF ],
            ["6", INF,  "5",  INF,  "3",  INF ],
            ["1", "5",  INF,  "5",  "6",  "4" ],
            ["5", INF,  "5",  INF,  INF,  "2" ],
            [INF, "3",  "6",  INF,  INF,  "6" ],
            [INF, INF,  "4",  "2",  "6",  INF ],
        ]
        n = 6
        for i in range(n):
            for j in range(n):
                if i != j:
                    self.dist_entries[i][j].delete(0, "end")
                    self.dist_entries[i][j].insert(0, data[i][j])
        if hasattr(self, "edge_text"):
            self.edge_text.delete("1.0", "end")
            self.edge_text.insert(
                "end",
                "\n".join(
                    [
                        "1 2 6",
                        "1 3 1",
                        "1 4 5",
                        "2 3 5",
                        "2 5 3",
                        "3 4 5",
                        "3 5 6",
                        "3 6 4",
                        "4 6 2",
                        "5 6 6",
                    ]
                ),
            )
