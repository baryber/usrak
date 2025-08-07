import uuid


def generate_identifier_from_str() -> str:
    return str(uuid.uuid4())
