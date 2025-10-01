from typing import Union, Optional


def validate_unix_timestamp(ts: Union[int, float]) -> Optional[int]:
    """
    Validate whether the given value is a valid Unix timestamp in seconds.

    :param ts: The timestamp value to validate (int or float).
    :return: The timestamp if valid, None otherwise.
    """
    if not isinstance(ts, (int, float)):
        return None

    min_ts = 0
    max_ts = 4102444800

    return int(ts) if min_ts < ts < max_ts else None
