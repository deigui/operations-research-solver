"""最短路求解页。"""
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
from or_solver.core.network_solver import dijkstra
from or_solver.ui.mixins import TableEditMixin
from or_solver.ui.widgets import make_button


class ShortestPathPage(tk.Frame, TableEditMixin):
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
        self.image_panel = tk.Frame(main, bg="#f5f5f0", relief="groove", bd=1, width=620)
        self.image_panel.pack(side="left", fill="both", expand=False, padx=(0, 10))
        self.image_panel.pack_propagate(False)
        self._build_image_panel()
        self.body = tk.Frame(main, bg="#f5f0e8")
        self.body.pack(side="left", fill="both", expand=False)
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
            text="可粘贴/打开网络图\n再在右侧生成矩阵并求解",
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
            title="选择最短路题图",
            filetypes=[
                ("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                ("所有文件", "*.*"),
            ],
        )
        if not path:
            return
        try:
            image = Image.open(path)
            self._set_reference_image(image)
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
        if not result.nodes:
            self.result_text.delete("1.0", "end")
            self.result_text.insert("end", "\n".join(result.notes) or "离线识别未得到结果。")
            return

        self.node_labels_var.set(" ".join(result.nodes))
        self.n_nodes.set(len(result.nodes))
        self._build_table()
        if result.source in result.nodes:
            self.src_var.set(result.nodes.index(result.source) + 1)
        if result.target in result.nodes:
            self.dst_var.set(result.nodes.index(result.target) + 1)
        if result.edges:
            self.edge_text.delete("1.0", "end")
            self.edge_text.insert(
                "end",
                "\n".join(f"{u} {v} {w:g}" for u, v, w in result.edges),
            )
            self._load_edges_to_matrix()

        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", "离线识别完成。\n")
        self.result_text.insert("end", f"节点名称: {' '.join(result.nodes)}\n")
        if result.edges:
            self.result_text.insert("end", f"已填入 {len(result.edges)} 条边到矩阵。\n")
        if result.notes:
            self.result_text.insert("end", "\n".join(result.notes))

    def _set_recognition_status(self, text: str):
        if hasattr(self, "result_text"):
            self.result_text.delete("1.0", "end")
            self.result_text.insert("end", text)

    # ── TableEditMixin 接口 ───────────────────────────────
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

        table_box = tk.Frame(self.body, bg="#f5f0e8")
        table_box.grid(row=0, column=0, sticky="nw")
        tk.Label(
            table_box,
            text="距离矩阵（无连接填 inf 或留空）",
            bg="#f5f0e8",
            fg="#111",
            font=("微软雅黑", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        matrix = tk.Frame(table_box, bg="#d2c9bd", highlightthickness=1, highlightbackground="#a99f94")
        matrix.grid(row=1, column=0, sticky="nw")

        def cell_label(parent, text, bg, width=10, font=FONT_SMALL, fg="#222"):
            return tk.Label(parent, text=text, bg=bg, fg=fg, font=font,
                            width=width, relief="flat", bd=0)

        labels = self._node_labels(n)
        cell_width = 6 if n >= 10 else 10
        row_label_width = 5 if n >= 10 else 9
        cell_label(matrix, "", "#f7efe2", width=row_label_width).grid(
            row=0, column=0, padx=1, pady=1, ipady=2, sticky="nsew"
        )
        for j, label in enumerate(labels):
            cell_label(matrix, label, "#f4d7a5", width=cell_width).grid(
                row=0, column=j + 1, padx=1, pady=1, ipady=2, sticky="nsew"
            )

        self.dist_entries: list[list[tk.Entry]] = []
        for i, label in enumerate(labels):
            cell_label(matrix, label, "#f7efe2", width=row_label_width).grid(
                row=i + 1, column=0, padx=1, pady=1, ipady=2, sticky="nsew"
            )
            row_e = []
            for j in range(n):
                e = tk.Entry(
                    matrix,
                    width=cell_width,
                    font=("微软雅黑", 9),
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

        control_bar = tk.Frame(self.body, bg="#f5f0e8")
        control_bar.grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Label(control_bar, text="起点:", bg="#f5f0e8", font=FONT_SMALL).pack(side="left")
        self.src_var = tk.IntVar(value=1)
        tk.Spinbox(control_bar, from_=1, to=n, textvariable=self.src_var,
                   width=4, font=FONT_SMALL).pack(side="left", padx=(4, 16))
        tk.Label(control_bar, text="终点:", bg="#f5f0e8", font=FONT_SMALL).pack(side="left")
        self.dst_var = tk.IntVar(value=n)
        tk.Spinbox(control_bar, from_=1, to=n, textvariable=self.dst_var,
                   width=4, font=FONT_SMALL).pack(side="left", padx=(4, 0))

        lower = tk.Frame(self.body, bg="#f5f0e8")
        lower.grid(row=2, column=0, sticky="nw", pady=(8, 0))

        result_box = tk.Frame(
            lower,
            bg="#f5f0e8",
            highlightthickness=1,
            highlightbackground="#d1c8bc",
        )
        result_box.grid(row=0, column=0, sticky="nw")
        tk.Label(result_box, text="求解结果", bg="#f5f0e8",
                 fg="#111", font=("微软雅黑", 10, "bold")).grid(
                 row=0, column=0, sticky="w", padx=14, pady=(12, 8))
        self.result_text = tk.Text(
            result_box,
            height=5,
            width=42,
            font=FONT_SMALL,
            bg="#fffde7",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#d1c8bc",
            wrap="word",
        )
        self.result_text.grid(row=1, column=0, padx=14, pady=(0, 14))

        edge_frame = tk.Frame(
            lower,
            bg="#f5f0e8",
            highlightthickness=1,
            highlightbackground="#d1c8bc",
        )
        edge_frame.grid(row=0, column=1, sticky="nw", padx=(8, 0))
        tk.Label(edge_frame, text="边表输入", bg="#f5f0e8",
                 fg="#111", font=("微软雅黑", 10, "bold")).grid(
                 row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 8))
        tk.Label(edge_frame, text="节点名称:", bg="#f5f0e8", font=FONT_SMALL).grid(
            row=1, column=0, sticky="w", padx=(14, 0))
        labels_entry = tk.Entry(edge_frame, textvariable=self.node_labels_var, width=34, font=FONT_SMALL)
        labels_entry.grid(row=1, column=1, sticky="we", padx=(4, 14))
        tk.Label(
            edge_frame,
            text="每行：起点 终点 距离，如 S A 3",
            bg="#f5f0e8",
            font=FONT_SMALL,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 6))
        self.edge_text = tk.Text(
            edge_frame,
            height=6,
            width=40,
            font=("Consolas", 10),
            bg="#ffffff",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#a99f94",
        )
        self.edge_text.grid(row=3, column=0, columnspan=2, sticky="we", padx=14)
        make_button(edge_frame, "从边表生成矩阵", self._load_edges_to_matrix,
                    bg="#26a69a", width=14).grid(
                    row=4, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 14))
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
        if not token:
            raise ValueError("节点名不能为空")
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

    def _parse_edge_lines(self, text: str, labels: list[str]) -> list[tuple[int, int, float]]:
        edges: list[tuple[int, int, float]] = []
        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = [p for p in re.split(r"\s*(?:->|,|，|\s+)\s*", line) if p]
            if len(parts) != 3:
                raise ValueError(f"第 {line_no} 行格式应为：起点 终点 距离")
            u = self._label_to_index(parts[0], labels)
            v = self._label_to_index(parts[1], labels)
            try:
                weight = float(parts[2])
            except ValueError as exc:
                raise ValueError(f"第 {line_no} 行距离不是数字：{parts[2]}") from exc
            if weight < 0:
                raise ValueError("Dijkstra 不支持负权边")
            edges.append((u, v, weight))
        if not edges:
            raise ValueError("请先输入边表")
        return edges

    def _load_edges_to_matrix(self):
        labels = self._split_labels()
        edge_text = self.edge_text.get("1.0", "end") if hasattr(self, "edge_text") else ""
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
            e = self.dist_entries[u][v]
            e.delete(0, "end")
            e.insert(0, f"{weight:g}")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", f"已导入 {len(edges)} 条边，可直接求解。")

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
        def shifted(value: int) -> int:
            if value > remove_idx + 1:
                return value - 1
            if value == remove_idx + 1:
                return min(value, n - 1)
            return value

        src = shifted(self.src_var.get())
        dst = shifted(self.dst_var.get())
        self.n_nodes.set(n - 1)
        self._build_table()
        self._restore_entries(data)
        self.src_var.set(max(1, min(src, n - 1)))
        self.dst_var.set(max(1, min(dst, n - 1)))
        self.result_text.delete("1.0", "end")

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
        src = self.src_var.get()
        dst = self.dst_var.get()
        self.n_nodes.set(n + 1)
        self._build_table()
        self._restore_entries(data)
        self.src_var.set(src + 1 if src > insert_idx else src)
        self.dst_var.set(dst + 1 if dst > insert_idx else dst)
        self.result_text.delete("1.0", "end")

    _insert_selected_row = _insert_selected_node
    _insert_selected_col = _insert_selected_node
    _delete_selected_row = _delete_selected_node
    _delete_selected_col = _delete_selected_node

    # ── 剪贴板粘贴 ───────────────────────────────────────
    def _paste_from_clipboard(self, event=None):
        """Ctrl+V 从剪贴板粘贴 TSV 距离矩阵。

        兼容 Excel 直接复制的表格：
        - 自动跳过非数字标题行 / 标题列
        - '-' / '—' 识别为无连接（inf / 留空）
        - 若粘贴数据维度与当前节点数不符，自动扩展节点数并重建表格
        """
        try:
            text = self.body.clipboard_get()
        except Exception:
            return None

        # 单值：走正常粘贴
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
                return True          # 视为有效（表示 inf 或空）
            try:
                float(s); return True
            except ValueError:
                return False

        raw_rows = [ln.split("\t") for ln in text.strip().splitlines() if ln.strip()]
        if not raw_rows:
            return "break"

        # 跳过标题行（首行存在非数字非空单元格）
        skip_row = 1 if any(not _is_num(c) and c.strip() for c in raw_rows[0]) else 0
        # 跳过标签列（各数据行首列存在非数字非空）
        skip_col = 0
        for row in raw_rows[skip_row:]:
            if row and not _is_num(row[0]) and row[0].strip():
                skip_col = 1; break

        data = [[row[c] for c in range(skip_col, len(row))]
                for row in raw_rows[skip_row:]]
        if not data:
            return "break"

        new_n = max(len(r) for r in data)
        cur_n = self.n_nodes.get()

        # 自动扩展：数据维度大于当前节点数时重建
        if new_n > cur_n:
            self.n_nodes.set(new_n)
            self._build_table()
            cur_n = new_n

        def _cell_val(s: str) -> str:
            """将单元格文字转换为距离矩阵条目（inf→留空，数字→原样）。"""
            s = s.strip()
            if s in ("-", "—", "inf", "∞", "INF", ""):
                return ""        # 留空表示无连接
            try:
                float(s)
                return s
            except ValueError:
                return ""

        # 计算列偏移：若粘贴列数 = 矩阵阶数-1，说明用户复制时
        # 遗漏了第一列（全为"-"的对角列），数据从矩阵第1列开始。
        n_data_cols = max(len(r) for r in data)
        col_offset = 1 if n_data_cols == cur_n - 1 else 0

        # 若数据实际覆盖的最大列索引超出当前矩阵，扩展节点数
        effective_n = n_data_cols + col_offset
        if effective_n > cur_n:
            self.n_nodes.set(effective_n)
            self._build_table()
            cur_n = effective_n

        for i, row in enumerate(data):
            if i >= cur_n:
                break
            for j, cell in enumerate(row):
                target_j = j + col_offset
                if target_j >= cur_n or i == target_j:   # 跳过对角线
                    continue
                val = _cell_val(cell)
                e = self.dist_entries[i][target_j]
                e.delete(0, "end")
                if val:
                    e.insert(0, val)
        return "break"

    # ── 求解 ────────────────────────────────────────────
    def _solve(self):
        if not self.entries_built:
            messagebox.showwarning("提示", "请先点击【确定】")
            return
        n = self.n_nodes.get()
        INF = math.inf
        dist_matrix: list[list[float]] = []
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
            dist_matrix.append(row)

        src = self.src_var.get() - 1
        dst = self.dst_var.get() - 1
        result = dijkstra(dist_matrix, src, dst)
        labels = self._node_labels(n)

        self.result_text.delete("1.0", "end")
        if result.status == "no_path":
            self.result_text.insert("end", result.message)
        else:
            self.result_text.insert("end", f"最短路长度: {result.distance}\n")
            path_labels = [labels[i - 1] for i in result.path]
            self.result_text.insert("end", f"最短路径: {' → '.join(path_labels)}")
