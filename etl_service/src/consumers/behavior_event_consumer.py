import json
from src.processors.event_processor import EventProcessor
from src.consumers.base_consumer import BaseConsumer


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
        print(f"📬 [Behavior] Received message from {self.topic_name}: {raw_msg}")
        try:
            data = json.loads(raw_msg)

            event_type = self.get_event_type(raw_msg)

            if event_type.startswith("POST_"):
                self.process_post_interaction(data, event_type)
            elif event_type == "SEARCH":
                self.process_search_event(data)
            else:
                print(
                    f"❌ [Behavior] Unknown event type: {event_type} for message: {raw_msg}"
                )

            print(f"📊 [Behavior] Processed data: {data}")

        except json.JSONDecodeError as e:
            print(f"❌ [Behavior] JSON decode error: {e} for message: {raw_msg}")

    def process_post_interaction(self, data: dict, event_type: str):
        try:
            post_id = data.get("aggregateId")
            user_id = data.get("data", {}).get("userId")
            timestamp = data.get("timestamp")

            self.processor.process_post_interaction(
                user_id, post_id, event_type, timestamp
            )

        except Exception as e:
            print(f"❌ [Behavior] Error processing post interaction: {e}")

    def process_search_event(self, data: dict):
        try:
            user_id = data.get("aggregateId")
            search_query = data.get("data", {}).get("query")
            timestamp = data.get("timestamp")

            self.processor.process_search_behavior(user_id, search_query, timestamp)

        except Exception as e:
            print(f"❌ [Behavior] Error processing search event: {e}")
