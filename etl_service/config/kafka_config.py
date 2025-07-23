import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    bootstrap_servers: str
    consumer_group_prefix: str
    topics: Dict[str, str]
    consumer_config: Dict[str, Any]

    @classmethod
    def from_env(cls) -> "KafkaConfig":
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            consumer_group_prefix=os.getenv(
                "KAFKA_CONSUMER_GROUP_PREFIX", "etl_service"
            ),
            topics={
                "post_events": os.getenv("POST_TOPIC", "post-events"),
                "behavior_events": os.getenv("BEHAVIOR_TOPIC", "behavior-events"),
                "search_events": os.getenv("SEARCH_TOPIC", "search-events"),
            },
            consumer_config={
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 1000,
                "session.timeout.ms": 30000,
                "heartbeat.interval.ms": 10000,
                "max.poll.interval.ms": 600000,
            },
        )
