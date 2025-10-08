import asyncio
import signal
import sys
from loguru import logger
from sqlalchemy import text

from config.logging_config import setup_logging
from config.kafka_config import KafkaConfig
from config.database_config import DatabaseConfig

from src.storage.postgres_store import PostgresStore
from src.storage.qdrant_manager import QdrantManager
from src.storage.vector_store import VectorStore
from src.consumers.behavior_event_consumer import BehaviorEventConsumer
from src.consumers.post_event_consumer import PostEventConsumer


class ETLService:
    def __init__(self):
        setup_logging()
        logger.info("🚀 Initializing ETL Service...")

        self.kafka_config = KafkaConfig.from_env()
        self.db_config = DatabaseConfig()
        self.postgres_store = PostgresStore(db_config=self.db_config)
        self.qdrant_manager = QdrantManager()
        self.vector_store = VectorStore(self.qdrant_manager)

        self.consumers = []
        self.running = False

    async def health_check(self) -> bool:
        """check the health of the service components"""
        try:
            # Check Database
            with self.db_config.get_session() as session:
                session.execute(text("SELECT 1"))

            logger.info("✅ All services healthy")
            return True

        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False

    def setup_consumers(self):
        """set up Kafka consumers"""
        logger.info("🔧 Setting up consumers...")

        self.consumers = [
            PostEventConsumer(self.vector_store, self.postgres_store),
            BehaviorEventConsumer(self.vector_store, self.postgres_store),
        ]

        logger.info(f"📝 {len(self.consumers)} consumers configured")

    async def start_consumers(self):
        """start all consumers"""
        if not self.consumers:
            logger.warning("⚠️ No consumers configured")
            return
        logger.info("🔄 Starting consumers...")
        tasks = []

        for consumer in self.consumers:
            task = asyncio.create_task(consumer.start())
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    def setup_signal_handlers(self):
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, shutting down...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        logger.info("🎯 Starting ETL Service...")

        if not await self.health_check():
            logger.error("❌ Health check failed, exiting...")
            sys.exit(1)

        self.setup_signal_handlers()

        self.setup_consumers()

        self.running = True
        logger.info("✅ ETL Service started successfully")

        try:
            await self.start_consumers()
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ ETL Service error: {e}")
        finally:
            logger.info("🛑 ETL Service stopped")


if __name__ == "__main__":
    service = ETLService()
    asyncio.run(service.run())
