# Copyright (c) 2026 [wangdong]. All Rights Reserved.
# 非商业使用，未经授权禁止商用。详见 LICENSE 文件。
"""运筹学模型求解工具 — 程序入口。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from or_solver.app import App

if __name__ == "__main__":
    App().mainloop()