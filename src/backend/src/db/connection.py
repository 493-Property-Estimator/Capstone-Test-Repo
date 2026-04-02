from __future__ import annotations

import sqlite3
from pathlib import Path

from data_sourcing.database import connect as connect_sqlite


def connect(db_path: Path) -> sqlite3.Connection:
    return connect_sqlite(db_path)
