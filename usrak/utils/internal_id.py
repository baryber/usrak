import uuid


def generate_internal_id_from_str() -> str:
    return str(uuid.uuid4())
