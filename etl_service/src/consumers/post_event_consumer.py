import json
from src.processors.event_processor import EventProcessor
from src.consumers.base_consumer import BaseConsumer
from loguru import logger


class PostEventConsumer(BaseConsumer):
    def __init__(self, vector_store, postgres_store):
        super().__init__(topic_key="post_events")
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
        logger.info(f"📬 [Post] Received message from {self.topic_name}: {raw_msg}")

        try:
            eventType = self.get_event_type(raw_msg)
            data = json.loads(raw_msg)
            if eventType == "POST_CREATED":
                self.process_post_created(data)
            elif eventType == "POST_UPDATED":
                self.process_post_updated(data)
            elif eventType == "POST_DELETED":
                self.process_post_deleted(data)
            else:
                logger.error(
                    f"❌ [Post] Unknown event type: {eventType} for message: {raw_msg}"
                )

        except json.JSONDecodeError as e:
            logger.error(f"❌ [Post] JSON decode error: {e} for message: {raw_msg}")

    def process_post_created(self, data):
        """
        Process the 'post_created' event.
        This method can be extended to handle additional logic if needed.
        """

        logger.info(f"Processing post created event: {data}")
        try:
            post_data = data.get("data", {})
            post_id = data.get("aggregateId")
            metadata = data.get("metadata", {})

            self.processor.process_post_created(
                post_id=post_id,
                title=post_data.get("title", ""),
                content=post_data.get("content", ""),
                tags=post_data.get("tags", []),
                author_id=post_data.get("authorId"),
                timestamp=data.get("timestamp"),
                event_id=data.get("eventId"),
                source=metadata.get("source"),
                extra_data=post_data,
            )

        except Exception as e:
            logger.error(
                f"❌ [Post] Error processing post created event: {e} for data: {data}"
            )

    def process_post_updated(self, data):
        """
        Process the 'post_updated' event.
        This method can be extended to handle additional logic if needed.
        """

        logger.info(f"Processing post updated event: {data}")

        try:
            post_data = data.get("data", {})
            metadata = data.get("metadata", {})

            self.processor.process_post_updated(
                post_id=data.get("aggregateId"),
                title=post_data.get("updatedFields", {}).get(
                    "title", post_data.get("title", "")
                ),
                content=post_data.get("updatedFields", {}).get(
                    "content", post_data.get("content", "")
                ),
                tags=post_data.get("updatedFields", {}).get(
                    "tags", post_data.get("tags", [])
                ),
                author_id=post_data.get("authorId"),
                timestamp=data.get("timestamp"),
                event_id=data.get("eventId"),
                source=metadata.get("source"),
                extra_data=post_data,
            )

        except Exception as e:
            logger.error(
                f"❌ [Post] Error processing post updated event: {e} for data: {data}"
            )

    def process_post_deleted(self, data):
        """
        Process the 'post_deleted' event.
        This method can be extended to handle additional logic if needed.
        """

        logger.info(f"Processing post deleted event: {data}")

        try:
            post_id = data.get("aggregateId")
            if post_id:
                self.processor.process_post_deleted(post_id)
                logger.info(f"✅ [Post] Deleted post vector for post ID: {post_id}")
            else:
                logger.error(f"❌ [Post] Missing post_id for message: {post_id}")

        except Exception as e:
            logger.error(
                f"❌ [Post] Error processing post deleted event: {e} for data: {data}"
            )
