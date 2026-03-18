"""DatabaseManager 兼容层测试。"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from database.db_manager import DatabaseManager
from models.character import Base


class DatabaseManagerTestCase(unittest.TestCase):
    """验证数据库兼容层不会因训练域解耦而丢失旧能力。"""

    def test_init_db_should_register_training_models_before_create_all(self):
        """显式建表入口在兼容模式下也应先注册训练模型。"""
        manager = DatabaseManager()

        with patch.object(manager, "_register_managed_models") as register_mock:
            with patch.object(Base.metadata, "create_all") as create_all_mock:
                manager.init_db()

        register_mock.assert_called_once_with()
        create_all_mock.assert_called_once_with(manager.engine)


if __name__ == "__main__":
    unittest.main()
