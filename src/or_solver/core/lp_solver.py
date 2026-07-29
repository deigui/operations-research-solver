"""线性规划 / 整数规划核心求解器。

零 tkinter 依赖，所有函数均可独立单测。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from or_solver.core.pulp_compat import solve_mip_problem


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

    # ── 灵敏度分析（基矩阵法）────────────────────────────
    try:
        # 构建增广矩阵：决策变量列 + 松弛/剩余变量列
        # ≤ 约束添加松弛 s≥0：A_aug[i,col]=+1
        # ≥ 约束添加剩余 s≥0：A_aug[i,col]=-1
        # = 约束不添加
        slack_info: list = []  # (constraint_idx, sign, aug_col)
        s_col = n
        for i, rel in enumerate(rels):
            if rel in ("≤", "<=", "<"):
                slack_info.append((i, 1, s_col)); s_col += 1
            elif rel in ("≥", ">=", ">"):
                slack_info.append((i, -1, s_col)); s_col += 1

        N = s_col
        A_aug = np.zeros((m, N))
        A_aug[:, :n] = np.array(A, dtype=float)
        for ci, sign, col in slack_info:
            A_aug[ci, col] = float(sign)

        b_arr = np.array(b, dtype=float)

        # 最小化形式目标（松弛/剩余系数=0）
        c_min_full = np.zeros(N)
        c_min_full[:n] = [-ci for ci in c] if maximize else list(c)

        # 完整解向量（含松弛/剩余）
        x_full = np.zeros(N)
        x_full[:n] = res.x
        for ci, sign, col in slack_info:
            ax_i = float(A_aug[ci, :n] @ res.x)
            x_full[col] = (b_arr[ci] - ax_i) if sign == 1 else (ax_i - b_arr[ci])

        # 基变量识别：x_full > eps 为基变量候选
        eps_b = 1e-7
        basic_candidates = [j for j in range(N) if x_full[j] > eps_b]

        if len(basic_candidates) == m:
            basic_idx = sorted(basic_candidates)
        elif len(basic_candidates) < m:
            needed = m - len(basic_candidates)
            cand_set = set(basic_candidates)
            zero_vars = [j for j in range(N) if j not in cand_set and x_full[j] >= -eps_b]
            basic_idx = sorted(basic_candidates + zero_vars[:needed])
        else:
            basic_idx = sorted(
                sorted(basic_candidates, key=lambda j: -x_full[j])[:m]
            )

        nonbasic_idx = [j for j in range(N) if j not in set(basic_idx)]

        B_mat = A_aug[:, basic_idx]
        B_inv = np.linalg.inv(B_mat)
        c_B = c_min_full[basic_idx]

        # 简约费用向量（从基矩阵直接计算，不依赖 HiGHS 内部数据）
        rc_full = c_min_full - c_B @ B_inv @ A_aug

        # ── 目标函数系数变动范围 ──────────────────────────
        c_lo: list[float] = []
        c_hi: list[float] = []
        c_diff: list[float] = []
        basic_set = set(basic_idx)

        for j in range(n):
            if j in basic_set:
                p = basic_idx.index(j)
                r_lo_v: list[float] = []
                r_hi_v: list[float] = []
                for k in nonbasic_idx:
                    eta = float(B_inv[p, :] @ A_aug[:, k])
                    rc_k = max(0.0, float(rc_full[k]))
                    if abs(eta) < 1e-10:
                        continue
                    ratio = rc_k / eta          # 注意：不是 -rc_k/eta
                    if eta > 0:
                        r_hi_v.append(ratio)    # Δ 上界
                    else:
                        r_lo_v.append(ratio)    # Δ 下界
                d_lo = max(r_lo_v) if r_lo_v else -INF
                d_hi = min(r_hi_v) if r_hi_v else INF
                # 最小化形式：c_min[j] 可在 [c_min[j]+d_lo, c_min[j]+d_hi] 变动
                clo_min = c_min_full[j] + (d_lo if d_lo > -INF * 0.9 else -INF)
                chi_min = c_min_full[j] + (d_hi if d_hi < INF * 0.9 else INF)
                if maximize:
                    # c_min[j] = -c[j]，故原始 c[j] 范围 = [-chi_min, -clo_min]
                    c_lo.append(-chi_min if chi_min < INF * 0.9 else -INF)
                    c_hi.append(-clo_min if clo_min > -INF * 0.9 else INF)
                else:
                    c_lo.append(clo_min)
                    c_hi.append(chi_min)
                c_diff.append(0.0)
            else:
                # 非基变量（处于下界 0）
                rc_j_min = max(0.0, float(rc_full[j]))
                if maximize:
                    # 最大化：c[j] 最多增加 rc_j_min 才会入基
                    c_lo.append(-INF)
                    c_hi.append(c[j] + rc_j_min)
                    c_diff.append(-rc_j_min)
                else:
                    # 最小化：c[j] 最多减少 rc_j_min 才会入基
                    c_lo.append(c[j] - rc_j_min)
                    c_hi.append(INF)
                    c_diff.append(rc_j_min)

        result.c_lower = c_lo
        result.c_upper = c_hi
        result.c_diff = c_diff

        # ── 约束右端项变动范围 ────────────────────────────
        # d(x_B)/d(b[i]) = B_inv[:,i]（i-th 列）
        # x_B[p] + δ·B_inv[p,i] ≥ 0 → 推导 δ 范围
        b_lo2: list[float] = []
        b_hi2: list[float] = []
        x_B = np.array([x_full[j] for j in basic_idx])

        for i in range(m):
            col_Bi = B_inv[:, i]
            lo_r: list[float] = []
            hi_r: list[float] = []
            for p in range(m):
                bi_p = col_Bi[p]
                if abs(bi_p) < 1e-10:
                    continue
                ratio = -float(x_B[p]) / bi_p
                if bi_p > 0:
                    lo_r.append(ratio)   # δ 下界
                else:
                    hi_r.append(ratio)   # δ 上界
            d_lo2 = max(lo_r) if lo_r else -INF
            d_hi2 = min(hi_r) if hi_r else INF
            b_lo2.append(b[i] + (d_lo2 if d_lo2 > -INF * 0.9 else -INF))
            b_hi2.append(b[i] + (d_hi2 if d_hi2 < INF * 0.9 else INF))

        result.b_lower = b_lo2
        result.b_upper = b_hi2

    except Exception:
        result.c_lower = [-INF] * n
        result.c_upper = [INF] * n
        result.c_diff = [0.0] * n
        result.b_lower = [-INF] * m
        result.b_upper = [INF] * m

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
        xs = [prob.add_variable(f"x{j+1}", cat="Binary") for j in range(n)]
    elif mixed_var_types:
        xs = []
        for j in range(n):
            vtype = mixed_var_types[j] if j < len(mixed_var_types) else "C"
            if vtype == "B":
                xs.append(prob.add_variable(f"x{j+1}", cat="Binary"))
            elif vtype == "I":
                xs.append(prob.add_variable(f"x{j+1}", lowBound=0, cat="Integer"))
            else:
                xs.append(prob.add_variable(f"x{j+1}", lowBound=0, cat="Continuous"))
    elif integer_vars is True:
        xs = [prob.add_variable(f"x{j+1}", lowBound=0, cat="Integer") for j in range(n)]
    else:
        int_set = set(integer_vars or [])
        xs = [
            prob.add_variable(
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

    solve_mip_problem(prob, pulp, msg=0)

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
