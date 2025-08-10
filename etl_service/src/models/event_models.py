from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class PostEvent:
    event_id: str
    event_type: str
    post_id: str
    user_id: str
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchEvent:
    event_id: str
    event_type: str
    user_id: str
    search_term: str
    timestamp: datetime
