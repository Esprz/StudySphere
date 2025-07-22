import json
from src.consumers.base_consumer import BaseConsumer


class PostEventConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(topic_key="post_events")
        

    def handle_message(self, raw_msg: str):
        print(f"📬 [Post] Received message from {self.topic_name}: {raw_msg}")
        try:
            data = json.loads(raw_msg)
            print(f"📊 [Post] Processed data: {data}")
            # TODO: Add your processing logic here
        except json.JSONDecodeError as e:
            print(f"❌ [Post] JSON decode error: {e} for message: {raw_msg}")
