"""自动保存 / 加载 JSON 数据。

路径规则：程序运行目录下的 autosave_<name>.json。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _autosave_path(name: str) -> Path:
    """返回自动保存文件的绝对路径。"""
    # 保存到 main.py 所在目录（src 的上两级）
    here = Path(__file__).resolve().parent.parent.parent.parent
    return here / f"autosave_{name}.json"


def save(name: str, data: dict[str, Any]) -> None:
    """将数据序列化为 JSON 写入磁盘，失败时静默忽略。"""
    try:
        path = _autosave_path(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load(name: str) -> dict[str, Any] | None:
    """从磁盘加载 JSON，文件不存在或解析失败时返回 None。"""
    path = _autosave_path(name)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_to_path(path: str, data: dict[str, Any]) -> None:
    """将数据保存到指定路径（用于手动存盘）。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_from_path(path: str) -> dict[str, Any]:
    """从指定路径加载 JSON（用于手动导入）。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
