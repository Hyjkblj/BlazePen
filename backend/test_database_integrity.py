"""数据库完整性识别测试。"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from database.integrity import is_unique_constraint_conflict


class DatabaseIntegrityTestCase(unittest.TestCase):
    """验证唯一约束冲突识别优先走结构化字段，而不是只靠异常文本。"""

    def test_should_recognize_postgres_unique_conflict_by_sqlstate_and_constraint(self):
        """PostgreSQL 场景下应优先使用 SQLSTATE 与约束名判断。"""
        orig = SimpleNamespace(
            pgcode="23505",
            diag=SimpleNamespace(constraint_name="uq_training_rounds_session_round"),
        )
        err = IntegrityError("insert", {"id": "x"}, orig)

        self.assertTrue(
            is_unique_constraint_conflict(
                err,
                constraint_name="uq_training_rounds_session_round",
            )
        )

    def test_should_recognize_mysql_duplicate_by_errno_and_message_tokens(self):
        """MySQL 场景下应能用 errno 先识别唯一冲突，再配合文本确认目标约束。"""
        orig = SimpleNamespace(
            errno=1062,
            sqlstate="23000",
            args=(1062, "Duplicate entry 's-1-1' for key 'uq_training_rounds_session_round'"),
        )
        err = IntegrityError("insert", {"id": "x"}, orig)

        self.assertTrue(
            is_unique_constraint_conflict(
                err,
                constraint_name="uq_training_rounds_session_round",
                fallback_token_groups=(("duplicate entry", "uq_training_rounds_session_round"),),
            )
        )

    def test_should_recognize_sqlite_unique_conflict_by_error_code(self):
        """SQLite 场景下应能识别唯一冲突错误码，并用兜底 token 确认目标表。"""
        orig = SimpleNamespace(
            sqlite_errorcode=2067,
            sqlite_errorname="SQLITE_CONSTRAINT_UNIQUE",
            args=("UNIQUE constraint failed: training_rounds.session_id, training_rounds.round_no",),
        )
        err = IntegrityError("insert", {"id": "x"}, orig)

        self.assertTrue(
            is_unique_constraint_conflict(
                err,
                constraint_name="uq_training_rounds_session_round",
                fallback_token_groups=(("training_rounds", "session_id", "round_no"),),
            )
        )

    def test_should_reject_non_unique_integrity_error_even_if_text_contains_table_name(self):
        """如果结构化字段已明确说明不是唯一冲突，就不应再被文本误判。"""
        orig = SimpleNamespace(
            sqlite_errorcode=787,
            sqlite_errorname="SQLITE_CONSTRAINT_FOREIGNKEY",
            args=("FOREIGN KEY constraint failed: training_rounds",),
        )
        err = IntegrityError("insert", {"id": "x"}, orig)

        self.assertFalse(
            is_unique_constraint_conflict(
                err,
                constraint_name="uq_training_rounds_session_round",
                fallback_token_groups=(("training_rounds",),),
            )
        )


if __name__ == "__main__":
    unittest.main()
