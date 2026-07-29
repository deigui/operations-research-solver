"""Cutting-stock model builders."""
from __future__ import annotations

from dataclasses import dataclass

from or_solver.core.lp_solver import LPResult, solve_integer_lp


@dataclass(frozen=True)
class EnumeratedCuttingStockModel:
    """Integer-programming form of an enumerated cutting-stock problem.

    x_j is the number of raw bars cut with pattern j.
    """

    c: list[float]
    A: list[list[float]]
    b: list[float]
    rels: list[str]
    maximize: bool


def build_enumerated_cutting_stock_model(
    patterns: list[list[float]],
    demands: list[float],
    waste: list[float] | None = None,
) -> EnumeratedCuttingStockModel:
    """Build an IP model from an already-enumerated cutting pattern table.

    Args:
        patterns: rows are finished-material types, columns are cutting schemes.
        demands: minimum demand for each finished-material type.
        waste: leftover amount or cost for each scheme. If omitted, minimize the
            number of raw bars used.
    """
    if not patterns:
        raise ValueError("下料方案表不能为空")
    if not demands:
        raise ValueError("需求量不能为空")
    if len(patterns) != len(demands):
        raise ValueError("下料品种数必须与需求量个数一致")

    n_patterns = len(patterns[0])
    if n_patterns == 0:
        raise ValueError("至少需要一个下料方案")
    for row in patterns:
        if len(row) != n_patterns:
            raise ValueError("每种下料的方案列数必须一致")
        if any(v < 0 for v in row):
            raise ValueError("下料件数不能为负")
    if any(v < 0 for v in demands):
        raise ValueError("需求量不能为负")

    if waste is None:
        c = [1.0] * n_patterns
    else:
        if len(waste) != n_patterns:
            raise ValueError("余料/成本系数个数必须与方案数一致")
        if any(v < 0 for v in waste):
            raise ValueError("余料/成本系数不能为负")
        c = list(waste)

    return EnumeratedCuttingStockModel(
        c=c,
        A=[list(row) for row in patterns],
        b=list(demands),
        rels=["≥"] * len(demands),
        maximize=False,
    )


def solve_enumerated_cutting_stock(
    patterns: list[list[float]],
    demands: list[float],
    waste: list[float] | None = None,
) -> LPResult:
    """Solve an already-enumerated cutting-stock problem."""
    model = build_enumerated_cutting_stock_model(patterns, demands, waste)
    return solve_integer_lp(
        model.c,
        model.A,
        model.b,
        model.rels,
        maximize=model.maximize,
        integer_vars=True,
    )
