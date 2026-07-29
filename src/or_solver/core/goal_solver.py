"""Goal-programming solvers."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GoalStageResult:
    priority: int
    objective_value: float
    x: list[float]


@dataclass
class PreemptiveGoalResult:
    status: str
    x: list[float] = field(default_factory=list)
    objective_values: list[float] = field(default_factory=list)
    stage_results: list[GoalStageResult] = field(default_factory=list)
    actual_values: list[float] = field(default_factory=list)
    message: str = ""


def solve_preemptive_goal_lp(
    priority_objectives: list[list[float]],
    A: list[list[float]],
    b: list[float],
    rels: list[str],
    *,
    tol: float = 1e-7,
) -> PreemptiveGoalResult:
    """Solve a preemptive goal-programming LP by lexicographic optimization."""
    from scipy.optimize import linprog

    if not priority_objectives:
        return PreemptiveGoalResult(status="error", message="缺少优先级目标")

    n = len(priority_objectives[0])
    A_ub: list[list[float]] = []
    b_ub: list[float] = []
    A_eq: list[list[float]] = []
    b_eq: list[float] = []

    for i, rel in enumerate(rels):
        if rel in ("≤", "<=", "<"):
            A_ub.append(A[i])
            b_ub.append(b[i])
        elif rel in ("≥", ">=", ">"):
            A_ub.append([-a for a in A[i]])
            b_ub.append(-b[i])
        else:
            A_eq.append(A[i])
            b_eq.append(b[i])

    bounds = [(0, None)] * n
    stage_results: list[GoalStageResult] = []
    objective_values: list[float] = []
    current_x: list[float] = []

    for idx, obj in enumerate(priority_objectives, start=1):
        if len(obj) != n:
            return PreemptiveGoalResult(status="error", message=f"P{idx}目标维度不一致")

        res = linprog(
            obj,
            A_ub=A_ub or None,
            b_ub=b_ub or None,
            A_eq=A_eq or None,
            b_eq=b_eq or None,
            bounds=bounds,
            method="highs",
        )
        if not res.success:
            return PreemptiveGoalResult(status="infeasible", message=res.message)

        value = float(res.fun)
        current_x = list(res.x)
        objective_values.append(value)
        stage_results.append(
            GoalStageResult(priority=idx, objective_value=value, x=current_x)
        )

        A_eq.append(list(obj))
        b_eq.append(value if abs(value) > tol else 0.0)

    actual = [sum(A[i][j] * current_x[j] for j in range(n)) for i in range(len(A))]
    return PreemptiveGoalResult(
        status="optimal",
        x=current_x,
        objective_values=objective_values,
        stage_results=stage_results,
        actual_values=actual,
    )
