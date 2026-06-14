"""决策分析准则求解器。

支持：最大最小、最大最大、后悔值、期望值、乐观系数、等可能性。
零 tkinter 依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DecisionResult:
    criterion: str
    scores: list[float]
    best_value: float
    best_index: int       # 0-based
    extra: dict = field(default_factory=dict)  # criterion-specific data


def solve_maximin(mat: list[list[float]]) -> DecisionResult:
    """最大最小准则（悲观准则）。"""
    scores = [min(row) for row in mat]
    best = max(scores)
    return DecisionResult("最大最小准则", scores, best, scores.index(best))


def solve_maximax(mat: list[list[float]]) -> DecisionResult:
    """最大最大准则（乐观准则）。"""
    scores = [max(row) for row in mat]
    best = max(scores)
    return DecisionResult("最大最大准则", scores, best, scores.index(best))


def solve_regret(mat: list[list[float]]) -> DecisionResult:
    """后悔值准则（Minimax Regret）。"""
    m = len(mat)
    n = len(mat[0]) if mat else 0
    col_max = [max(mat[i][j] for i in range(m)) for j in range(n)]
    regret = [[col_max[j] - mat[i][j] for j in range(n)] for i in range(m)]
    scores = [max(row) for row in regret]
    best = min(scores)
    return DecisionResult(
        "后悔值准则",
        scores,
        best,
        scores.index(best),
        extra={"regret_matrix": regret},
    )


def solve_expected_value(
    mat: list[list[float]], probs: list[float]
) -> DecisionResult:
    """期望值准则（已知概率）。"""
    n = len(mat[0]) if mat else 0
    scores = [sum(mat[i][j] * probs[j] for j in range(n)) for i in range(len(mat))]
    best = max(scores)
    return DecisionResult("期望值准则", scores, best, scores.index(best))


def solve_hurwicz(mat: list[list[float]], alpha: float) -> DecisionResult:
    """乐观系数准则（Hurwicz）。"""
    scores = [alpha * max(row) + (1 - alpha) * min(row) for row in mat]
    best = max(scores)
    return DecisionResult(
        "乐观系数准则",
        scores,
        best,
        scores.index(best),
        extra={"alpha": alpha},
    )


def solve_laplace(mat: list[list[float]]) -> DecisionResult:
    """等可能性准则（Laplace）。"""
    n = len(mat[0]) if mat else 1
    p = 1.0 / n
    scores = [sum(row) * p for row in mat]
    best = max(scores)
    return DecisionResult(
        "等可能性准则",
        scores,
        best,
        scores.index(best),
        extra={"p": p},
    )
