import os
import psycopg
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

SQL_DIR = "recommender_system/sql"
SQL_FUNCTIONS_DIR = os.path.join(SQL_DIR, "functions")
CREATE_SCHEMA_FILE = os.path.join(SQL_DIR, "create_schema.sql")
DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")


def run_create_schema(cursor):
    with open(CREATE_SCHEMA_FILE, "r") as f:
        schema_sql = f.read()
    cursor.execute(schema_sql)
    logger.info("✅ Ran create_schema.sql")


def register_sql_functions(cursor):
    for filename in os.listdir(SQL_FUNCTIONS_DIR):
        if filename.endswith(".sql"):
            with open(os.path.join(SQL_FUNCTIONS_DIR, filename), "r") as f:
                sql = f.read()
            cursor.execute(sql)
            logger.info(f"✅ Registered SQL function: {filename}")


def main():
    with psycopg.connect(DB_CONNECTION_STRING) as conn:
        with conn.cursor() as cursor:
            run_create_schema(cursor)
            register_sql_functions(cursor)
        conn.commit()


if __name__ == "__main__":
    main()
