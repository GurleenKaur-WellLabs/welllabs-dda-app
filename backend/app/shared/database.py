from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg.rows import dict_row

from app.shared.config import settings


def get_connection() -> psycopg.Connection:
    return psycopg.connect(settings.database_url, row_factory=dict_row)


@contextmanager
def db_cursor() -> Generator:
    with get_connection() as conn:
        with conn.cursor() as cur:
            yield cur
            conn.commit()
