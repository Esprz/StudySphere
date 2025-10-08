import asyncio
from abc import ABC, abstractmethod
from confluent_kafka import Consumer, KafkaError
from config.kafka_config import KafkaConfig
from loguru import logger


class BaseConsumer(ABC):
    def __init__(self, topic_key: str):
        self.cfg = KafkaConfig.from_env()
        self.topic_name = self.cfg.topics[topic_key]
        self.group_id = f"{self.cfg.consumer_group_prefix}-{topic_key}"

        self.consumer = Consumer(
            {
                "bootstrap.servers": self.cfg.bootstrap_servers,
                "group.id": self.group_id,
                **self.cfg.consumer_config,
            }
        )
        logger.info(
            f"🔧 Consumer initialized for topic: {self.topic_name} (group: {self.group_id})"
        )

    async def start(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._consume_loop)
        self.consumer.start()
        logger.info(f"🟢 Consumer for topic {self.topic_name} started")

    def _consume_loop(self):
        try:
            self.consumer.subscribe([self.topic_name])
            logger.info(
                f"🟢 Subscribed to topic: {self.topic_name} (group: {self.group_id})",
                flush=True,
            )
            logger.info(
                f"🔧 Bootstrap servers: {self.cfg.bootstrap_servers}", flush=True
            )
            logger.info(f"🔧 Consumer config: {self.cfg.consumer_config}")

            while True:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                        continue

                self.handle_message(msg.value().decode("utf-8"))

        except KeyboardInterrupt:
            logger.info(f"🛑 Stopping consumer for topic: {self.topic_name}")
        except Exception as e:
            logger.error(f"❌ [FATAL ERROR IN CONSUMER LOOP] {e}")
        finally:
            self.consumer.close()
            logger.info(f"🔧 Consumer for topic {self.topic_name} closed")

    @abstractmethod
    def handle_message(self, raw_msg: str):
        """Each consumer must implement this method to process messages."""
        pass
