"""Изолированная база корпоративного сервиса."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def database():
    path=Path(os.environ.get('CORPORATE_DB',Path(__file__).with_name('corporate.db')))
    con=sqlite3.connect(path,timeout=10)
    con.row_factory=sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()
