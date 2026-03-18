"""Inspect ChromaDB sqlite schema and app-level collection usage.

This prints:
- SQLite tables / columns / indexes in the persistent ChromaDB file
- Chroma collections and counts
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from typing import Any


def _json_safe(x: Any) -> str:
    try:
        return json.dumps(x, ensure_ascii=False)
    except Exception:
        return repr(x)


def main() -> None:
    # Avoid Windows console encoding issues
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    db_path = os.path.join(project_root, "vector_db", "chroma.sqlite3")

    print(f"DB_PATH: {db_path}")
    print(f"EXISTS: {os.path.exists(db_path)}")
    if not os.path.exists(db_path):
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    print(f"\nTABLES ({len(tables)}):")
    for t in tables:
        print(f"- {t}")

    print("\nCOLUMNS:")
    for t in tables:
        cols = cur.execute(f"PRAGMA table_info({json.dumps(t)})").fetchall()
        print(f"\n[{t}]")
        for cid, name, ctype, notnull, dflt, pk in cols:
            flags = []
            if notnull:
                flags.append("NOT NULL")
            if pk:
                flags.append("PK")
            flags_s = (" " + " ".join(flags)) if flags else ""
            print(f"- {name} {ctype}{flags_s}")

    indexes = cur.execute(
        "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name"
    ).fetchall()
    print(f"\nINDEXES ({len(indexes)}):")
    for name, tbl, sql in indexes:
        print(f"- {tbl}.{name}: {sql}")

    # ChromaDB common tables include "collections"; print collection stats if present.
    if "collections" in tables:
        rows = cur.execute(
            "SELECT id, name, topic, dimension, database_id FROM collections ORDER BY name"
        ).fetchall()
        print(f"\nCOLLECTIONS ({len(rows)}):")
        for rid, name, topic, dim, database_id in rows:
            print(f"- id={rid} name={name} topic={topic} dimension={dim} database_id={database_id}")

            # Collection metadata lives in collection_metadata table in this schema.
            if "collection_metadata" in tables:
                meta_rows = cur.execute(
                    "SELECT key, str_value, int_value, float_value FROM collection_metadata WHERE collection_id=? ORDER BY key",
                    (rid,),
                ).fetchall()
                if meta_rows:
                    meta_obj = {}
                    for k, s, i, f in meta_rows:
                        meta_obj[k] = s if s is not None else (i if i is not None else f)
                    print(f"  metadata: {_json_safe(meta_obj)}")

    con.close()

    print(
        "\nAPP-LEVEL DESIGN (this project):\n"
        "- One collection: story_events\n"
        "- Document id format:\n"
        "  - event: {character_id}_{event_id}\n"
        "  - dialogue: {character_id}_{event_id}_round_{dialogue_round}\n"
        "- Stored fields:\n"
        "  - documents: combined text (story background + dialogue)\n"
        "  - metadatas: character_id, event_id, type, dialogue_round, scene, title, event_context ...\n"
    )


if __name__ == "__main__":
    main()


