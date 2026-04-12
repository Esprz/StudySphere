import json
from src.consumers.base_consumer import BaseConsumer
from src.processors.event_processor import EventProcessor
from loguru import logger


class UserEventConsumer(BaseConsumer):
    def __init__(self, vector_store, postgres_store):
        super().__init__(topic_key="user_events")
        self.vector_store = vector_store
        self.postgres_store = postgres_store
        self.processor = EventProcessor(vector_store, postgres_store)

    def get_event_type(self, raw_msg: str) -> str:
        """
        Extracts the event type from the raw message.
        Assumes the message is a JSON string with an 'eventType' key.
        """
        try:
            data = json.loads(raw_msg)
            return data.get("eventType", "unknown")
        except json.JSONDecodeError:
            return "invalid_json"

    def handle_message(self, raw_msg: str):
        logger.info(f"📬 [User] Received message from {self.topic_name}: {raw_msg}")
        try:
            eventType = self.get_event_type(raw_msg)
            data = json.loads(raw_msg)
            if eventType == "USER_CREATED":
                self.process_user_created(data)
            elif eventType == "USER_UPDATED":
                self.process_user_updated(data)
            elif eventType == "USER_DELETED":
                self.process_user_deleted(data)
            elif eventType in {"USER_FOLLOWED", "USER_UNFOLLOWED"}:
                self.process_follow_event(data, eventType)
            else:
                logger.error(
                    f"❌ [User] Unknown event type: {eventType} for message: {raw_msg}"
                )

        except json.JSONDecodeError as e:
            logger.error(f"❌ [User] JSON decode error: {e} for message: {raw_msg}")

    def process_user_created(self, data):
        logger.info(f"Processing user created event: {data}")
        try:
            user_id = data.get("aggregateId")
            if user_id:
                self.processor.process_user_created(user_id)
                logger.info(f"✅ [User] Initialized embedding for user {user_id}")
            else:
                logger.error(f"❌ [User] Missing user ID in data: {data}")

        except Exception as e:
            logger.error(f"❌ [User] Error processing user created event: {e}")

    def process_user_updated(self, data):
        try:
            user_id = data.get("aggregateId")
            self.processor.process_user_updated(user_id, data.get("data", {}))
        except Exception as e:
            logger.error(f"❌ [User] Error processing user updated event: {e}")

    def process_user_deleted(self, data):
        try:
            user_id = data.get("aggregateId")
            self.processor.process_user_deleted(user_id)
        except Exception as e:
            logger.error(f"❌ [User] Error processing user deleted event: {e}")

    def process_follow_event(self, data, event_type: str):
        try:
            payload = data.get("data", {})
            metadata = data.get("metadata", {})
            self.processor.process_aux_behavior(
                user_id=data.get("aggregateId"),
                event_type=event_type,
                event_id=data.get("eventId"),
                source=metadata.get("source"),
                extra_data=payload,
            )
        except Exception as e:
            logger.error(f"❌ [User] Error processing {event_type}: {e}")
