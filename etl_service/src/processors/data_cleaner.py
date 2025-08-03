def parse_post_behavior_event(event: dict):
    return {
        "user_id": event["data"]["userId"],
        "post_id": event["aggregateId"],
        "timestamp": event["timestamp"],
    }
