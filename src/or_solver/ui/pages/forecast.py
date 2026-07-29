"""预测方法页（移动平均 / 指数平滑 / 回归分析）。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from or_solver.constants import FONT_SMALL
from or_solver.core.forecast_solver import (
    exponential_smoothing,
    linear_regression,
    moving_average,
    seasonal_trend,
    weighted_moving_average,
)
from or_solver.ui.widgets import make_button


class ForecastPage(tk.Frame):
    def __init__(self, master: tk.Widget, controller, mode: str = "移动平均法"):
        super().__init__(master, bg="#f5f0e8")
        self.controller = controller
        self.mode = mode
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg="#d7ccc8")
        hdr.pack(fill="x")
        make_button(hdr, "求  解", self._solve, bg="#e53935", fg="white", width=8).pack(anchor="center", pady=6)

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
        elif self.mode == "加权移动平均":
            tk.Label(param_frame, text="权重（旧→新，空格分隔）:", bg="#f5f0e8", font=FONT_SMALL).pack(anchor="w")
            self.param_weights = tk.StringVar(value="0.2 0.3 0.5")
            tk.Entry(param_frame, textvariable=self.param_weights, width=18,
                     font=FONT_SMALL).pack(anchor="w")
        elif self.mode == "指数平滑法":
            tk.Label(param_frame, text="平滑系数 α (0~1):", bg="#f5f0e8", font=FONT_SMALL).pack(anchor="w")
            self.param_alpha = tk.DoubleVar(value=0.3)
            tk.Entry(param_frame, textvariable=self.param_alpha, width=8,
                     font=FONT_SMALL).pack(anchor="w")
        elif self.mode == "趋势投影法":
            tk.Label(param_frame, text="预测提前期:", bg="#f5f0e8", font=FONT_SMALL).pack(anchor="w")
            self.param_ahead = tk.IntVar(value=1)
            tk.Spinbox(param_frame, from_=1, to=24, textvariable=self.param_ahead,
                       width=5, font=FONT_SMALL).pack(anchor="w")
        elif self.mode == "趋势季节因素":
            tk.Label(param_frame, text="季节周期长度:", bg="#f5f0e8", font=FONT_SMALL).pack(anchor="w")
            self.param_season = tk.IntVar(value=4)
            tk.Spinbox(param_frame, from_=2, to=24, textvariable=self.param_season,
                       width=5, font=FONT_SMALL).pack(anchor="w")

        self.result_text = tk.Text(body, height=12, width=45, font=FONT_SMALL, bg="#fffde7")
        self.result_text.grid(row=1, column=2, rowspan=6, padx=10, pady=4, sticky="nw")

    def _solve(self):
        raw = self.data_text.get("1.0", "end").strip().split()
        try:
            data = [float(v) for v in raw if v]
        except ValueError:
            messagebox.showerror("输入错误", "数据格式不正确")
            return
        if len(data) < 2:
            messagebox.showerror("输入错误", "至少需要2个数据")
            return

        self.result_text.delete("1.0", "end")

        if self.mode == "移动平均法":
            n = self.param_n.get()
            result = moving_average(data, n)
            self.result_text.insert("end", f"移动平均预测（N={n}）：\n\n")
            offset = n - 1
            for i, p in enumerate(result.fitted):
                self.result_text.insert("end", f"  第{i + offset + 1}期预测值: {p:.4f}\n")
            self.result_text.insert("end", f"\n下一期预测值: {result.next_value:.4f}")

        elif self.mode == "加权移动平均":
            try:
                weights = [float(v) for v in self.param_weights.get().split() if v]
                result = weighted_moving_average(data, weights)
            except ValueError as e:
                messagebox.showerror("输入错误", str(e))
                return
            self.result_text.insert("end", "加权移动平均预测：\n\n")
            self.result_text.insert(
                "end",
                "  归一化权重: " + ", ".join(f"{w:.4f}" for w in result.params["weights"]) + "\n\n",
            )
            offset = len(result.params["weights"]) - 1
            for i, p in enumerate(result.fitted):
                self.result_text.insert("end", f"  第{i + offset + 1}期预测值: {p:.4f}\n")
            self.result_text.insert("end", f"\n下一期预测值: {result.next_value:.4f}")

        elif self.mode == "指数平滑法":
            alpha = self.param_alpha.get()
            result = exponential_smoothing(data, alpha)
            self.result_text.insert("end", f"指数平滑预测（α={alpha}）：\n\n")
            for i, p in enumerate(result.fitted):
                self.result_text.insert("end", f"  第{i + 1}期平滑值: {p:.4f}\n")
            self.result_text.insert("end", f"\n下一期预测值: {result.next_value:.4f}")

        elif self.mode in ("回归分析法", "趋势投影法"):
            ahead = self.param_ahead.get() if self.mode == "趋势投影法" else 1
            result = linear_regression(data, periods_ahead=ahead)
            a = result.params["slope"]
            b = result.params["intercept"]
            r2 = result.params["r2"]
            n = len(data)
            self.result_text.insert("end", f"{self.mode}：\n\n")
            self.result_text.insert("end", f"  回归方程: Y = {a:.4f}·t + {b:.4f}\n")
            self.result_text.insert("end", f"  拟合优度 R² = {r2:.4f}\n\n")
            self.result_text.insert("end", "  各期拟合值：\n")
            for i, fitted_v in enumerate(result.fitted):
                self.result_text.insert("end",
                    f"    第{i+1}期: 实际={data[i]}  预测={fitted_v:.4f}\n")
            self.result_text.insert("end",
                f"\n预测值（第{n+ahead}期）: {result.next_value:.4f}")

        elif self.mode == "趋势季节因素":
            try:
                result = seasonal_trend(data, self.param_season.get())
            except ValueError as e:
                messagebox.showerror("输入错误", str(e))
                return
            self.result_text.insert("end", "趋势季节因素预测：\n\n")
            self.result_text.insert(
                "end",
                "  季节指数: "
                + ", ".join(f"S{i+1}={v:.4f}" for i, v in enumerate(result.params["seasonal_indices"]))
                + "\n\n",
            )
            for i, p in enumerate(result.fitted):
                self.result_text.insert("end", f"  第{i+1}期: 实际={data[i]}  拟合={p:.4f}\n")
            self.result_text.insert("end", f"\n下一期预测值: {result.next_value:.4f}")
