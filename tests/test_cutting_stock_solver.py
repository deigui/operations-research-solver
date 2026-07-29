from or_solver.core.cutting_stock_solver import (
    build_enumerated_cutting_stock_model,
    solve_enumerated_cutting_stock,
)


def test_build_enumerated_cutting_stock_model_from_pattern_table():
    model = build_enumerated_cutting_stock_model(
        patterns=[
            [2, 1],
            [0, 2],
            [1, 0],
        ],
        demands=[10, 8, 4],
        waste=[0.1, 0.3],
    )

    assert model.maximize is False
    assert model.c == [0.1, 0.3]
    assert model.A == [[2, 1], [0, 2], [1, 0]]
    assert model.b == [10, 8, 4]
    assert model.rels == ["≥", "≥", "≥"]


def test_solve_enumerated_cutting_stock_uses_integer_pattern_counts():
    result = solve_enumerated_cutting_stock(
        patterns=[
            [2, 1],
            [0, 2],
            [1, 0],
        ],
        demands=[10, 8, 4],
        waste=[0.1, 0.3],
    )

    assert result.status == "optimal"
    assert all(abs(v - round(v)) < 1e-6 for v in result.x)
    assert result.x == [4, 4]
    assert abs(result.obj_value - 1.6) < 1e-6
