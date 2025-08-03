import uuid
import numpy as np


def uuid_to_int64(uuid_str):
    return np.int64(uuid.UUID(uuid_str).int % (2**63))  # stay in int64 range


def int64_to_uuid(int64_val):
    return str(uuid.UUID(int=int64_val))
