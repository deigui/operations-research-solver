"""线性规划求解器单元测试。"""
from or_solver.core.lp_solver import solve_lp, solve_integer_lp, simplex_steps


def test_lp_basic_max():
    c = [15.0, 10.0]
    A = [[1.0, 1.0], [1.0, 0.0]]
    b = [6.0, 4.0]
    rels = ["≤", "≤"]
    result = solve_lp(c, A, b, rels, maximize=True)
    assert result.status == "optimal"
    assert abs(result.obj_value - 70.0) < 1e-4


def test_lp_min():
    c = [1.0, 2.0]
    A = [[1.0, 1.0]]
    b = [4.0]
    rels = ["≥"]
    result = solve_lp(c, A, b, rels, maximize=False)
    assert result.status == "optimal"
    assert abs(result.obj_value - 4.0) < 1e-4


def test_integer_lp():
    c = [1.0, 1.0]
    A = [[2.0, 1.0], [1.0, 2.0]]
    b = [7.0, 7.0]
    rels = ["≤", "≤"]
    result = solve_integer_lp(c, A, b, rels, maximize=True, integer_vars=True)
    assert result.status == "optimal"
    assert abs(result.obj_value - round(result.obj_value)) < 1e-4


def test_simplex_steps():
    c = [5.0, 4.0]
    A = [[6.0, 4.0], [1.0, 2.0]]
    b = [24.0, 6.0]
    steps = simplex_steps(c, A, b, maximize=True)
    assert any("最优" in s["title"] for s in steps)
