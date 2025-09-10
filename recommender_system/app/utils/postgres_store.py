import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


class PostgresStore:
    def __init__(self):
        self.db_connection_string = os.getenv("DB_CONNECTION_STRING")
        self.psycopg_conn = psycopg.connect(self.db_connection_string)

    def get_session(self) -> psycopg.Connection:
        return self.psycopg_conn
