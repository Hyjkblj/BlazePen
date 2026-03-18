"""数据库完整性错误识别工具。"""

from __future__ import annotations

from typing import Iterable, Sequence

from sqlalchemy.exc import IntegrityError


# PostgreSQL 的唯一冲突通常会暴露标准 SQLSTATE。
POSTGRES_UNIQUE_SQLSTATES = {"23505"}
# MySQL 常见驱动会用 errno 表示“重复键”。
MYSQL_UNIQUE_ERRNOS = {1062}
# sqlite3 在 Python 3.11+ 常会暴露这两个唯一冲突错误码。
SQLITE_UNIQUE_ERROR_CODES = {1555, 2067}

# 下面这些是常见的“不是唯一冲突”的结构化错误码，用来尽早排除误判。
# `23000` 在 MySQL 中只是完整性错误大类，不能直接当成“非唯一冲突”。
NON_UNIQUE_SQLSTATES = {"23502", "23503", "23514"}
NON_UNIQUE_MYSQL_ERRNOS = {1048, 1216, 1217, 1451, 1452}
NON_UNIQUE_SQLITE_ERROR_CODES = {787, 1299, 1811}


def is_unique_constraint_conflict(
    exc: IntegrityError,
    *,
    constraint_name: str,
    fallback_token_groups: Sequence[Iterable[str]] | None = None,
) -> bool:
    """优先用结构化字段识别唯一约束冲突，文本匹配只做兜底。

    说明：
    1. PostgreSQL 驱动通常会带 `pgcode/sqlstate` 和 `diag.constraint_name`
    2. MySQL / SQLite 驱动常会带数值错误码
    3. 只有结构化字段不足时，才退回到文本关键词组合判断
    """
    orig = getattr(exc, "orig", None)
    structured_result = _match_structured_unique_conflict(
        orig=orig,
        constraint_name=constraint_name,
    )
    if structured_result is not None:
        return structured_result

    lowered_text = "\n".join(_iter_integrity_error_texts(exc)).lower()
    if constraint_name.lower() in lowered_text:
        return True

    for token_group in fallback_token_groups or ():
        normalized_group = [str(token).lower() for token in token_group if token]
        if normalized_group and all(token in lowered_text for token in normalized_group):
            return True
    return False


def _match_structured_unique_conflict(
    orig: object,
    constraint_name: str,
) -> bool | None:
    """先从驱动暴露的结构化字段判断是否属于唯一约束冲突。

    返回约定：
    1. `True` 表示已明确识别为目标唯一约束冲突
    2. `False` 表示已明确识别为别的完整性错误，不必再走文本兜底
    3. `None` 表示结构化字段不足，交给文本兜底继续判断
    """
    if orig is None:
        return None

    sqlstate = _extract_sqlstate(orig)
    if sqlstate in POSTGRES_UNIQUE_SQLSTATES:
        matched_constraint_name = _extract_constraint_name(orig)
        if matched_constraint_name:
            return matched_constraint_name == constraint_name
        return None
    if sqlstate in NON_UNIQUE_SQLSTATES:
        return False

    vendor_error_code = _extract_vendor_error_code(orig)
    if vendor_error_code in MYSQL_UNIQUE_ERRNOS or vendor_error_code in SQLITE_UNIQUE_ERROR_CODES:
        matched_constraint_name = _extract_constraint_name(orig)
        if matched_constraint_name:
            return matched_constraint_name == constraint_name
        return None
    if vendor_error_code in NON_UNIQUE_MYSQL_ERRNOS or vendor_error_code in NON_UNIQUE_SQLITE_ERROR_CODES:
        return False

    return None


def _extract_sqlstate(orig: object) -> str | None:
    """兼容不同驱动的 SQLSTATE 提取方式。"""
    sqlstate = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
    if sqlstate is None:
        return None
    return str(sqlstate).strip()


def _extract_constraint_name(orig: object) -> str | None:
    """尽量从驱动诊断信息里提取约束名。"""
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name:
        return str(constraint_name).strip()

    # 某些驱动会把约束名直接挂在异常对象上。
    direct_constraint_name = getattr(orig, "constraint_name", None)
    if direct_constraint_name:
        return str(direct_constraint_name).strip()
    return None


def _extract_vendor_error_code(orig: object) -> int | None:
    """提取 MySQL / SQLite 常见驱动暴露的数值错误码。"""
    candidate_codes = (
        getattr(orig, "errno", None),
        getattr(orig, "sqlite_errorcode", None),
    )
    for candidate in candidate_codes:
        if candidate is None:
            continue
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue

    args = getattr(orig, "args", None)
    if isinstance(args, (list, tuple)) and args:
        try:
            return int(args[0])
        except (TypeError, ValueError):
            return None
    return None


def _iter_integrity_error_texts(exc: IntegrityError) -> list[str]:
    """收集 SQLAlchemy 异常及驱动原始异常里的文本，降低单一字符串格式耦合。"""
    texts: list[str] = []
    for candidate in (exc, getattr(exc, "orig", None)):
        if candidate is None:
            continue

        candidate_text = str(candidate).strip()
        if candidate_text and candidate_text not in texts:
            texts.append(candidate_text)

        candidate_args = getattr(candidate, "args", None)
        if not isinstance(candidate_args, (list, tuple)):
            continue
        for item in candidate_args:
            item_text = str(item).strip()
            if item_text and item_text not in texts:
                texts.append(item_text)
    return texts
