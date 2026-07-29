"""合理排班问题求解器（循环班次线性规划）。

零 tkinter 依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from or_solver.core.pulp_compat import solve_mip_problem


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
    try:
        import pulp
    except ImportError as exc:
        return SchedulingResult(status="infeasible", message=f"missing pulp: {exc}")

    n = len(demands)
    if n == 0:
        return SchedulingResult(status="infeasible", message="period count must be positive")
    if work_days < 1 or work_days > n:
        return SchedulingResult(status="infeasible", message="work_days must be between 1 and period count")
    if any(v < 0 for v in demands):
        return SchedulingResult(status="infeasible", message="demands must be non-negative")

    prob = pulp.LpProblem("ShiftScheduling", pulp.LpMinimize)
    xs = [
        prob.add_variable(f"x{i+1}", lowBound=0, cat="Integer")
        for i in range(n)
    ]
    prob += pulp.lpSum(xs)
    for i in range(n):
        prob += pulp.lpSum(xs[(i - j) % n] for j in range(work_days)) >= demands[i]

    solve_mip_problem(prob, pulp, msg=0)
    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        return SchedulingResult(status="infeasible", message=f"solver status: {status}")

    x = [float(pulp.value(v) or 0.0) for v in xs]
    total = sum(x)
    actual = [sum(x[(i - j) % n] for j in range(work_days)) for i in range(n)]

    return SchedulingResult(
        status="optimal",
        x=x,
        total=total,
        actual_on_duty=actual,
    )
