import json
from src.consumers.base_consumer import BaseConsumer
from src.processors.event_processor import EventProcessor


class UserEventConsumer(BaseConsumer):
    def __init__(self, vector_store, db_config):
        super().__init__(topic_key="user_events")
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
        print(f"📬 [User] Received message from {self.topic_name}: {raw_msg}")
        try:
            eventType = self.get_event_type(raw_msg)
            data = json.loads(raw_msg)
            if eventType == "USER_CREATED":
                self.process_user_created(data)
            elif eventType == "USER_UPDATED":
                self.process_user_updated(data)
            elif eventType == "USER_DELETED":
                self.process_user_deleted(data)
            else:
                print(
                    f"❌ [User] Unknown event type: {eventType} for message: {raw_msg}"
                )

        except json.JSONDecodeError as e:
            print(f"❌ [User] JSON decode error: {e} for message: {raw_msg}")

    def process_user_created(self, data):
        print(f"Processing user created event: {data}")
        try:
            user_id = data.get("aggregateId")
            if user_id:
                self.processor.process_user_created(user_id)
                print(f"✅ [User] Initialized embedding for user {user_id}")
            else:
                print(f"❌ [User] Missing user ID in data: {data}")

        except Exception as e:
            print(f"❌ [User] Error processing user created event: {e}")
