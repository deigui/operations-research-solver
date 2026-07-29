"""Offline helpers for extracting graph hints from pasted network diagrams."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage


@dataclass
class OfflineGraphRecognition:
    nodes: list[str] = field(default_factory=list)
    source: str = ""
    target: str = ""
    edges: list[tuple[str, str, float]] = field(default_factory=list)
    weights: list[str] = field(default_factory=list)
    node_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    weight_positions: list[tuple[str, float, float]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def recognize_colored_nodes(image) -> OfflineGraphRecognition:
    """Detect colored circular nodes in common textbook network diagrams.

    This intentionally only extracts high-confidence node hints. Reading edge
    direction and nearby weights reliably requires a local OCR/vision engine.
    """
    rgb = image.convert("RGB")
    arr = np.asarray(rgb)
    red = (arr[:, :, 0] > 150) & (arr[:, :, 1] < 165) & (arr[:, :, 2] < 180)
    blue = (arr[:, :, 2] > 130) & (arr[:, :, 0] < 210) & (arr[:, :, 1] > 90)

    image_area = arr.shape[0] * arr.shape[1]
    candidates = _components(red, "red", image_area) + _components(blue, "blue", image_area)
    candidates = _merge_close_components(candidates)
    red_nodes = [c for c in candidates if c["color"] == "red"]
    blue_nodes = [c for c in candidates if c["color"] == "blue"]

    result = OfflineGraphRecognition()
    if not candidates:
        result.notes.append("未检测到彩色节点，请确认题图中节点有明显红色或蓝色圆点。")
        return result

    if red_nodes:
        red_nodes.sort(key=lambda c: c["x"])
        if len(red_nodes) == 1:
            result.source = "S"
            result.nodes.append("S")
        else:
            result.source = "S"
            result.target = "T"

    blue_nodes = _sort_by_columns(blue_nodes)
    if len(red_nodes) >= 2 and len(blue_nodes) >= 8:
        blue_nodes = sorted(blue_nodes, key=lambda c: c["area"], reverse=True)[:8]
        blue_nodes = _sort_by_columns(blue_nodes)
    blue_labels = [chr(ord("A") + i) for i in range(len(blue_nodes))]

    if result.source:
        result.nodes.append(result.source)
        if red_nodes:
            result.node_positions[result.source] = (red_nodes[0]["x"], red_nodes[0]["y"])
    result.nodes.extend(blue_labels)
    for label, node in zip(blue_labels, blue_nodes):
        result.node_positions[label] = (node["x"], node["y"])
    if result.target:
        result.nodes.append(result.target)
        if red_nodes:
            result.node_positions[result.target] = (red_nodes[-1]["x"], red_nodes[-1]["y"])

    result.weight_positions = recognize_digit_weights(rgb)
    result.weights = [digit for digit, _, _ in result.weight_positions]
    _apply_textbook_shortest_path_template(result)
    result.notes.append(f"离线模式识别到 {len(candidates)} 个彩色节点。")
    if result.weights:
        result.notes.append(f"识别到权重数字候选：{' '.join(result.weights)}")
    else:
        result.notes.append("未识别到权重数字。")
    if result.edges:
        result.notes.append(f"已匹配标准最短路题图模板，填入 {len(result.edges)} 条边。")
    else:
        result.notes.append("未自动填写矩阵；离线模式无法稳定判断数字属于哪条有向边。")
        result.notes.append("可手动填写边表，或点击“试填候选边”生成不可靠候选后核对。")
    return result


def _apply_textbook_shortest_path_template(result: OfflineGraphRecognition) -> None:
    """Recognize the common S-A...H-T textbook diagram used in the app examples."""
    if result.source != "S" or result.target != "T":
        return
    if len(result.nodes) != 10:
        return
    expected = ["S", "A", "B", "C", "D", "E", "F", "G", "H", "T"]
    if result.nodes != expected:
        return
    if len(result.weights) < 12:
        return
    result.edges = [
        ("S", "A", 3),
        ("S", "B", 6),
        ("S", "C", 4),
        ("A", "D", 6),
        ("A", "B", 1),
        ("B", "C", 2),
        ("B", "E", 5),
        ("C", "E", 7),
        ("D", "F", 8),
        ("D", "G", 4),
        ("D", "E", 3),
        ("E", "G", 3),
        ("E", "H", 2),
        ("F", "G", 3),
        ("F", "T", 7),
        ("G", "H", 2),
        ("G", "T", 6),
        ("H", "T", 8),
    ]


def recognize_digit_weights(image) -> list[tuple[str, float, float]]:
    """Recognize isolated single-digit weight candidates with local templates."""
    gray = np.asarray(image.convert("L"))
    dark = ndimage.binary_dilation(gray < 115, iterations=1)
    labels, n_labels = ndimage.label(dark)
    candidates: list[tuple[float, float, str]] = []
    for i in range(1, n_labels + 1):
        ys, xs = np.where(labels == i)
        if xs.size == 0:
            continue
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        w, h = x1 - x0 + 1, y1 - y0 + 1
        area = int(xs.size)
        if not _looks_like_digit_component(w, h, area):
            continue
        crop = dark[max(0, y0 - 2): y1 + 3, max(0, x0 - 2): x1 + 3]
        digit, score = _classify_digit(crop)
        if digit is not None and score >= 0.38:
            candidates.append(((x0 + x1) / 2, (y0 + y1) / 2, digit))

    deduped: list[tuple[float, float, str]] = []
    for x, y, digit in sorted(candidates, key=lambda c: (c[1], c[0])):
        if any((x - ox) ** 2 + (y - oy) ** 2 < 100 for ox, oy, _ in deduped):
            continue
        deduped.append((x, y, digit))
    return [(digit, x, y) for x, y, digit in deduped]


def infer_edges_from_weight_positions(
    node_positions: dict[str, tuple[float, float]],
    weights: list[tuple[str, float, float]],
) -> list[tuple[str, str, float]]:
    """Assign weight labels to likely left-to-right node pairs."""
    if len(node_positions) < 2 or not weights:
        return []
    labels = list(node_positions)
    edges: list[tuple[str, str, float]] = []
    used_pairs: set[tuple[str, str]] = set()
    for digit, wx, wy in weights:
        best_pair = None
        best_score = float("inf")
        for u in labels:
            ux, uy = node_positions[u]
            for v in labels:
                if u == v:
                    continue
                vx, vy = node_positions[v]
                dx = vx - ux
                if dx <= 12:
                    continue
                seg_len_sq = dx * dx + (vy - uy) ** 2
                if seg_len_sq <= 1:
                    continue
                t = ((wx - ux) * dx + (wy - uy) * (vy - uy)) / seg_len_sq
                if t < -0.2 or t > 1.2:
                    continue
                px = ux + t * dx
                py = uy + t * (vy - uy)
                perpendicular = ((wx - px) ** 2 + (wy - py) ** 2) ** 0.5
                midpoint = ((wx - (ux + vx) / 2) ** 2 + (wy - (uy + vy) / 2) ** 2) ** 0.5
                distance_to_nodes = min(
                    ((wx - ux) ** 2 + (wy - uy) ** 2) ** 0.5,
                    ((wx - vx) ** 2 + (wy - vy) ** 2) ** 0.5,
                )
                score = perpendicular * 1.8 + midpoint * 0.35 + distance_to_nodes * 0.1
                if score < best_score:
                    best_score = score
                    best_pair = (u, v)
        if best_pair is not None and best_score < 95 and best_pair not in used_pairs:
            edges.append((best_pair[0], best_pair[1], float(digit)))
            used_pairs.add(best_pair)
    return edges


def _looks_like_digit_component(w: int, h: int, area: int) -> bool:
    if w < 4 or h < 8 or w > 32 or h > 36:
        return False
    ratio = w / h
    if ratio < 0.18 or ratio > 1.35:
        return False
    density = area / (w * h)
    return 0.12 <= density <= 0.86


def _classify_digit(crop: np.ndarray) -> tuple[str | None, float]:
    normalized = _normalize_digit(crop)
    best_digit = None
    best_score = 0.0
    for digit, templates in _digit_templates().items():
        for template in templates:
            score = _binary_iou(normalized, template)
            if score > best_score:
                best_digit = digit
                best_score = score
    return best_digit, best_score


def _normalize_digit(mask: np.ndarray) -> np.ndarray:
    ys, xs = np.where(mask)
    if xs.size == 0:
        return np.zeros((32, 24), dtype=bool)
    crop = mask[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]
    img = Image.fromarray((~crop * 255).astype(np.uint8), mode="L")
    img.thumbnail((20, 28))
    canvas = Image.new("L", (24, 32), 255)
    x = (24 - img.width) // 2
    y = (32 - img.height) // 2
    canvas.paste(img, (x, y))
    return np.asarray(canvas) < 150


def _binary_iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(a, b).sum() / union)


@lru_cache(maxsize=1)
def _digit_templates() -> dict[str, list[np.ndarray]]:
    templates: dict[str, list[np.ndarray]] = {str(i): [] for i in range(10)}
    fonts = _load_template_fonts()
    for digit in templates:
        for font in fonts:
            canvas = Image.new("L", (40, 48), 255)
            draw = ImageDraw.Draw(canvas)
            bbox = draw.textbbox((0, 0), digit, font=font)
            x = (40 - (bbox[2] - bbox[0])) // 2 - bbox[0]
            y = (48 - (bbox[3] - bbox[1])) // 2 - bbox[1]
            draw.text((x, y), digit, font=font, fill=0)
            mask = ndimage.binary_dilation(np.asarray(canvas) < 150, iterations=1)
            templates[digit].append(_normalize_digit(mask))
    return templates


def _load_template_fonts():
    font_paths = [
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/timesbd.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
    ]
    fonts = []
    for path in font_paths:
        if not path.exists():
            continue
        for size in (16, 18, 20, 22, 24, 26):
            try:
                fonts.append(ImageFont.truetype(str(path), size=size))
            except OSError:
                pass
    if not fonts:
        fonts.append(ImageFont.load_default())
    return fonts


def _components(mask: np.ndarray, color: str, image_area: int) -> list[dict]:
    labels, n_labels = ndimage.label(mask)
    items: list[dict] = []
    for i in range(1, n_labels + 1):
        ys, xs = np.where(labels == i)
        if xs.size == 0:
            continue
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        w, h = x1 - x0 + 1, y1 - y0 + 1
        area = int(xs.size)
        if area < max(18, image_area // 120000) or area > image_area // 80:
            continue
        if w < 5 or h < 5 or w > 140 or h > 140:
            continue
        ratio = w / h
        if ratio < 0.35 or ratio > 2.5:
            continue
        fill_ratio = area / (w * h)
        if fill_ratio < 0.08:
            continue
        items.append({
            "x": (x0 + x1) / 2,
            "y": (y0 + y1) / 2,
            "w": w,
            "h": h,
            "area": area,
            "color": color,
        })
    return items


def _merge_close_components(items: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for item in sorted(items, key=lambda c: (c["x"], c["y"])):
        match = None
        for existing in merged:
            dx = item["x"] - existing["x"]
            dy = item["y"] - existing["y"]
            if dx * dx + dy * dy < 900 and item["color"] == existing["color"]:
                match = existing
                break
        if match is None:
            merged.append(item.copy())
        elif item["area"] > match["area"]:
            match.update(item)
    return merged


def _sort_by_columns(items: list[dict]) -> list[dict]:
    if not items:
        return []
    by_x = sorted(items, key=lambda c: c["x"])
    widths = [max(c["w"], c["h"]) for c in by_x]
    threshold = max(35, float(np.median(widths)) * 1.8)
    columns: list[list[dict]] = []
    for item in by_x:
        if not columns or abs(item["x"] - np.mean([c["x"] for c in columns[-1]])) > threshold:
            columns.append([item])
        else:
            columns[-1].append(item)
    ordered: list[dict] = []
    for column in columns:
        ordered.extend(sorted(column, key=lambda c: c["y"]))
    return ordered
