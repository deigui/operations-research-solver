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


def solve_perfect_information(mat: list[list[float]], probs: list[float]) -> DecisionResult:
    """全情报准则：计算完全信息期望值和完全信息价值。"""
    n = len(mat[0]) if mat else 0
    ev_scores = [sum(row[j] * probs[j] for j in range(n)) for row in mat]
    ev_best = max(ev_scores)
    state_best = [max(row[j] for row in mat) for j in range(n)]
    ev_with_pi = sum(state_best[j] * probs[j] for j in range(n))
    return DecisionResult(
        "全情报准则",
        ev_scores,
        ev_with_pi,
        ev_scores.index(ev_best),
        extra={
            "expected_value_without_information": ev_best,
            "expected_value_with_perfect_information": ev_with_pi,
            "expected_value_of_perfect_information": ev_with_pi - ev_best,
            "state_best_values": state_best,
        },
    )


def solve_expected_utility(mat: list[list[float]], probs: list[float]) -> DecisionResult:
    """效用值准则：按概率计算期望效用，选择期望效用最大的方案。"""
    result = solve_expected_value(mat, probs)
    result.criterion = "效用值准则"
    return result


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
