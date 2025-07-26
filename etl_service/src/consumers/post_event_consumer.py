import json
from src.processors.text_processor import TextProcessor
from src.consumers.base_consumer import BaseConsumer


class PostEventConsumer(BaseConsumer):
    def __init__(self, faiss_manager, db_config):
        super().__init__(topic_key="post_events")
        self.faiss = faiss_manager
        self.db = db_config
        self.processor = TextProcessor()

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
            if eventType == "post_created":
                self.process_post_created(data)
            elif eventType == "post_updated":
                self.process_post_updated(data)
            elif eventType == "post_deleted":
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
            embedding = self.processor.generate_post_embedding(
                title=data.get("title", ""),
                content=data.get("content", ""),
                tags=data.get("tags", []),
            )

            post_id = data.get("post_id")

            if post_id and embedding:
                self.faiss.add_post_vector(post_id, embedding)
                print(f"✅ [Post] Stored post vector for post ID: {post_id}")
            else:
                print(f"❌ [Post] Missing post_id or embedding for message: {raw_msg}")

        except Exception as e:
            print(
                f"❌ [Post] Error processing post created event: {e} for message: {raw_msg}"
            )

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

            post_id = data.get("post_id")

            if post_id and embedding:
                self.faiss.add_post_vector(post_id, embedding)
                print(f"✅ [Post] Updated post vector for post ID: {post_id}")
            else:
                print(f"❌ [Post] Missing post_id or embedding for message: {raw_msg}")

        except Exception as e:
            print(
                f"❌ [Post] Error processing post updated event: {e} for message: {raw_msg}"
            )

    def process_post_deleted(self, data):
        """
        Process the 'post_deleted' event.
        This method can be extended to handle additional logic if needed.
        """

        print(f"Processing post deleted event: {data}")

        try:
            post_id = data.get("post_id")
            if post_id:
                self.faiss.delete_post_vector(post_id)
                # TODO: Also update the deleted post related user vectors in the future
                print(f"✅ [Post] Deleted post vector for post ID: {post_id}")
            else:
                print(f"❌ [Post] Missing post_id for message: {raw_msg}")

        except Exception as e:
            print(
                f"❌ [Post] Error processing post deleted event: {e} for message: {raw_msg}"
            )
