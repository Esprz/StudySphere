import json
from src.processors.event_processor import EventProcessor
from src.consumers.base_consumer import BaseConsumer


class PostEventConsumer(BaseConsumer):
    def __init__(self, faiss_manager, db_config):
        super().__init__(topic_key="post_events")
        self.faiss = faiss_manager
        self.db = db_config
        self.processor = EventProcessor(faiss_manager, db_config)

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
        print(f"📬 [Post] Received message from {self.topic_name}: {raw_msg}")
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
                print(
                    f"❌ [Post] Unknown event type: {eventType} for message: {raw_msg}"
                )

        except json.JSONDecodeError as e:
            print(f"❌ [Post] JSON decode error: {e} for message: {raw_msg}")

    def process_post_created(self, data):
        """
        Process the 'post_created' event.
        This method can be extended to handle additional logic if needed.
        """

        print(f"Processing post created event: {data}")
        try:
            post_data = data.get("data", {})
            post_id = data.get("aggregateId")

            self.processor.process_post_created(
                post_id=post_id,
                title=post_data.get("title", ""),
                content=post_data.get("content", ""),
                tags=post_data.get("tags", []),
                author_id=post_data.get("authorId"),
                timestamp=data.get("timestamp"),
            )

        except Exception as e:
            print(f"❌ [Post] Error processing post created event: {e} for data: {data}")

    def process_post_updated(self, data):
        """
        Process the 'post_updated' event.
        This method can be extended to handle additional logic if needed.
        """

        print(f"Processing post updated event: {data}")

        try:
            embedding = self.processor.generate_post_embedding(
                title=data.get("title", ""),
                content=data.get("content", ""),
                tags=data.get("tags", []),
            )

            post_id = data.get("aggregateId")

            if post_id and embedding:
                self.faiss.add_post_vector(post_id, embedding)
                print(f"✅ [Post] Updated post vector for post ID: {post_id}")
            else:
                print(f"❌ [Post] Missing post_id or embedding for for data: {data}")

        except Exception as e:
            print(f"❌ [Post] Error processing post updated event: {e} for data: {data}")

    def process_post_deleted(self, data):
        """
        Process the 'post_deleted' event.
        This method can be extended to handle additional logic if needed.
        """

        print(f"Processing post deleted event: {data}")

        try:
            post_id = data.get("aggregateId")
            if post_id:
                self.faiss.delete_post_vector(post_id)
                # TODO: Also update the deleted post related user vectors in the future
                print(f"✅ [Post] Deleted post vector for post ID: {post_id}")
            else:
                print(f"❌ [Post] Missing post_id for message: {post_id}")

        except Exception as e:
            print(f"❌ [Post] Error processing post deleted event: {e} for data: {data}")
