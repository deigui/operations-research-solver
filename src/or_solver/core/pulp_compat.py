"""Compatibility helpers for PuLP-backed integer programming solvers."""
from __future__ import annotations

import warnings
from typing import Any


def solve_mip_problem(prob: Any, pulp_module: Any, msg: int = 0) -> int:
    """Solve a PuLP model with the non-deprecated CBC entry point when available."""
    coin_solver = pulp_module.COIN_CMD(msg=msg)
    if coin_solver.available():
        return prob.solve(coin_solver)

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message=".*PULP_CBC_CMD is deprecated.*",
        )
        return prob.solve(pulp_module.PULP_CBC_CMD(msg=msg))
