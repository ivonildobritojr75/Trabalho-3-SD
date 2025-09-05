# server/db.py
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    original_name TEXT,
    original_ext TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    duration_sec REAL,
    fps REAL,
    width INTEGER,
    height INTEGER,
    filter TEXT,
    created_at TEXT,
    path_original TEXT,
    path_processed TEXT,
    thumb_frame TEXT,
    thumb_gif TEXT
);
"""

COLUMNS = [
    'id','original_name','original_ext','mime_type','size_bytes','duration_sec','fps','width','height',
    'filter','created_at','path_original','path_processed','thumb_frame','thumb_gif'
]

def connect(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

_conn_cache = {}
def _get_conn(db_path: str):
    if db_path not in _conn_cache:
        _conn_cache[db_path] = connect(db_path)
    return _conn_cache[db_path]

def init_db(db_path: str):
    conn = _get_conn(db_path)
    conn.execute(SCHEMA)
    conn.commit()

# Para simplificar, usaremos o arquivo padrão 'server.db'
DEFAULT_DB = 'server.db'

def insert_video(meta: dict):
    conn = _get_conn(DEFAULT_DB)
    q = f"INSERT OR REPLACE INTO videos ({', '.join(COLUMNS)}) VALUES ({', '.join(['?']*len(COLUMNS))})"
    values = [meta.get(k) for k in COLUMNS]
    conn.execute(q, values)
    conn.commit()

def list_videos(limit: int = 100):
    conn = _get_conn(DEFAULT_DB)
    cur = conn.execute("SELECT * FROM videos ORDER BY created_at DESC LIMIT ?", (limit,))
    return [dict(r) for r in cur.fetchall()]

def get_video(vid: str):
    conn = _get_conn(DEFAULT_DB)
    cur = conn.execute("SELECT * FROM videos WHERE id = ?", (vid,))
    row = cur.fetchone()
    return dict(row) if row else None
