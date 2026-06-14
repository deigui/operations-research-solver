"""LP / 运输问题表达式的标准化与解析工具。

不依赖 tkinter，所有函数均为纯函数，可单独测试。
"""
from __future__ import annotations

import re


def normalize_expr(s: str) -> str:
    """全角符号→ASCII，Unicode 下标→普通数字。"""
    s = (s.replace("＝", "=").replace("＋", "+").replace("－", "-")
          .replace("≥", ">=").replace("≤", "<=")
          .replace("＜＝", "<=").replace("＞＝", ">="))
    for sub, num in zip("₀₁₂₃₄₅₆₇₈₉", "0123456789"):
        s = s.replace(sub, num)
    return s


def parse_polynomial(s: str) -> dict[int, float]:
    """解析多项式字符串，返回 {变量0-索引: 系数} 字典。

    支持格式：5x1 + 10x2 - 7x3，系数可省略（默认1）。
    """
    s = s.strip().replace(" ", "").replace("－", "-").replace("＋", "+")
    if s and s[0] not in "+-":
        s = "+" + s
    coefs: dict[int, float] = {}
    for m in re.finditer(r"([+-])([0-9.]*)[xX]([0-9]+)", s):
        sign = 1 if m.group(1) == "+" else -1
        c_str = m.group(2)
        c = float(c_str) if c_str else 1.0
        coefs[int(m.group(3)) - 1] = sign * c
    return coefs


def parse_lp_expr(raw: str) -> dict:
    """解析标准 LP 表达式文本，返回结构化数据。

    返回格式::

        {
            "maximize": bool,
            "obj_coefs": {0: 15.0, 1: 10.0, ...},
            "constraints": [
                {"coefs": {0: 5.0, ...}, "rel": "≤", "rhs": 8000.0},
                ...
            ],
            "n_vars": int,
            "n_cons": int,
        }

    Raises:
        ValueError: 解析失败时抛出，message 为中文说明。
    """
    raw = normalize_expr(raw)
    # 去掉求解结果分隔线之后的内容
    if "# ── 求解结果" in raw:
        raw = raw[: raw.index("# ── 求解结果")].strip()

    lines = [l.strip() for l in raw.split("\n") if l.strip()]

    # 目标函数行
    obj_line = next(
        (l for l in lines if re.match(r"(max|min|MAX|MIN)", l, re.I)), None
    )
    if not obj_line:
        raise ValueError("找不到目标函数行（需含 max 或 min）")

    maximize = bool(re.match(r"(max|MAX)", obj_line, re.I))
    obj_part = re.sub(r"^(max|min)[^=]*=\s*", "", obj_line, flags=re.I)
    obj_coefs = parse_polynomial(obj_part)
    if not obj_coefs:
        raise ValueError("目标函数解析失败，请检查变量格式（x1, x2, ...）")

    # 约束行
    REL_RE = re.compile(r"(<=|>=|<|>|=)")
    REL_MAP = {"<=": "≤", ">=": "≥", "<": "≤", ">": "≥", "=": "="}
    constraints = []
    for line in lines:
        if not REL_RE.search(line):
            continue
        if re.match(r"s\.?t\.?", line, re.I):
            continue
        if re.match(r"\s*(max|min)", line, re.I):
            continue
        if line.strip().startswith("#"):
            continue
        if re.match(r"\s*(最优|Z\s*=)", line):
            continue
        l_clean = line.replace(" ", "")
        if re.match(r"x\d+>=0$", l_clean) or re.match(r"x\d+<=0$", l_clean):
            continue

        matched = False
        for sym in ["<=", ">=", "<", ">", "="]:
            if sym in l_clean:
                parts = l_clean.split(sym, 1)
                try:
                    rhs = float(parts[1])
                except ValueError:
                    continue
                constraints.append(
                    {
                        "coefs": parse_polynomial(parts[0]),
                        "rel": REL_MAP[sym],
                        "rhs": rhs,
                    }
                )
                matched = True
                break
        if not matched:
            raise ValueError(f"无法解析约束行：{line}")

    if not constraints:
        raise ValueError("找不到约束条件")

    all_vars: set[int] = set(obj_coefs.keys())
    for con in constraints:
        all_vars |= set(con["coefs"].keys())
    if not all_vars:
        raise ValueError("未识别到变量（格式应为 x1, x2, ...）")

    n_vars = max(all_vars) + 1
    return {
        "maximize": maximize,
        "obj_coefs": obj_coefs,
        "constraints": constraints,
        "n_vars": n_vars,
        "n_cons": len(constraints),
    }


def parse_transport_simple(raw: str) -> dict:
    """解析简单运输问题格式（费用矩阵 + 产量:/销量: 行）。

    返回格式::

        {
            "cost_matrix": [[...], ...],
            "supply": [...],
            "demand": [...],
        }

    Raises:
        ValueError: 解析失败。
    """
    lines = [
        l.strip()
        for l in raw.split("\n")
        if l.strip() and not l.strip().startswith("#")
    ]
    supply: list[float] = []
    demand: list[float] = []
    cost_rows: list[list[float]] = []

    for line in lines:
        if re.match(r"产量\s*[:：]", line):
            nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", re.split(r"[:：]", line, 1)[-1])
            supply = [float(x) for x in nums]
        elif re.match(r"销量\s*[:：]", line):
            nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", re.split(r"[:：]", line, 1)[-1])
            demand = [float(x) for x in nums]
        else:
            nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+", line)
            if nums:
                cost_rows.append([float(x) for x in nums])

    if not cost_rows:
        raise ValueError("未找到费用矩阵数据（请每行填写一个产地的运费，空格分隔）")

    return {"cost_matrix": cost_rows, "supply": supply, "demand": demand}


def parse_transport_lp(raw: str) -> dict:
    """解析 LP 格式运输问题表达式，推断 m×n 并返回费用矩阵。

    返回格式::

        {
            "cost_matrix": [[...], ...],
            "supply": [...],
            "demand": [...],
            "m": int,
            "n": int,
        }

    Raises:
        ValueError: 解析失败。
    """
    raw = normalize_expr(raw)
    lines = [l.strip() for l in raw.split("\n") if l.strip()]

    # 目标函数
    obj_line = next((l for l in lines if re.match(r"(min|max)\b", l, re.I)), None)
    if not obj_line:
        raise ValueError("找不到目标函数行（需含 min 或 max）")
    obj_part = re.sub(r"^(min|max)\s*\w?\s*=\s*", "", obj_line, flags=re.I)
    cost_coefs = parse_polynomial(obj_part)
    if not cost_coefs:
        raise ValueError("目标函数解析失败，请检查变量格式（x1, x2, ...）")
    total_vars = max(cost_coefs.keys()) + 1

    # 等式约束
    eq_cons: list[tuple[list[int], float]] = []
    for line in lines:
        if re.match(r"(min|max)\b", line, re.I):
            continue
        if line.startswith("#"):
            continue
        line = re.sub(r"^s\.?\s*t\.?\s*", "", line, flags=re.I).strip()
        if not line:
            continue
        lc = line.replace(" ", "")
        if re.match(r"x[^0-9]*[0-9,，…\s]*\s*>=?\s*0", lc, re.I):
            continue
        if "=" not in lc or ">=" in lc or "<=" in lc:
            continue
        parts = lc.split("=", 1)
        var_set = sorted(
            {int(m.group(1)) - 1 for m in re.finditer(r"[xX]([0-9]+)", parts[0])}
        )
        if not var_set:
            continue
        try:
            rhs = float(parts[1])
            eq_cons.append((var_set, rhs))
        except ValueError:
            pass

    if not eq_cons:
        raise ValueError("未找到等式约束")

    # 区分供应约束（连续索引）与需求约束（等步长索引）
    supply_cons: list[tuple[list[int], float]] = []
    demand_cons: list[tuple[list[int], float]] = []
    n_detected: int | None = None

    for var_set, rhs in eq_cons:
        if len(var_set) < 2:
            supply_cons.append((var_set, rhs))
            continue
        diffs = [var_set[k + 1] - var_set[k] for k in range(len(var_set) - 1)]
        if all(d == 1 for d in diffs):
            supply_cons.append((var_set, rhs))
            if n_detected is None:
                n_detected = len(var_set)
        elif len(set(diffs)) == 1:
            demand_cons.append((var_set, rhs))

    if n_detected is None:
        if demand_cons:
            n_detected = len(demand_cons)
        else:
            raise ValueError("无法推断销地数，请检查约束格式")

    n = n_detected
    m_src = total_vars // n if total_vars % n == 0 else len(supply_cons)

    cost_matrix = [[0.0] * n for _ in range(m_src)]
    for var_idx, coef in cost_coefs.items():
        i, j = var_idx // n, var_idx % n
        if i < m_src and j < n:
            cost_matrix[i][j] = coef

    supply_cons.sort(key=lambda x: x[0][0])
    demand_cons.sort(key=lambda x: x[0][0])

    return {
        "cost_matrix": cost_matrix,
        "supply": [rhs for _, rhs in supply_cons],
        "demand": [rhs for _, rhs in demand_cons],
        "m": m_src,
        "n": n,
    }
