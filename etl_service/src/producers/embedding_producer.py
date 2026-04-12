"""Publishes EMBEDDING_UPDATED events to the embedding-updates topic."""

import json
import uuid
from datetime import datetime, timezone
from confluent_kafka import Producer
from config.kafka_config import KafkaConfig
from loguru import logger


class EmbeddingProducer:
    def __init__(self):
        cfg = KafkaConfig.from_env()
        self.topic = cfg.topics.get("embedding_updates", "embedding-updates")
        self.producer = Producer({"bootstrap.servers": cfg.bootstrap_servers})

    def _delivery_report(self, err, msg):
        if err:
            logger.error(f"Embedding event delivery failed: {err}")

    def publish(
        self,
        embedding_type: str,
        entity_id: str,
        source_event_id: str | None = None,
        priority: str = "NORMAL",
    ):
        event = {
            "eventId": str(uuid.uuid4()),
            "eventType": "EMBEDDING_UPDATED",
            "aggregateId": entity_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "data": {
                "embeddingType": embedding_type,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "priority": priority,
                "sourceEventId": source_event_id,
            },
        }
        self.producer.produce(
            self.topic,
            key=entity_id,
            value=json.dumps(event),
            callback=self._delivery_report,
        )
        self.producer.poll(0)

    def flush(self):
        self.producer.flush(timeout=5)
