import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool


class DatabaseConfig:
    def __init__(self):
        self.database_user = os.getenv("DATABASE_USER", "user")
        self.database_password = os.getenv("DATABASE_PASSWORD", "1234")
        self.database_host = os.getenv("DATABASE_HOST", "db")
        self.database_port = os.getenv("DATABASE_PORT", "5432")
        self.database_db = os.getenv("DATABASE_DB", "studysphere")

        db_connect_string = f"postgresql+psycopg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_db}"

        self.engine = create_engine(
            db_connect_string,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=os.getenv("LOG_LEVEL") == "DEBUG",
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.Base = declarative_base()

    def get_session(self):
        return self.SessionLocal()
