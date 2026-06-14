"""预测求解器单元测试。"""
from or_solver.core.forecast_solver import moving_average, exponential_smoothing, linear_regression


def test_moving_average():
    data = [10, 12, 13, 15, 14, 16, 18]
    result = moving_average(data, 3)
    assert len(result.fitted) == len(data) - 2
    assert result.next_value > 0


def test_exponential_smoothing():
    data = [10, 12, 13, 15, 14]
    result = exponential_smoothing(data, alpha=0.3)
    assert len(result.fitted) == len(data)
    assert result.next_value > 0


def test_linear_regression():
    data = [2, 4, 5, 4, 5, 7, 8, 9]
    result = linear_regression(data)
    assert "slope" in result.params
    assert "r2" in result.params
    assert 0 <= result.params["r2"] <= 1
