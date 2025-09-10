class DiversityBase:
    def __init__(self, name):
        self.name = name

    def enhance(self, user_id, candidates, entity_type="posts", context=None):
        raise NotImplementedError("Subclasses should implement this method")
