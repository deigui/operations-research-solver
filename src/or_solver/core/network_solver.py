"""网络优化求解器（最短路 Dijkstra、最小支撑树 Prim）。

零 tkinter 依赖。
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field


@dataclass
class ShortestPathResult:
    status: str           # "found" | "no_path"
    distance: float = math.inf
    path: list[int] = field(default_factory=list)   # 1-based 节点编号
    message: str = ""


def dijkstra(
    dist_matrix: list[list[float]],
    src: int,
    dst: int,
) -> ShortestPathResult:
    """Dijkstra 最短路算法。

    Args:
        dist_matrix: n×n 距离矩阵，math.inf 表示无连接。
        src: 起点索引（0-based）。
        dst: 终点索引（0-based）。

    Returns:
        ShortestPathResult，path 为 1-based 节点序列。
    """
    n = len(dist_matrix)
    INF = math.inf
    d = [INF] * n
    d[src] = 0.0
    prev = [-1] * n
    pq: list[tuple[float, int]] = [(0.0, src)]

    while pq:
        dd, u = heapq.heappop(pq)
        if dd > d[u]:
            continue
        for v in range(n):
            w = dist_matrix[u][v]
            if w < INF and d[u] + w < d[v]:
                d[v] = d[u] + w
                prev[v] = u
                heapq.heappush(pq, (d[v], v))

    if d[dst] == INF:
        return ShortestPathResult(
            status="no_path",
            message="节点间无通路",
        )

    path: list[int] = []
    cur = dst
    while cur != -1:
        path.append(cur + 1)   # 转为 1-based
        cur = prev[cur]
    path.reverse()

    return ShortestPathResult(
        status="found",
        distance=d[dst],
        path=path,
    )


# ── 最小支撑树 ────────────────────────────────────────────


@dataclass
class MSTResult:
    status: str                                     # "found" | "disconnected"
    edges: list[tuple[int, int, float]] = field(default_factory=list)  # (u, v, w) 1-based
    total_weight: float = 0.0
    steps: list[str] = field(default_factory=list)  # 文字步骤记录
    message: str = ""


def prim_mst(
    weight_matrix: list[list[float]],
) -> MSTResult:
    """Prim 算法求最小支撑树。

    Args:
        weight_matrix: n×n 权重矩阵，math.inf 表示无边。
                       矩阵应对称；对角线为 0 或 inf。

    Returns:
        MSTResult，edges 中节点编号为 1-based。
    """
    n = len(weight_matrix)
    if n == 0:
        return MSTResult(status="disconnected", message="图为空")

    INF = math.inf
    in_tree = [False] * n
    key = [INF] * n        # 连接该节点到树的最小边权
    parent = [-1] * n      # 各节点在 MST 中的父节点
    key[0] = 0.0

    edges: list[tuple[int, int, float]] = []
    steps: list[str] = []
    total = 0.0

    steps.append(f"初始：从节点 1 开始构建最小支撑树")

    for iteration in range(n):
        # 取未加入树中 key 最小的节点
        u = min((i for i in range(n) if not in_tree[i]), key=lambda i: key[i])
        if key[u] == INF:
            return MSTResult(
                status="disconnected",
                message="图不连通，无法构建最小支撑树",
            )
        in_tree[u] = True

        if parent[u] != -1:
            w = weight_matrix[parent[u]][u]
            edges.append((parent[u] + 1, u + 1, w))
            total += w
            steps.append(
                f"第{iteration}步：选择边 ({parent[u]+1}, {u+1})，"
                f"权重 = {w:g}，累计权重 = {total:g}"
            )

        # 更新相邻节点的 key
        for v in range(n):
            w = weight_matrix[u][v]
            if not in_tree[v] and w < key[v]:
                key[v] = w
                parent[v] = u

    steps.append(f"\n最小支撑树总权重 = {total:g}")
    return MSTResult(
        status="found",
        edges=edges,
        total_weight=total,
        steps=steps,
    )
