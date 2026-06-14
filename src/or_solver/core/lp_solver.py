"""线性规划 / 整数规划核心求解器。

零 tkinter 依赖，所有函数均可独立单测。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class LPResult:
    status: str          # "optimal" | "infeasible" | "unbounded" | "error"
    x: list[float] = field(default_factory=list)
    obj_value: float = 0.0
    message: str = ""
    # 灵敏度分析
    shadow_prices: list[float] = field(default_factory=list)
    c_lower: list[float] = field(default_factory=list)
    c_upper: list[float] = field(default_factory=list)
    c_diff: list[float] = field(default_factory=list)
    b_lower: list[float] = field(default_factory=list)
    b_upper: list[float] = field(default_factory=list)
    actual_values: list[float] = field(default_factory=list)


def solve_lp(
    c: list[float],
    A: list[list[float]],
    b: list[float],
    rels: list[str],
    maximize: bool,
    compute_sensitivity: bool = True,
) -> LPResult:
    """求解连续线性规划并返回灵敏度分析数据。

    Args:
        c: 目标函数系数（最大化时原始符号，内部取反）。
        A: 约束系数矩阵。
        b: 约束右端项。
        rels: 约束关系列表，元素为 "≤"、"≥" 或 "="。
        maximize: True 表示最大化。
        compute_sensitivity: 是否计算灵敏度区间（默认 True）。
    """
    from scipy.optimize import linprog

    n = len(c)
    m = len(b)
    obj = [-ci for ci in c] if maximize else list(c)

    A_ub: list[list[float]] = []
    b_ub: list[float] = []
    A_eq: list[list[float]] = []
    b_eq: list[float] = []
    ub_idx: list[int] = []
    eq_idx: list[int] = []

    for i, rel in enumerate(rels):
        if rel in ("≤", "<=", "<"):
            A_ub.append(A[i])
            b_ub.append(b[i])
            ub_idx.append(i)
        elif rel in ("≥", ">=", ">"):
            A_ub.append([-a for a in A[i]])
            b_ub.append(-b[i])
            ub_idx.append(i)
        else:
            A_eq.append(A[i])
            b_eq.append(b[i])
            eq_idx.append(i)

    bounds = [(0, None)] * n
    res = linprog(
        obj,
        A_ub=A_ub or None,
        b_ub=b_ub or None,
        A_eq=A_eq or None,
        b_eq=b_eq or None,
        bounds=bounds,
        method="highs",
    )

    if not res.success:
        return LPResult(status="infeasible", message=res.message)

    x = list(res.x)
    opt = (-res.fun if maximize else res.fun)
    actual = [sum(A[i][j] * x[j] for j in range(n)) for i in range(m)]

    result = LPResult(
        status="optimal",
        x=x,
        obj_value=opt,
        actual_values=actual,
    )

    if not compute_sensitivity:
        return result

    # ── 对偶价格 ──────────────────────────────────────────
    INF = 1e30
    ub_dual = (
        list(res.ineqlin.marginals)
        if (hasattr(res, "ineqlin") and res.ineqlin is not None)
        else [0.0] * len(A_ub)
    )
    eq_dual = (
        list(res.eqlin.marginals)
        if (hasattr(res, "eqlin") and res.eqlin is not None)
        else [0.0] * len(A_eq)
    )
    shadow: list[float] = []
    ui, ei = 0, 0
    for rel in rels:
        if rel in ("≤", "<=", "<"):
            sp = ub_dual[ui] if ui < len(ub_dual) else 0.0
            ui += 1
            shadow.append(-sp if maximize else sp)
        elif rel in ("≥", ">=", ">"):
            sp = ub_dual[ui] if ui < len(ub_dual) else 0.0
            ui += 1
            shadow.append(sp if maximize else sp)
        else:
            sp = eq_dual[ei] if ei < len(eq_dual) else 0.0
            ei += 1
            shadow.append(-sp if maximize else sp)

    result.shadow_prices = shadow

    # ── 目标系数范围（基矩阵法）──────────────────────────
    try:
        A_np = np.array(A_ub, dtype=float)
        b_np = np.array(b_ub, dtype=float)
        ms = len(A_ub)
        A_std = np.hstack([A_np, np.eye(ms)])
        c_std = np.array(obj + [0.0] * ms)
        n_std = n + ms

        s_vals = b_np - A_np @ np.array(x)
        all_vals = np.concatenate([x, s_vals])

        basic_idx = sorted([j for j in range(n_std) if all_vals[j] > 1e-6])
        if len(basic_idx) < ms:
            cands = sorted(range(n_std), key=lambda j: -all_vals[j])
            for j in cands:
                if j not in basic_idx:
                    basic_idx.append(j)
                if len(basic_idx) == ms:
                    break
        basic_idx = sorted(basic_idx[:ms])

        B = A_std[:, basic_idx]
        B_inv = np.linalg.inv(B)
        c_B = c_std[basic_idx]

        rc = np.array(
            [c_std[k] - float(c_B @ (B_inv @ A_std[:, k])) for k in range(n_std)]
        )
        non_basic = [k for k in range(n_std) if k not in basic_idx]

        c_lo: list[float] = []
        c_hi: list[float] = []
        c_diff: list[float] = []

        for j in range(n):
            if j in basic_idx:
                bi = basic_idx.index(j)
                r_lo, r_hi = [], []
                for k in non_basic:
                    y = float((B_inv @ A_std[:, k])[bi])
                    rck = rc[k]
                    if abs(y) < 1e-10:
                        continue
                    ratio = -rck / y
                    if y > 0:
                        r_lo.append(ratio)
                    else:
                        r_hi.append(ratio)
                d_lo = max(r_lo) if r_lo else -INF
                d_hi = min(r_hi) if r_hi else INF
                c_lo.append(c[j] + d_lo if d_lo > -INF else -INF)
                c_hi.append(c[j] + d_hi if d_hi < INF else INF)
                c_diff.append(0.0)
            else:
                c_lo.append(-INF)
                c_hi.append(c[j] + rc[j])
                c_diff.append(rc[j])

        result.c_lower = c_lo
        result.c_upper = c_hi
        result.c_diff = c_diff

        # ── 约束右端项范围（扰动法）────────────────────────
        orig_duals = list(res.ineqlin.marginals) if (
            hasattr(res, "ineqlin") and res.ineqlin is not None
        ) else []
        b_lo2: list[float] = []
        b_hi2: list[float] = []

        for i in range(len(b_ub)):
            # 向下搜索
            lo_d, hi_d = -1e8, 0.0
            found_lo = None
            for _ in range(60):
                mid = (lo_d + hi_d) / 2
                bt = list(b_ub)
                bt[i] = b_ub[i] + mid
                r2 = linprog(
                    obj,
                    A_ub=A_ub or None,
                    b_ub=bt or None,
                    A_eq=A_eq or None,
                    b_eq=b_eq or None,
                    bounds=bounds,
                    method="highs",
                )
                if (
                    r2.success
                    and hasattr(r2, "ineqlin")
                    and r2.ineqlin is not None
                    and np.allclose(r2.ineqlin.marginals, orig_duals, atol=1e-4)
                ):
                    found_lo = mid
                    lo_d = mid
                else:
                    hi_d = mid
            b_lo2.append(b[i] + found_lo if found_lo is not None else -INF)

            # 向上搜索
            lo_d, hi_d = 0.0, 1e8
            found_hi = None
            for _ in range(60):
                mid = (lo_d + hi_d) / 2
                bt = list(b_ub)
                bt[i] = b_ub[i] + mid
                r2 = linprog(
                    obj,
                    A_ub=A_ub or None,
                    b_ub=bt or None,
                    A_eq=A_eq or None,
                    b_eq=b_eq or None,
                    bounds=bounds,
                    method="highs",
                )
                if (
                    r2.success
                    and hasattr(r2, "ineqlin")
                    and r2.ineqlin is not None
                    and np.allclose(r2.ineqlin.marginals, orig_duals, atol=1e-4)
                ):
                    found_hi = mid
                    lo_d = mid
                else:
                    hi_d = mid
            b_hi2.append(b[i] + found_hi if found_hi is not None else INF)

        result.b_lower = b_lo2
        result.b_upper = b_hi2

    except Exception:
        n_ub = len(A_ub)
        result.c_lower = [-INF] * n
        result.c_upper = [INF] * n
        result.c_diff = [0.0] * n
        result.b_lower = [-INF] * n_ub
        result.b_upper = [INF] * n_ub

    return result


def solve_integer_lp(
    c: list[float],
    A: list[list[float]],
    b: list[float],
    rels: list[str],
    maximize: bool,
    integer_vars: list[int] | None = None,
    binary_vars: bool = False,
    mixed_var_types: list[str] | None = None,
) -> LPResult:
    """使用 PuLP 求解整数 / 混合整数 / 0-1 规划。

    Args:
        integer_vars: 指定整数变量的0-based索引列表；None=全连续；True=全整数。
        binary_vars: True 表示全部 0-1 变量。
        mixed_var_types: 长度=n 的列表，元素 "C"/"I"/"B"，用于混合整数规划。
    """
    try:
        import pulp
    except ImportError as exc:
        return LPResult(status="error", message=f"缺少 pulp 库：{exc}")

    n = len(c)
    sense = pulp.LpMaximize if maximize else pulp.LpMinimize
    prob = pulp.LpProblem("IP", sense)

    if binary_vars:
        xs = [pulp.LpVariable(f"x{j+1}", cat="Binary") for j in range(n)]
    elif mixed_var_types:
        xs = []
        for j in range(n):
            vtype = mixed_var_types[j] if j < len(mixed_var_types) else "C"
            if vtype == "B":
                xs.append(pulp.LpVariable(f"x{j+1}", cat="Binary"))
            elif vtype == "I":
                xs.append(pulp.LpVariable(f"x{j+1}", lowBound=0, cat="Integer"))
            else:
                xs.append(pulp.LpVariable(f"x{j+1}", lowBound=0, cat="Continuous"))
    elif integer_vars is True:
        xs = [pulp.LpVariable(f"x{j+1}", lowBound=0, cat="Integer") for j in range(n)]
    else:
        int_set = set(integer_vars or [])
        xs = [
            pulp.LpVariable(
                f"x{j+1}",
                lowBound=0,
                cat="Integer" if j in int_set else "Continuous",
            )
            for j in range(n)
        ]

    prob += pulp.lpSum(c[j] * xs[j] for j in range(n))

    REL_MAP = {"≤": "<=", "≥": ">=", "=": "==", "<=": "<=", ">=": ">="}
    for i, rel in enumerate(rels):
        expr = pulp.lpSum(A[i][j] * xs[j] for j in range(n))
        mapped = REL_MAP.get(rel, "<=")
        if mapped == "<=":
            prob += expr <= b[i]
        elif mapped == ">=":
            prob += expr >= b[i]
        else:
            prob += expr == b[i]

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if pulp.LpStatus[prob.status] != "Optimal":
        return LPResult(
            status="infeasible",
            message=f"求解状态：{pulp.LpStatus[prob.status]}",
        )

    xvals = [pulp.value(xs[j]) for j in range(n)]
    opt_v = pulp.value(prob.objective)
    return LPResult(
        status="optimal",
        x=xvals,
        obj_value=opt_v if opt_v is not None else 0.0,
    )


def simplex_steps(
    c_orig: list[float],
    A: list[list[float]],
    b: list[float],
    maximize: bool = True,
) -> list[dict]:
    """记录单纯形法各迭代步骤，返回步骤列表（仅供展示）。"""
    import numpy as np

    subs = "₁₂₃₄₅₆₇₈₉"
    n = len(c_orig)
    m = len(b)
    steps: list[dict] = []
    c = [-v for v in c_orig] if maximize else list(c_orig)
    tab = np.zeros((m + 1, n + m + 1))
    tab[:m, :n] = np.array(A, dtype=float)
    tab[:m, n : n + m] = np.eye(m)
    tab[:m, -1] = np.array(b, dtype=float)
    tab[m, :n] = c
    basic = list(range(n, n + m))

    def vname(j: int) -> str:
        return (f"x{subs[j]}" if j < len(subs) else f"x{j+1}") if j < n else f"s{j-n+1}"

    vn = [vname(j) for j in range(n + m)]

    steps.append(
        {
            "title": "初始基可行解",
            "note": f"初始基变量：{', '.join(vn[b] for b in basic)}",
            "basic": [vn[b] for b in basic],
            "x_B": [round(v, 4) for v in tab[:m, -1]],
            "obj": 0,
        }
    )

    for it in range(50):
        obj_row = tab[m, : n + m]
        pc = int(np.argmin(obj_row))
        if obj_row[pc] >= -1e-8:
            steps.append({"title": "✅ 达到最优", "note": "所有检验数 ≥ 0，当前解即为最优解"})
            break
        col = tab[:m, pc]
        ratios = [
            (tab[i, -1] / col[i] if col[i] > 1e-10 else float("inf"), i)
            for i in range(m)
        ]
        pr = min(ratios, key=lambda r: r[0])[1]
        ev, lv = vn[pc], vn[basic[pr]]
        rv = tab[pr, -1] / col[pr]
        pivot = tab[pr, pc]
        tab[pr] /= pivot
        for i in range(m + 1):
            if i != pr:
                tab[i] -= tab[i, pc] * tab[pr]
        basic[pr] = pc
        obj_val = -tab[m, -1] if maximize else tab[m, -1]
        steps.append(
            {
                "title": f"第{it+1}次迭代",
                "note": f"入基：{ev}  出基：{lv}  最小比值={rv:.4g}",
                "basic": [vn[b] for b in basic],
                "x_B": [round(float(v), 4) for v in tab[:m, -1]],
                "obj": round(float(obj_val), 4),
            }
        )

    return steps
