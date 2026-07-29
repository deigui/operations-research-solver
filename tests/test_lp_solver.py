"""线性规划求解器单元测试。"""
from or_solver.utils.expr_parser import parse_lp_data_matrix, parse_lp_expr, parse_table_lp_expr
from or_solver.core.goal_solver import solve_preemptive_goal_lp
from or_solver.core.lp_solver import solve_lp, solve_integer_lp, simplex_steps


def test_lp_basic_max():
    c = [15.0, 10.0]
    A = [[1.0, 1.0], [1.0, 0.0]]
    b = [6.0, 4.0]
    rels = ["≤", "≤"]
    result = solve_lp(c, A, b, rels, maximize=True)
    assert result.status == "optimal"
    assert abs(result.obj_value - 80.0) < 1e-4


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


def test_parse_table_lp_expr():
    raw = """
    max
    15 10 7 13 9
    5 10 7 <= 8000
    6 4 8 6 4 <= 12000
    3 2 2 3 2 <= 10000
    """
    parsed = parse_table_lp_expr(raw)
    assert parsed["maximize"] is True
    assert parsed["n_vars"] == 5
    assert parsed["n_cons"] == 3
    assert parsed["obj_coefs"] == {0: 15.0, 1: 10.0, 2: 7.0, 3: 13.0, 4: 9.0}
    assert parsed["constraints"][0]["coefs"] == {0: 5.0, 1: 10.0, 2: 7.0}
    assert parsed["constraints"][0]["rel"] == "≤"
    assert parsed["constraints"][0]["rhs"] == 8000.0


def test_table_lp_expr_can_solve():
    raw = """
    max
    15 10 7 13 9
    5 10 7 0 0 <= 8000
    6 4 8 6 4 <= 12000
    3 2 2 3 2 <= 10000
    """
    parsed = parse_table_lp_expr(raw)
    c = [parsed["obj_coefs"].get(j, 0.0) for j in range(parsed["n_vars"])]
    A = [
        [con["coefs"].get(j, 0.0) for j in range(parsed["n_vars"])]
        for con in parsed["constraints"]
    ]
    b = [con["rhs"] for con in parsed["constraints"]]
    rels = [con["rel"] for con in parsed["constraints"]]
    result = solve_lp(c, A, b, rels, maximize=parsed["maximize"], compute_sensitivity=False)

    assert result.status == "optimal"
    assert abs(result.obj_value - 29400.0) < 1e-4
    assert abs(float(result.x[0]) - 1600.0) < 1e-4
    assert abs(float(result.x[4]) - 600.0) < 1e-4


def test_parse_lp_expr_all_zero_objective():
    raw = """
    max Z = 0

    s.t.
      2x1 <= 300
      3x2 <= 540
      2x1 + 2x2 <= 440

      x1 >= 0
      x2 >= 0
    """
    parsed = parse_lp_expr(raw)
    assert parsed["maximize"] is True
    assert parsed["n_vars"] == 2
    assert parsed["n_cons"] == 3
    assert parsed["obj_coefs"] == {}


def test_parse_mixed_integer_expr_with_y_binary_variables():
    raw = """
    min f=8x1+15x2+10x3+12x4+7x5+9x6+18x7+16x8+x9+11x10+12x11+8x12+19x13+4x14+15x15+370000y1+300000y2+375000y3+500000y4
    s.t.
    x1+x2+x3<=30000
    x4+x5+x6-20000y1<=0
    x7+x8+x9-40000y2<=0
    x10+x11+x12-30000y3<=0
    x13+x14+x15-10000y4<=0
    x1+x4+x7+x10+x13=30000
    x2+x5+x8+x11+x14=20000
    x3+x6+x9+x12+x15=20000
    """
    parsed = parse_lp_expr(raw)

    assert parsed["maximize"] is False
    assert parsed["n_vars"] == 19
    assert parsed["n_cons"] == 8
    assert parsed["var_names"][:3] == ["x1", "x2", "x3"]
    assert parsed["var_names"][15:] == ["y1", "y2", "y3", "y4"]
    assert parsed["var_types"][:15] == ["I"] * 15
    assert parsed["var_types"][15:] == ["B"] * 4
    assert parsed["obj_coefs"][15] == 370000.0
    assert parsed["constraints"][1]["coefs"][15] == -20000.0


def test_solve_mixed_integer_expr_with_binary_setup_variables():
    raw = """
    min f=8x1+15x2+10x3+12x4+7x5+9x6+18x7+16x8+x9+11x10+12x11+8x12+19x13+4x14+15x15+370000y1+300000y2+375000y3+500000y4
    s.t.
    x1+x2+x3<=30000
    x4+x5+x6-20000y1<=0
    x7+x8+x9-40000y2<=0
    x10+x11+x12-30000y3<=0
    x13+x14+x15-10000y4<=0
    x1+x4+x7+x10+x13=30000
    x2+x5+x8+x11+x14=20000
    x3+x6+x9+x12+x15=20000
    """
    parsed = parse_lp_expr(raw)
    c = [parsed["obj_coefs"].get(j, 0.0) for j in range(parsed["n_vars"])]
    A = [
        [con["coefs"].get(j, 0.0) for j in range(parsed["n_vars"])]
        for con in parsed["constraints"]
    ]
    b = [con["rhs"] for con in parsed["constraints"]]
    rels = [con["rel"] for con in parsed["constraints"]]

    result = solve_integer_lp(
        c,
        A,
        b,
        rels,
        maximize=parsed["maximize"],
        mixed_var_types=parsed["var_types"],
    )

    assert result.status == "optimal"
    assert abs(result.obj_value - 880000.0) < 1e-6
    assert result.x[0] == 30000.0
    assert result.x[7] == 20000.0
    assert result.x[8] == 20000.0
    assert result.x[16] == 1.0


def test_solve_investment_site_model_uses_continuous_x_and_integer_y():
    raw = """
    max z = 1.15x4 + 1.28x5 + 1.40x6 + 1.06x11
    s.t.
    x1 + x7 = 10
    x2 + x6 - 1.06x7 + x8 = 0
    -1.15x1 + x3 + x5 - 1.06x8 + x9 = 0
    -1.15x2 + x4 - 1.06x9 + x10 = 0
    -1.15x3 - 1.06x10 + x11 = 0
    x1 - 4y1 >= 0
    x1 - 16y1 >= 0
    x5 - 5y2 >= 0
    x5 - 3y2 >= 0
    x6 - 2y3 = 0
    y3 <= 4
    """
    parsed = parse_lp_expr(raw)
    c = [parsed["obj_coefs"].get(j, 0.0) for j in range(parsed["n_vars"])]
    A = [
        [con["coefs"].get(j, 0.0) for j in range(parsed["n_vars"])]
        for con in parsed["constraints"]
    ]
    b = [con["rhs"] for con in parsed["constraints"]]
    rels = [con["rel"] for con in parsed["constraints"]]
    var_types = ["C"] * 11 + ["I"] * 3

    result = solve_integer_lp(
        c,
        A,
        b,
        rels,
        maximize=parsed["maximize"],
        mixed_var_types=var_types,
    )

    assert result.status == "optimal"
    assert abs(result.obj_value - 14.810566016) < 1e-6
    assert abs(result.x[5] - 8.0) < 1e-6
    assert abs(result.x[13] - 4.0) < 1e-6


def test_solve_preemptive_goal_programming_example():
    raw = """
    min z = dp1 + dm2 + dm3 + dm4 + 2dm5
    s.t.
    200x1 + 300x2 + dm1 - dp1 = 68000
    200x1 + 300x2 + dm2 - dp2 = 60000
    250x1 + 125x2 + dm3 - dp3 = 70000
    x1 + dm4 - dp4 = 200
    x2 + dm5 - dp5 = 120
    """
    parsed = parse_lp_expr(raw)
    c = [parsed["obj_coefs"].get(j, 0.0) for j in range(parsed["n_vars"])]
    A = [
        [con["coefs"].get(j, 0.0) for j in range(parsed["n_vars"])]
        for con in parsed["constraints"]
    ]
    b = [con["rhs"] for con in parsed["constraints"]]
    rels = [con["rel"] for con in parsed["constraints"]]
    names = parsed["var_names"]
    idx = {name: j for j, name in enumerate(names)}

    def obj(terms):
        values = [0.0] * parsed["n_vars"]
        for name, coef in terms:
            values[idx[name]] = coef
        return values

    result = solve_preemptive_goal_lp(
        [
            obj([("dp1", 1.0), ("dm2", 1.0)]),
            obj([("dm3", 1.0)]),
            obj([("dm4", 1.0), ("dm5", 2.0)]),
        ],
        A,
        b,
        rels,
    )

    assert result.status == "optimal"
    assert abs(result.x[idx["x1"]] - 250.0) < 1e-6
    assert abs(result.x[idx["x2"]] - 60.0) < 1e-6
    assert abs(result.x[idx["dm5"]] - 60.0) < 1e-6
    assert [round(v, 6) for v in result.objective_values] == [0.0, 0.0, 120.0]


def test_lp_paste_auto_expand_layout():
    import tkinter as tk
    from or_solver.ui.pages.lp import LPPage

    root = tk.Tk()
    root.withdraw()

    class Controller:
        def show_menu(self):
            pass

    page = LPPage(root, Controller(), "线性规划问题")
    root.update_idletasks()
    page.n_vars.set(2)
    page.n_cons.set(2)
    page._build_table()

    page.body.clipboard_clear()
    page.body.clipboard_append(
        "1 2 3\n"
        "4 5 6 7\n"
        "8 9 10 11\n"
    )
    page._paste_from_clipboard(type("E", (), {"widget": page.obj_entries[0]})(), 0, 0)

    assert page.n_vars.get() >= 3
    assert page.n_cons.get() >= 2
    assert page.obj_entries[0].get() == "1"
    assert page.obj_entries[1].get() == "2"
    assert page.obj_entries[2].get() == "3"

    root.destroy()


def test_parse_lp_data_matrix():
    raw = """
    2 0 2
    0 3 1
    2 2 2
    1.2 1.5 3
    1 2 3
    """
    parsed = parse_lp_data_matrix(raw)
    assert parsed["n_vars"] == 2
    assert parsed["n_cons"] == 5
    assert parsed["obj_coefs"] == {}
    assert parsed["constraints"][0]["coefs"] == {0: 2.0}
    assert parsed["constraints"][0]["rhs"] == 2.0
