"""预测方法核心算法。

零 tkinter 依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ForecastResult:
    method: str
    fitted: list[float] = field(default_factory=list)   # 各期拟合/平滑值
    next_value: float = 0.0
    params: dict = field(default_factory=dict)           # 方法特定参数


def moving_average(data: list[float], n_periods: int) -> ForecastResult:
    """移动平均法。

    Args:
        data: 历史数据（时间正序）。
        n_periods: 移动步数 N。
    """
    preds = [
        sum(data[i - n_periods + 1 : i + 1]) / n_periods
        for i in range(n_periods - 1, len(data))
    ]
    return ForecastResult(
        method="移动平均法",
        fitted=preds,
        next_value=preds[-1] if preds else 0.0,
        params={"N": n_periods},
    )


def exponential_smoothing(data: list[float], alpha: float) -> ForecastResult:
    """指数平滑法。

    Args:
        data: 历史数据。
        alpha: 平滑系数（0 < α < 1）。
    """
    s = data[0]
    smoothed = [s]
    for v in data[1:]:
        s = alpha * v + (1 - alpha) * s
        smoothed.append(s)
    return ForecastResult(
        method="指数平滑法",
        fitted=smoothed,
        next_value=smoothed[-1],
        params={"alpha": alpha},
    )


def linear_regression(data: list[float]) -> ForecastResult:
    """线性回归法（最小二乘）。

    Returns fitted values, R², slope, intercept, and next period prediction.
    """
    import numpy as np

    n = len(data)
    x = np.arange(1, n + 1, dtype=float)
    y = np.array(data, dtype=float)
    a, b = np.polyfit(x, y, 1)

    fitted = [float(a * xi + b) for xi in x]
    ss_res = sum((y[i] - fitted[i]) ** 2 for i in range(n))
    ss_tot = float(sum((v - y.mean()) ** 2 for v in y))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    return ForecastResult(
        method="回归分析法",
        fitted=fitted,
        next_value=float(a * (n + 1) + b),
        params={"slope": float(a), "intercept": float(b), "r2": r2},
    )
