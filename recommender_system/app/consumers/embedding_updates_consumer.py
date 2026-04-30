"""Consumes EMBEDDING_UPDATED events from Kafka with per-user debouncing."""

import asyncio
import json
import time
import threading
from typing import Dict
from confluent_kafka import Consumer, KafkaError
from kafka_config.schemas.validate import validate_json_message
from loguru import logger


DEBOUNCE_SECONDS = float(__import__("os").getenv("EMBEDDING_DEBOUNCE_SECONDS", "5"))


class EmbeddingUpdatesConsumer:
    def __init__(
        self,
        pipeline,
        redis_config,
        bootstrap_servers: str,
        topic: str = "embedding-updates",
    ):
        self.pipeline = pipeline
        self.redis = redis_config
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self._pending: Dict[str, float] = {}
        self._lock = threading.Lock()

    async def start(self):
        loop = asyncio.get_event_loop()
        poll_task = loop.run_in_executor(None, self._poll_loop, loop)
        flush_task = asyncio.ensure_future(self._flush_loop())
        await asyncio.gather(poll_task, flush_task, return_exceptions=True)

    def _poll_loop(self, loop: asyncio.AbstractEventLoop):
        consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": "recommender-embedding-updates",
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
            }
        )
        consumer.subscribe([self.topic])
        logger.info(f"EmbeddingUpdatesConsumer subscribed to {self.topic}")

        try:
            while True:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka error: {msg.error()}")
                    continue

                try:
                    raw_msg = msg.value().decode("utf-8")
                    is_valid, payload, error = validate_json_message(
                        self.topic, raw_msg
                    )
                    if not is_valid or payload is None:
                        logger.warning(
                            f"Skipping malformed embedding-updates message: {error}"
                        )
                        continue

                    data = payload.get("data", {})
                    entity_type = data.get("embeddingType") or data.get("entityType", "")
                    entity_id = payload.get("aggregateId") or data.get("entityId", "")
                    priority = data.get("priority", "NORMAL")
                    if entity_type == "user" and entity_id:
                        if priority == "HIGH":
                            asyncio.run_coroutine_threadsafe(
                                self._recompute_user(entity_id),
                                loop,
                            )
                            continue
                        with self._lock:
                            self._pending[entity_id] = time.monotonic()
                except Exception as e:
                    logger.warning(f"Bad embedding-updates message: {e}")
        except Exception as e:
            logger.error(f"EmbeddingUpdatesConsumer poll loop died: {e}")
        finally:
            consumer.close()

    async def _flush_loop(self):
        while True:
            await asyncio.sleep(DEBOUNCE_SECONDS)
            now = time.monotonic()
            to_flush = []
            with self._lock:
                for user_id, ts in list(self._pending.items()):
                    if now - ts >= DEBOUNCE_SECONDS:
                        to_flush.append(user_id)
                        del self._pending[user_id]

            for user_id in to_flush:
                await self._recompute_user(user_id)

    async def _recompute_user(self, user_id: str):
        try:
            await self.pipeline.recommend(
                user_id=user_id,
                context={},
                use_cache=False,
            )
            logger.info(f"Recomputed recommendation feed for user {user_id}")
        except Exception as e:
            logger.error(f"Recommendation recompute failed for {user_id}: {e}")
