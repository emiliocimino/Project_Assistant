import os
from src import MEMORY_DIR
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


DB_PATH = os.path.join(MEMORY_DIR, "memory.db")

async def get_sqlite_connection():
    if not os.path.isdir(MEMORY_DIR):
        os.mkdir(MEMORY_DIR)

    conn = await aiosqlite.connect(DB_PATH)
    checkpointer = AsyncSqliteSaver(conn)
    return conn, checkpointer


def _label_from_checkpoint_tuple(tup, thread_id: str) -> str:
    """First human message in the thread, trimmed, as a human-readable label.
    Falls back to a short id fragment for a thread that was created but never
    actually asked anything."""
    if tup is None:
        return thread_id[:8]
    messages = tup.checkpoint.get("channel_values", {}).get("messages", [])
    for m in messages:
        if getattr(m, "type", None) == "human" and getattr(m, "content", None):
            text = " ".join(m.content.split())
            return text[:60] + ("…" if len(text) > 60 else "")
    return thread_id[:8]


async def list_threads(limit: int = 30) -> list[dict]:
    """Recent conversations, newest first, for a sidebar / resume list.

    AsyncSqliteSaver has no public "list all threads" call, only per-thread
    listing (alist/aget_tuple), so this queries the checkpoints table directly.
    Ordered by SQLite's own rowid rather than checkpoint_id, since rowid is
    guaranteed monotonic by SQLite itself and doesn't depend on assumptions
    about how LangGraph formats checkpoint ids. This does depend on the
    two-table (checkpoints, writes) schema of langgraph-checkpoint-sqlite,
    which is an implementation detail, not a documented public contract; a
    LangGraph upgrade that changes it would break this function specifically,
    not the rest of the app.
    """
    db_path = DB_PATH
    if not os.path.isfile(db_path):
        return []

    conn = await aiosqlite.connect(db_path)
    try:
        checkpointer = AsyncSqliteSaver(conn)
        cursor = await conn.execute(
            "SELECT thread_id, MAX(rowid) AS last_seen FROM checkpoints "
            "GROUP BY thread_id ORDER BY last_seen DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()

        threads = []
        for thread_id, _ in rows:
            config = {"configurable": {"thread_id": thread_id}}
            tup = await checkpointer.aget_tuple(config)
            threads.append({
                "thread_id": thread_id,
                "label": _label_from_checkpoint_tuple(tup, thread_id),
            })
        return threads
    finally:
        await conn.close()


async def load_history(thread_id: str) -> list[dict]:
    """Rehydrate a Gradio-displayable [{"role", "content"}, ...] history from a
    thread's latest checkpoint. Does not detect a stranded human-in-the-loop
    interrupt (see note in app.py about resuming mid-approval); it only
    reconstructs the message log for display.
    """
    db_path = DB_PATH
    if not os.path.isfile(db_path):
        return []

    conn = await aiosqlite.connect(db_path)
    try:
        checkpointer = AsyncSqliteSaver(conn)
        config = {"configurable": {"thread_id": thread_id}}
        tup = await checkpointer.aget_tuple(config)
        if tup is None:
            return []

        messages = tup.checkpoint.get("channel_values", {}).get("messages", [])
        role_map = {"human": "user", "ai": "assistant"}
        history = []
        for m in messages:
            role = role_map.get(getattr(m, "type", None))
            content = getattr(m, "content", None)
            if role and content:
                history.append({"role": role, "content": content})
        return history
    finally:
        await conn.close()