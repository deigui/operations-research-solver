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


@dataclass
class FlowResult:
    status: str
    value: float = 0.0
    cost: float = 0.0
    flows: list[tuple[int, int, float, float]] = field(default_factory=list)  # u, v, flow, cost
    distances: list[list[float]] = field(default_factory=list)
    message: str = ""


def max_flow(n: int, edges: list[tuple[int, int, float, float]], src: int, dst: int) -> FlowResult:
    """Edmonds-Karp 最大流。节点编号入参为 0-based。"""
    from collections import deque

    cap = [[0.0] * n for _ in range(n)]
    for u, v, c, _cost in edges:
        cap[u][v] += c
    flow = [[0.0] * n for _ in range(n)]
    total = 0.0

    while True:
        parent = [-1] * n
        parent[src] = src
        q = deque([src])
        while q and parent[dst] == -1:
            u = q.popleft()
            for v in range(n):
                if parent[v] == -1 and cap[u][v] - flow[u][v] > 1e-9:
                    parent[v] = u
                    q.append(v)
        if parent[dst] == -1:
            break
        aug = math.inf
        v = dst
        while v != src:
            u = parent[v]
            aug = min(aug, cap[u][v] - flow[u][v])
            v = u
        v = dst
        while v != src:
            u = parent[v]
            flow[u][v] += aug
            flow[v][u] -= aug
            v = u
        total += aug

    used = [(u + 1, v + 1, flow[u][v], 0.0) for u in range(n) for v in range(n) if flow[u][v] > 1e-9]
    return FlowResult(status="optimal", value=total, flows=used)


def min_cost_flow(
    n: int,
    edges: list[tuple[int, int, float, float]],
    src: int,
    dst: int,
    demand: float | None = None,
) -> FlowResult:
    """最小费用流；demand=None 时求最小费用最大流。"""
    graph: list[list[dict]] = [[] for _ in range(n)]

    def add_edge(u: int, v: int, cap: float, cost: float) -> None:
        fwd = {"to": v, "rev": len(graph[v]), "cap": cap, "cost": cost, "flow": 0.0}
        rev = {"to": u, "rev": len(graph[u]), "cap": 0.0, "cost": -cost, "flow": 0.0}
        graph[u].append(fwd)
        graph[v].append(rev)

    for u, v, cap, cost in edges:
        add_edge(u, v, cap, cost)

    total_flow = 0.0
    total_cost = 0.0
    target = math.inf if demand is None else demand

    while total_flow + 1e-9 < target:
        dist = [math.inf] * n
        inq = [False] * n
        pv = [-1] * n
        pe = [-1] * n
        dist[src] = 0.0
        queue = [src]
        inq[src] = True
        while queue:
            u = queue.pop(0)
            inq[u] = False
            for i, e in enumerate(graph[u]):
                if e["cap"] > 1e-9 and dist[u] + e["cost"] < dist[e["to"]] - 1e-9:
                    dist[e["to"]] = dist[u] + e["cost"]
                    pv[e["to"]] = u
                    pe[e["to"]] = i
                    if not inq[e["to"]]:
                        queue.append(e["to"])
                        inq[e["to"]] = True
        if dist[dst] == math.inf:
            break

        aug = target - total_flow
        v = dst
        while v != src:
            u = pv[v]
            e = graph[u][pe[v]]
            aug = min(aug, e["cap"])
            v = u
        v = dst
        while v != src:
            u = pv[v]
            e = graph[u][pe[v]]
            rev = graph[v][e["rev"]]
            e["cap"] -= aug
            rev["cap"] += aug
            e["flow"] += aug
            rev["flow"] -= aug
            total_cost += aug * e["cost"]
            v = u
        total_flow += aug

        if demand is None and aug <= 1e-9:
            break

    if demand is not None and total_flow + 1e-9 < demand:
        return FlowResult(status="infeasible", value=total_flow, cost=total_cost, message="无法满足指定流量")

    used: list[tuple[int, int, float, float]] = []
    for u in range(n):
        for e in graph[u]:
            if e["flow"] > 1e-9:
                used.append((u + 1, e["to"] + 1, e["flow"], e["cost"]))
    return FlowResult(status="optimal", value=total_flow, cost=total_cost, flows=used)


def floyd_warshall(n: int, edges: list[tuple[int, int, float, float]]) -> FlowResult:
    """Floyd-Warshall 全源最短路。边元组中的 cost 字段作为距离。"""
    dist = [[math.inf] * n for _ in range(n)]
    for i in range(n):
        dist[i][i] = 0.0
    for u, v, _cap, cost in edges:
        dist[u][v] = min(dist[u][v], cost)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    return FlowResult(status="optimal", distances=dist)
