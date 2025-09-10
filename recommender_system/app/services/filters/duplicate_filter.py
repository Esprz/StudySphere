class DuplicateFilter:
    def __init__(self):
        self.name = "duplicate_filter"

    def filter(self, user_id, candidates, entity_type="posts", context=None):
        seen = set()
        filtered_candidates = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                filtered_candidates.append(candidate)
        return filtered_candidates
