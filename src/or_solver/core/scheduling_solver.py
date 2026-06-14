"""合理排班问题求解器（循环班次线性规划）。

零 tkinter 依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SchedulingResult:
    status: str             # "optimal" | "infeasible"
    x: list[float] = field(default_factory=list)   # 各班次开班人数
    total: float = 0.0
    actual_on_duty: list[float] = field(default_factory=list)
    message: str = ""


def solve_shift_schedule(
    demands: list[float],
    work_days: int,
) -> SchedulingResult:
    """求解循环班次排班问题。

    每人连续工作 work_days 天，n = len(demands) 个时间段循环。
    目标：最小化总人数，满足各时段在班人数 ≥ demands[i]。

    Args:
        demands: 各时段最少需求人数列表。
        work_days: 每人连续工作天数（k）。
    """
    from scipy.optimize import linprog

    n = len(demands)
    A_ub: list[list[float]] = []
    b_ub: list[float] = []

    for i in range(n):
        row = [0.0] * n
        for j in range(work_days):
            row[(i - j) % n] = 1.0
        A_ub.append([-v for v in row])
        b_ub.append(-demands[i])

    res = linprog(
        [1.0] * n,
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=[(0, None)] * n,
        method="highs",
    )

    if not res.success:
        return SchedulingResult(status="infeasible", message=res.message)

    x = list(res.x)
    total = sum(x)
    actual = [sum(x[(i - j) % n] for j in range(work_days)) for i in range(n)]

    return SchedulingResult(
        status="optimal",
        x=x,
        total=total,
        actual_on_duty=actual,
    )
