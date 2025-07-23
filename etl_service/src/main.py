import asyncio
import signal
import sys
from loguru import logger
from sqlalchemy import text

from config.logging_config import setup_logging
from config.kafka_config import KafkaConfig
from config.database_config import DatabaseConfig

from src.storage.faiss_manager import FaissManager
from src.consumers.behavior_event_consumer import BehaviorEventConsumer
from src.consumers.post_event_consumer import PostEventConsumer


class ETLService:
    def __init__(self):
        setup_logging()
        logger.info("🚀 Initializing ETL Service...")

        self.kafka_config = KafkaConfig.from_env()
        self.db_config = DatabaseConfig()
        self.faiss_manager = FaissManager()

        self.consumers = []
        self.running = False

    async def health_check(self) -> bool:
        """check the health of the service components"""
        try:
            # TODO: Check Redis once it's implemented

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
            PostEventConsumer(self.faiss_manager, self.db_config),
            BehaviorEventConsumer(self.faiss_manager, self.db_config),
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
