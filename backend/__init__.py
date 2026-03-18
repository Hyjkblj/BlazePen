"""后端包初始化。

用于兼容两种测试入口：
1. 在 `backend/` 目录下直接执行 `python -m unittest ...`
2. 在仓库根目录执行 `python -m unittest backend.test_xxx`

第二种情况下，测试文件内部仍使用 `api`、`training` 等历史顶层导入，
因此这里把 `backend/` 目录补入 `sys.path`，保持两种入口行为一致。
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
backend_path = str(BACKEND_DIR)

if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
