"""Matplotlib 图表嵌入 tkinter 的帮助函数。"""
from __future__ import annotations

import tkinter as tk


def embed_figure(fig, parent: tk.Widget) -> None:
    """将 matplotlib Figure 嵌入 tkinter 容器，并销毁旧内容。"""
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    for w in parent.winfo_children():
        w.destroy()

    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
    plt.close(fig)


def draw_bar_chart(
    parent: tk.Widget,
    categories: list[str],
    series: dict[str, list[float]],
    title: str = "",
    ylabel: str = "",
    figsize: tuple[float, float] = (5.5, 3.5),
) -> None:
    """绘制分组柱状图并嵌入 tkinter 容器。

    Args:
        categories: x 轴标签。
        series: {"系列名": [值, ...], ...}
    """
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=figsize, dpi=90)
    fig.patch.set_facecolor("#f5f5f0")
    ax.set_facecolor("#fafafa")

    n = len(categories)
    n_series = len(series)
    width = 0.35
    offsets = np.linspace(-(n_series - 1) * width / 2, (n_series - 1) * width / 2, n_series)
    colors = ["#aed6f1", "#f1948a", "#a9dfbf", "#f9e79f"]
    edge_colors = ["#2980b9", "#c0392b", "#1e8449", "#d4ac0d"]
    idx = np.arange(n)

    for k, (label, values) in enumerate(series.items()):
        bars = ax.bar(
            idx + offsets[k],
            values,
            width,
            label=label,
            color=colors[k % len(colors)],
            edgecolor=edge_colors[k % len(edge_colors)],
        )
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h + 0.3,
                    str(int(h)),
                    ha="center",
                    fontsize=7,
                    color=edge_colors[k % len(edge_colors)],
                )

    ax.set_xticks(idx)
    ax.set_xticklabels(categories, fontfamily="SimHei", fontsize=8, rotation=30)
    if ylabel:
        ax.set_ylabel(ylabel, fontfamily="SimHei", fontsize=9)
    if title:
        ax.set_title(title, fontfamily="SimHei", fontsize=11, fontweight="bold")
    ax.legend(prop={"family": "SimHei", "size": 8})
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout(pad=0.3)
    embed_figure(fig, parent)
