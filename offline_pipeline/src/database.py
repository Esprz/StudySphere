"""Database helpers for offline jobs."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg.rows import dict_row


def normalize_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != "schema"
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(filtered_query), parts.fragment)
    )


@contextmanager
def get_connection(database_url: str) -> Iterator[psycopg.Connection]:
    connection = psycopg.connect(normalize_database_url(database_url), row_factory=dict_row)
    try:
        yield connection
    finally:
        connection.close()
