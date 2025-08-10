import json
from src.consumers.base_consumer import BaseConsumer


class BehaviorEventConsumer(BaseConsumer):
    def __init__(self, faiss_manager, db_config):
        super().__init__(topic_key="behavior_events")
        self.faiss = faiss_manager
        self.db = db_config

    def handle_message(self, raw_msg: str):
        print(f"📬 [Behavior] Received message from {self.topic_name}: {raw_msg}")
        try:
            data = json.loads(raw_msg)
            print(f"📊 [Behavior] Processed data: {data}")
            # TODO: Add your processing logic here
        except json.JSONDecodeError as e:
            print(f"❌ [Behavior] JSON decode error: {e} for message: {raw_msg}")
