"""历史记录 API — 接入 SQLite 持久化，查询训练和 Prep 历史记录"""

import sqlite3
from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from jarvis.paths import CACHE_DIR
from jarvis.persistence import TrainingDB

router = APIRouter()

# ── 数据库单例 ──
_db_path = CACHE_DIR / "training_sessions.db"


def _get_training_db() -> TrainingDB | None:
    try:
        return TrainingDB(_db_path)
    except Exception:
        return None


def _get_prep_db() -> sqlite3.Connection | None:
    """获取 prep_history 表的连接（与 training DB 共用同一个文件）"""
    try:
        _db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(_db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prep_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                industry    TEXT NOT NULL,
                scenario    TEXT NOT NULL,
                engine_mode TEXT,
                summary     TEXT
            )
            """
        )
        conn.commit()
        return conn
    except Exception:
        return None


class HistoryItem(BaseModel):
    id: int | str
    type: Literal["prep", "training"]
    title: str
    date: str
    industry: str
    score: int | None = None


@router.get("/items")
async def get_history():
    """获取历史记录列表（训练 + Prep）"""
    items: list[dict] = []

    # ── 训练记录 ──
    tdb = _get_training_db()
    if tdb is not None:
        try:
            for s in tdb.list_sessions():
                date_str = s.get("created_at", "")[:10]
                items.append({
                    "id": s["id"],
                    "type": "training",
                    "title": f"{s.get('industry', '')}-{s.get('scenario', '')}",
                    "date": date_str,
                    "industry": s.get("industry", ""),
                    "score": s.get("final_score"),
                })
        except Exception:
            pass

    # ── Prep 记录 ──
    pdb = _get_prep_db()
    if pdb is not None:
        try:
            rows = pdb.execute(
                "SELECT id, created_at, industry, scenario, engine_mode, summary "
                "FROM prep_history ORDER BY created_at DESC"
            ).fetchall()
            for r in rows:
                items.append({
                    "id": f"prep-{r['id']}",
                    "type": "prep",
                    "title": r["scenario"][:50],
                    "date": r["created_at"][:10],
                    "industry": r["industry"],
                    "score": None,
                })
        except Exception:
            pass
        finally:
            pdb.close()

    # 按日期降序排列
    items.sort(key=lambda x: x["date"], reverse=True)
    return {"items": items, "total": len(items)}


@router.delete("/items/{item_id}")
async def delete_history_item(item_id: str):
    """删除历史记录"""
    # 训练记录删除
    if not item_id.startswith("prep-"):
        tdb = _get_training_db()
        if tdb is not None:
            tdb.delete_session(item_id)
        return {"message": f"Training session {item_id} deleted"}

    # Prep 记录删除
    prep_id = item_id.replace("prep-", "")
    pdb = _get_prep_db()
    if pdb is not None:
        try:
            pdb.execute("DELETE FROM prep_history WHERE id = ?", (prep_id,))
            pdb.commit()
        finally:
            pdb.close()
    return {"message": f"Prep record {item_id} deleted"}


@router.post("/prep")
async def save_prep_record(industry: str, scenario: str, engine_mode: str = "hybrid", summary: str = ""):
    """保存 Prep 记录（供 smartprep 路由调用）"""
    pdb = _get_prep_db()
    if pdb is None:
        return {"message": "DB unavailable", "id": None}
    try:
        cursor = pdb.execute(
            "INSERT INTO prep_history (created_at, industry, scenario, engine_mode, summary) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), industry, scenario[:200], engine_mode, summary[:500]),
        )
        pdb.commit()
        return {"message": "Saved", "id": f"prep-{cursor.lastrowid}"}
    finally:
        pdb.close()
