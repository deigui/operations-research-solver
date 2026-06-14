"""剪贴板 TSV 解析工具。

从 Excel 或程序内部复制的表格数据（制表符分隔）进行解析，
自动检测并跳过标题行和标签列。
"""
from __future__ import annotations


def parse_tsv(text: str) -> list[list[str]]:
    """将 TSV 文本解析为二维列表。"""
    return [line.split("\t") for line in text.strip().splitlines() if line.strip()]


def _is_numeric(s: str) -> bool:
    """判断字符串是否为数字或空值。"""
    try:
        float(s.strip())
        return True
    except ValueError:
        return s.strip() == ""


def detect_headers(rows: list[list[str]]) -> tuple[bool, bool]:
    """检测粘贴数据是否含有标题行和标签列。

    Returns:
        (has_header_row, has_label_col)
    """
    if not rows:
        return False, False

    has_header_row = any(
        not _is_numeric(c) and c.strip() for c in rows[0]
    )

    has_label_col = False
    data_rows = rows[1:] if has_header_row else rows
    for row in data_rows:
        if row and not _is_numeric(row[0]) and row[0].strip():
            has_label_col = True
            break

    return has_header_row, has_label_col


def extract_data_block(
    rows: list[list[str]],
    skip_row: int,
    skip_col: int,
) -> list[list[str]]:
    """去掉标题行和标签列，返回纯数据块。"""
    return [row[skip_col:] for row in rows[skip_row:]]


def detect_transport_dimensions(
    rows: list[list[str]],
    skip_row: int,
    skip_col: int,
    raw_rows: list[list[str]],
) -> tuple[int | None, int | None, int | None]:
    """推断运输问题的 m（产地数）、n（销地数）和需求行索引。

    Returns:
        (new_m, new_n, demand_row_idx)  — 任意值可为 None 表示无法推断。
    """
    data = extract_data_block(rows, skip_row, skip_col)
    if len(data) <= 1:
        return None, None, None

    # 检测需求行
    demand_row_idx: int | None = None
    last = data[-1]
    prev = data[-2]

    # 方法1：末行产量列为空，前一行非空
    last_supply = last[-1].strip() if last else ""
    prev_supply = prev[-1].strip() if prev else ""
    supply_match = last_supply == "" and prev_supply != ""

    # 方法2：末行原始标签含需求相关关键词
    last_label = ""
    if skip_col == 1 and raw_rows:
        last_raw_idx = skip_row + len(data) - 1
        if last_raw_idx < len(raw_rows):
            last_raw = raw_rows[last_raw_idx]
            last_label = last_raw[0].strip() if last_raw else ""
    label_match = any(
        kw in last_label for kw in ["用量", "销量", "需求", "demand", "Demand"]
    )

    if supply_match or label_match:
        demand_row_idx = len(data) - 1

    if demand_row_idx is None:
        return None, None, None

    n_cost_rows = demand_row_idx
    # 判断是否含供应量列
    d_last = data[demand_row_idx][-1].strip() if data[demand_row_idx] else ""
    c_lasts = [data[ri][-1].strip() for ri in range(n_cost_rows) if data[ri]]
    has_supply_col = (
        not d_last
        and bool(c_lasts)
        and all(_is_numeric(v) and v for v in c_lasts)
    )

    new_m = n_cost_rows
    new_n = (len(data[0]) - 1) if has_supply_col else len(data[0])

    return new_m if new_m > 0 else None, new_n if new_n > 0 else None, demand_row_idx
