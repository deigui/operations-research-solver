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


def weighted_moving_average(data: list[float], weights: list[float]) -> ForecastResult:
    """加权移动平均法，weights 按时间从旧到新排列。"""
    if not weights:
        raise ValueError("权重不能为空")
    total_w = sum(weights)
    if total_w == 0:
        raise ValueError("权重和不能为0")
    weights = [w / total_w for w in weights]
    n = len(weights)
    if len(data) < n:
        raise ValueError("历史数据数量不能少于权重个数")
    fitted = [
        sum(data[i - n + 1 + k] * weights[k] for k in range(n))
        for i in range(n - 1, len(data))
    ]
    return ForecastResult(
        method="加权移动平均",
        fitted=fitted,
        next_value=fitted[-1],
        params={"weights": weights},
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


def linear_regression(data: list[float], periods_ahead: int = 1) -> ForecastResult:
    """线性回归法 / 趋势投影法（最小二乘）。

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
        next_value=float(a * (n + periods_ahead) + b),
        params={"slope": float(a), "intercept": float(b), "r2": r2, "periods_ahead": periods_ahead},
    )


def seasonal_trend(data: list[float], season_length: int) -> ForecastResult:
    """趋势季节因素法：线性趋势 × 乘法季节指数。"""
    if season_length < 2:
        raise ValueError("季节周期至少为2")
    if len(data) < season_length * 2:
        raise ValueError("至少需要两个完整季节周期的数据")

    trend = linear_regression(data)
    fitted_trend = trend.fitted
    ratios = [data[i] / fitted_trend[i] if fitted_trend[i] else 1.0 for i in range(len(data))]
    seasonal = []
    for s in range(season_length):
        vals = [ratios[i] for i in range(s, len(ratios), season_length)]
        seasonal.append(sum(vals) / len(vals))
    avg = sum(seasonal) / season_length
    seasonal = [v / avg for v in seasonal]

    fitted = [
        fitted_trend[i] * seasonal[i % season_length]
        for i in range(len(data))
    ]
    next_index = len(data)
    a = trend.params["slope"]
    b = trend.params["intercept"]
    next_value = (a * (next_index + 1) + b) * seasonal[next_index % season_length]
    return ForecastResult(
        method="趋势季节因素",
        fitted=fitted,
        next_value=float(next_value),
        params={
            "season_length": season_length,
            "seasonal_indices": seasonal,
            "slope": a,
            "intercept": b,
            "r2": trend.params["r2"],
        },
    )
