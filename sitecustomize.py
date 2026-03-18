"""仓库根目录下的 Python 启动补丁。

用于让从项目根目录执行 `python -m unittest ...` 时，
也能稳定导入 `backend/` 目录里的 `api`、`training` 等顶层模块。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

backend_path = str(BACKEND_DIR)
if BACKEND_DIR.is_dir() and backend_path not in sys.path:
    # 把 backend 放到最前面，保证测试入口与在 backend 目录内执行时行为一致。
    sys.path.insert(0, backend_path)
