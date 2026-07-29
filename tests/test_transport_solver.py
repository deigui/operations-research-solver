"""运输问题求解器单元测试。"""
import numpy as np
from or_solver.core.transport_solver import solve_transport, solve_assignment, parse_cost


def test_parse_cost():
    assert parse_cost("M") == 1e7
    assert parse_cost("m") == 1e7
    assert parse_cost("3.5") == 3.5
    assert parse_cost("") == 0.0


def test_balanced_transport():
    cost = [[2, 3, 1], [5, 4, 8], [5, 6, 8]]
    supply = [120, 80, 80]
    demand = [150, 70, 60]
    result = solve_transport(cost, supply, demand)
    assert result.status == "optimal"
    assert result.total_cost > 0


def test_unbalanced_supply_exceeds():
    cost = [[3, 2], [4, 5]]
    supply = [100, 80]
    demand = [60, 90]
    result = solve_transport(cost, supply, demand)
    assert result.status == "optimal"
    assert result.dummy_added == "col"


def test_supply_exceeds_adds_dummy_destination_standard_example():
    cost = [[1800, 1700, 1550], [1600, 1500, 1750]]
    supply = [3500, 2500]
    demand = [2500, 1000, 2000]
    result = solve_transport(cost, supply, demand)

    assert result.status == "optimal"
    assert result.dummy_added == "col"
    assert result.allocation.shape == (2, 4)
    assert abs(result.allocation[:, 3].sum() - 500) < 1e-6
    assert abs(result.total_cost - 8800000.0) < 1e-6


def test_assignment():
    cost = np.array([[4, 2, 8], [2, 3, 7], [3, 1, 6]], dtype=float)
    result = solve_assignment(cost)
    assert result.status == "optimal"
    assert len(result.row_ind) == 3
