import os, datetime, orjson
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()

def db_url() -> str:
    # Use MySQL if provided, else SQLite file
    return os.getenv("DATABASE_URL", "sqlite:///data.db")

def get_engine() -> Engine:
    eng = create_engine(db_url(), future=True)
    with eng.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS brand_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_url TEXT NOT NULL,
            snapshot_json BLOB NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """))
    return eng

ENGINE = get_engine()

def save_snapshot(store_url: str, payload: dict) -> int:
    blob = orjson.dumps(payload)
    with ENGINE.begin() as conn:
        res = conn.execute(
            text("INSERT INTO brand_snapshots (store_url, snapshot_json, created_at) VALUES (:u, :j, :t)"),
            {"u": store_url, "j": blob, "t": datetime.datetime.utcnow()}
        )
        return int(res.lastrowid)

def latest_snapshots(limit: int = 10):
    with ENGINE.begin() as conn:
        rows = conn.execute(
            text("SELECT id, store_url, created_at FROM brand_snapshots ORDER BY id DESC LIMIT :l"),
            {"l": limit}
        ).mappings().all()
    return [dict(r) for r in rows]