"""运输问题 / 指派问题核心求解器。

零 tkinter 依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

BIG_M = 1e7  # 大M法禁止路线标记值


def parse_cost(s: str) -> float:
    """解析单元格成本字符串，支持 "M"/"m" 大M值。"""
    s = s.strip()
    if not s:
        return 0.0
    if s.upper() == "M":
        return BIG_M
    return float(s)


@dataclass
class TransportResult:
    status: str              # "optimal" | "infeasible"
    allocation: np.ndarray = field(default_factory=lambda: np.array([]))
    total_cost: float = 0.0
    message: str = ""
    dummy_added: str = ""    # "row" | "col" | ""


def solve_transport(
    cost: np.ndarray,
    supply: np.ndarray,
    demand: np.ndarray,
) -> TransportResult:
    """求解运输问题（供需自动平衡）。

    Args:
        cost:   m×n 费用矩阵（numpy 数组）。
        supply: 长度 m 的供应量向量。
        demand: 长度 n 的需求量向量。

    Returns:
        TransportResult，包含分配矩阵和总费用。
    """
    from scipy.optimize import linprog

    cost = np.array(cost, dtype=float)
    supply = np.array(supply, dtype=float)
    demand = np.array(demand, dtype=float)

    dummy = ""
    total_s, total_d = supply.sum(), demand.sum()
    if total_s > total_d:
        demand = np.append(demand, total_s - total_d)
        cost = np.hstack([cost, np.zeros((len(supply), 1))])
        dummy = "col"
    elif total_d > total_s:
        supply = np.append(supply, total_d - total_s)
        cost = np.vstack([cost, np.zeros((1, len(demand)))])
        dummy = "row"

    m, n = cost.shape
    c_flat = cost.flatten()

    A_eq: list[list[float]] = []
    b_eq: list[float] = []
    for i in range(m):
        row = [0.0] * (m * n)
        for j in range(n):
            row[i * n + j] = 1.0
        A_eq.append(row)
        b_eq.append(float(supply[i]))
    for j in range(n):
        row = [0.0] * (m * n)
        for i in range(m):
            row[i * n + j] = 1.0
        A_eq.append(row)
        b_eq.append(float(demand[j]))

    res = linprog(c_flat, A_eq=A_eq, b_eq=b_eq, bounds=[(0, None)] * (m * n), method="highs")

    if not res.success:
        return TransportResult(status="infeasible", message=res.message)

    allocation = res.x.reshape(m, n)
    return TransportResult(
        status="optimal",
        allocation=allocation,
        total_cost=res.fun,
        dummy_added=dummy,
    )


@dataclass
class AssignmentResult:
    status: str
    row_ind: list[int] = field(default_factory=list)
    col_ind: list[int] = field(default_factory=list)
    total_cost: float = 0.0
    message: str = ""


def solve_assignment(cost: np.ndarray) -> AssignmentResult:
    """求解指派问题（匈牙利算法）。"""
    from scipy.optimize import linear_sum_assignment

    try:
        row_ind, col_ind = linear_sum_assignment(cost)
        total = float(cost[row_ind, col_ind].sum())
        return AssignmentResult(
            status="optimal",
            row_ind=list(row_ind),
            col_ind=list(col_ind),
            total_cost=total,
        )
    except Exception as e:
        return AssignmentResult(status="infeasible", message=str(e))
