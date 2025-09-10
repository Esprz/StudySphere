class FilterBase:
    def __init__(self, name):
        self.name = name

    def filter(self, user_id, candidates, entity_type="posts", context=None):
        raise NotImplementedError("Subclasses should implement this method")
