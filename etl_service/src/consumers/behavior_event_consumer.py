import json
from src.processors.event_processor import EventProcessor
from src.consumers.base_consumer import BaseConsumer
from loguru import logger


class BehaviorEventConsumer(BaseConsumer):
    def __init__(self, vector_store, db_config):
        super().__init__(topic_key="behavior_events")
        self.vector_store = vector_store
        self.db = db_config
        self.processor = EventProcessor(vector_store, db_config)

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
        logger.info(f"📬 [Behavior] Received message from {self.topic_name}: {raw_msg}")
        try:
            data = json.loads(raw_msg)

            event_type = self.get_event_type(raw_msg)

            if event_type.startswith("POST_"):
                self.process_post_interaction(data, event_type)
            elif event_type in {"SEARCH", "SEARCH_PERFORMED"}:
                self.process_search_event(data)
            elif event_type == "COMMENT_CREATED":
                self.process_comment_event(data)
            elif event_type in {"START_FOCUS", "END_FOCUS", "ADD_TASK", "COMPLETE_TASK"}:
                self.process_aux_behavior(data, event_type)
            else:
                logger.error(
                    f"❌ [Behavior] Unknown event type: {event_type} for message: {raw_msg}"
                )

            logger.info(f"📊 [Behavior] Processed data: {data}")

        except json.JSONDecodeError as e:
            logger.error(f"❌ [Behavior] JSON decode error: {e} for message: {raw_msg}")

    def process_post_interaction(self, data: dict, event_type: str):
        try:
            post_id = data.get("aggregateId")
            user_id = data.get("data", {}).get("userId")
            timestamp = data.get("timestamp")
            metadata = data.get("metadata", {})
            session_id = data.get("sessionId") or metadata.get("sessionId")
            dwell_ms = data.get("data", {}).get("dwellMs")
            position = data.get("data", {}).get("position")

            self.processor.process_post_interaction(
                user_id=user_id,
                post_id=post_id,
                behavior_type=event_type,
                timestamp=timestamp,
                event_id=data.get("eventId"),
                session_id=session_id,
                position=position,
                dwell_ms=dwell_ms,
                source=metadata.get("source"),
                extra_data=data.get("data", {}),
            )

        except Exception as e:
            logger.error(f"❌ [Behavior] Error processing post interaction: {e}")

    def process_search_event(self, data: dict):
        try:
            user_id = data.get("aggregateId")
            search_query = data.get("data", {}).get("query")
            timestamp = data.get("timestamp")
            metadata = data.get("metadata", {})
            session_id = data.get("sessionId") or metadata.get("sessionId")

            self.processor.process_search_behavior(
                user_id=user_id,
                search_query=search_query,
                timestamp=timestamp,
                event_id=data.get("eventId"),
                session_id=session_id,
                source=metadata.get("source"),
                extra_data=data.get("data", {}),
            )

        except Exception as e:
            logger.error(f"❌ [Behavior] Error processing search event: {e}")

    def process_comment_event(self, data: dict):
        try:
            payload = data.get("data", {})
            metadata = data.get("metadata", {})
            session_id = data.get("sessionId") or metadata.get("sessionId")

            self.processor.process_comment_created(
                user_id=payload.get("userId"),
                post_id=payload.get("postId"),
                comment_id=data.get("aggregateId"),
                timestamp=data.get("timestamp"),
                event_id=data.get("eventId"),
                session_id=session_id,
                source=metadata.get("source"),
                extra_data=payload,
            )
        except Exception as e:
            logger.error(f"❌ [Behavior] Error processing comment event: {e}")

    def process_aux_behavior(self, data: dict, event_type: str):
        try:
            payload = data.get("data", {})
            metadata = data.get("metadata", {})
            session_id = data.get("sessionId") or metadata.get("sessionId")

            self.processor.process_aux_behavior(
                user_id=payload.get("userId"),
                event_type=event_type,
                event_id=data.get("eventId"),
                post_id=payload.get("postId"),
                search_term=payload.get("query"),
                session_id=session_id,
                source=metadata.get("source"),
                extra_data=payload,
            )
        except Exception as e:
            logger.error(f"❌ [Behavior] Error processing {event_type}: {e}")
