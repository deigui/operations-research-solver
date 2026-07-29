from or_solver.core.scheduling_solver import solve_shift_schedule


def test_shift_schedule_uses_integer_staffing():
    result = solve_shift_schedule([20, 24, 25, 20, 28, 32, 34], 5)

    assert result.status == "optimal"
    assert all(abs(v - round(v)) < 1e-7 for v in result.x)
    assert abs(result.total - round(result.total)) < 1e-7
    assert all(
        actual + 1e-7 >= demand
        for actual, demand in zip(result.actual_on_duty, [20, 24, 25, 20, 28, 32, 34])
    )


def test_shift_schedule_rejects_invalid_work_days():
    result = solve_shift_schedule([1, 2, 3], 4)

    assert result.status == "infeasible"
