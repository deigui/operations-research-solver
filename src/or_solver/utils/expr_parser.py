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


def _find_variable_names(s: str) -> list[str]:
    """Return algebraic variable names such as x1, y2 in first-seen form."""
    names: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"[A-Za-z]+\d+", s):
        name = match.group(0).lower()
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _sort_variable_names(names: list[str]) -> list[str]:
    """Sort x variables first, then other prefixes by prefix and number."""
    def key(name: str) -> tuple[int, str, int]:
        m = re.match(r"([a-z]+)(\d+)$", name)
        if not m:
            return (1, name, 0)
        prefix, num = m.group(1), int(m.group(2))
        return (0 if prefix == "x" else 1, prefix, num)

    return sorted(names, key=key)


def _parse_polynomial_with_names(s: str, var_index: dict[str, int]) -> dict[int, float]:
    """Parse polynomial terms containing named variables from var_index."""
    s = s.strip().replace(" ", "").replace("－", "-").replace("＋", "+")
    if s and s[0] not in "+-":
        s = "+" + s
    coefs: dict[int, float] = {}
    number_re = r"(?:\d+(?:\.\d*)?|\.\d+)"
    term_re = re.compile(rf"([+-])({number_re}?)([A-Za-z]+\d+)")
    for match in term_re.finditer(s):
        name = match.group(3).lower()
        if name not in var_index:
            continue
        sign = 1 if match.group(1) == "+" else -1
        coef_text = match.group(2)
        coef = float(coef_text) if coef_text else 1.0
        idx = var_index[name]
        coefs[idx] = coefs.get(idx, 0.0) + sign * coef
    return {idx: coef for idx, coef in coefs.items() if abs(coef) > 1e-12}


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
    # 约束行
    REL_RE = re.compile(r"(<=|>=|<|>|=)")
    REL_MAP = {"<=": "≤", ">=": "≥", "<": "≤", ">": "≥", "=": "="}
    constraint_parts = []
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
        if re.match(r"[A-Za-z]\d+>=0$", l_clean) or re.match(r"[A-Za-z]\d+<=0$", l_clean):
            continue

        matched = False
        for sym in ["<=", ">=", "<", ">", "="]:
            if sym in l_clean:
                parts = l_clean.split(sym, 1)
                try:
                    rhs = float(parts[1])
                except ValueError:
                    continue
                constraint_parts.append((parts[0], REL_MAP[sym], rhs))
                matched = True
                break
        if not matched:
            raise ValueError(f"无法解析约束行：{line}")

    if not constraint_parts:
        raise ValueError("找不到约束条件")

    var_names = _sort_variable_names(
        list(dict.fromkeys(_find_variable_names(obj_part + "\n" + "\n".join(p[0] for p in constraint_parts))))
    )
    if not var_names:
        raise ValueError("未识别到变量（格式应为 x1, x2, y1, ...）")

    var_index = {name: idx for idx, name in enumerate(var_names)}
    constraints = [
        {
            "coefs": _parse_polynomial_with_names(lhs, var_index),
            "rel": rel,
            "rhs": rhs,
        }
        for lhs, rel, rhs in constraint_parts
    ]

    n_vars = len(var_names)
    obj_coefs = _parse_polynomial_with_names(obj_part, var_index)
    if not obj_coefs:
        nums = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", obj_part)
        if nums and all(abs(float(v)) < 1e-12 for v in nums):
            obj_coefs = {}
        else:
            raise ValueError("目标函数解析失败，请检查变量格式（x1, x2, ...）")
    return {
        "maximize": maximize,
        "obj_coefs": obj_coefs,
        "constraints": constraints,
        "n_vars": n_vars,
        "n_cons": len(constraints),
        "var_names": var_names,
        "var_types": ["B" if name.startswith("y") else "I" for name in var_names],
    }


def parse_table_lp_expr(
    raw: str,
    default_maximize: bool = True,
    default_rel: str = "≤",
) -> dict:
    """解析表格式线性规划文本，返回结构化数据。

    支持格式::

        max
        15 10 7 13 9
        5 10 7 0 0 <= 8000
        6 4 8 6 4 <= 12000
        3 2 2 3 2 <= 10000

    也支持省略首行 max/min，此时使用 default_maximize；
    若约束行未显式提供关系符，则默认采用 default_rel，且最后一个数视为 RHS。
    """
    raw = normalize_expr(raw)
    if "# ── 求解结果" in raw:
        raw = raw[: raw.index("# ── 求解结果")].strip()

    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        raise ValueError("未找到表格式线性规划数据")

    number_re = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"

    def parse_numbers(text: str) -> list[float]:
        return [float(x) for x in re.findall(number_re, text)]

    maximize = default_maximize
    obj_line = ""
    first_line = lines[0]
    if re.match(r"^(max|min)\b", first_line, re.I):
        maximize = bool(re.match(r"^max\b", first_line, re.I))
        rest = re.sub(r"^(max|min)\b", "", first_line, flags=re.I).strip()
        if re.search(r"[xX]\d+", rest):
            raise ValueError("检测到代数式变量，请使用标准线性规划表达式格式")
        if parse_numbers(rest):
            obj_line = rest
            lines = lines[1:]
        else:
            lines = lines[1:]

    if not obj_line:
        if not lines:
            raise ValueError("缺少目标系数行")
        obj_line = lines[0]
        lines = lines[1:]

    if re.search(r"[xX]\d+", obj_line):
        raise ValueError("检测到代数式变量，请使用标准线性规划表达式格式")

    obj_values = parse_numbers(obj_line)
    if not obj_values:
        raise ValueError("目标系数行未识别到数字")

    n_vars = len(obj_values)
    obj_coefs = {
        j: value for j, value in enumerate(obj_values) if abs(value) > 1e-12
    }

    rel_map = {"<=": "≤", ">=": "≥", "<": "≤", ">": "≥", "=": "="}
    constraints = []

    for line in lines:
        if re.match(r"s\.?\s*t\.?", line, re.I):
            continue
        compact = line.replace(" ", "")
        if re.match(r"x\d+>=0$", compact, re.I) or re.match(r"x\d+<=0$", compact, re.I):
            continue
        if re.search(r"[xX]\d+", line):
            raise ValueError("检测到代数式变量，请使用标准线性规划表达式格式")

        rel_match = re.search(r"(<=|>=|<|>|=)", line)
        if rel_match:
            lhs = line[: rel_match.start()]
            rhs_text = line[rel_match.end() :]
            coef_values = parse_numbers(lhs)
            rhs_values = parse_numbers(rhs_text)
            rel = rel_map[rel_match.group(1)]
            if not coef_values:
                raise ValueError(f"约束系数解析失败：{line}")
            if len(rhs_values) != 1:
                raise ValueError(f"约束右端常数解析失败：{line}")
            rhs = rhs_values[0]
        else:
            row_values = parse_numbers(line)
            if not row_values:
                continue
            if len(row_values) < 2:
                raise ValueError(f"约束行至少需要 1 个系数和 1 个常数：{line}")
            coef_values = row_values[:-1]
            rhs = row_values[-1]
            rel = default_rel

        if len(coef_values) > n_vars:
            raise ValueError(f"约束系数个数超过目标系数个数：{line}")

        padded = coef_values + [0.0] * (n_vars - len(coef_values))
        constraints.append(
            {
                "coefs": {
                    j: value for j, value in enumerate(padded) if abs(value) > 1e-12
                },
                "rel": rel,
                "rhs": rhs,
            }
        )

    if not constraints:
        raise ValueError("找不到约束条件")

    return {
        "maximize": maximize,
        "obj_coefs": obj_coefs,
        "constraints": constraints,
        "n_vars": n_vars,
        "n_cons": len(constraints),
    }


def parse_lp_data_matrix(
    raw: str,
    maximize: bool = True,
    default_rel: str = "≤",
) -> dict:
    """解析纯数字数据矩阵，按“最后一列为 RHS，其余列为系数”处理。

    示例::

        2 0 2
        0 3 1
        2 2 2

    将被解释为 3 个约束、2 个决策变量，目标函数系数默认全 0。
    """
    raw = normalize_expr(raw)
    lines = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        raise ValueError("未找到数据矩阵")

    rows: list[list[float]] = []
    for line in lines:
        if re.search(r"[xX]\d+", line) or re.match(r"^(max|min)\b", line, re.I):
            raise ValueError("检测到表达式格式，请使用标准线性规划表达式解析")
        cells = line.replace("\t", " ").split()
        if len(cells) < 2:
            raise ValueError(f"数据矩阵每行至少应包含 1 个系数和 1 个常数项：{line}")
        try:
            rows.append([float(v) for v in cells])
        except ValueError as exc:
            raise ValueError(f"数据矩阵中存在无法识别的数字：{line}") from exc

    n_vars = max(len(row) for row in rows) - 1
    if n_vars <= 0:
        raise ValueError("数据矩阵列数不足，无法识别决策变量")

    constraints = []
    for row in rows:
        coef_values = row[:-1]
        rhs = row[-1]
        padded = coef_values + [0.0] * (n_vars - len(coef_values))
        constraints.append(
            {
                "coefs": {
                    j: value for j, value in enumerate(padded) if abs(value) > 1e-12
                },
                "rel": default_rel,
                "rhs": rhs,
            }
        )

    return {
        "maximize": maximize,
        "obj_coefs": {},
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
