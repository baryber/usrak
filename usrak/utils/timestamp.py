from typing import Union


def validate_unix_timestamp(ts: Union[int, float]) -> bool:
    """
    Validate whether the given value is a valid Unix timestamp in seconds.

    :param ts: The timestamp value to validate (int or float).
    :return: True if the timestamp is valid, False otherwise.
    """
    if not isinstance(ts, (int, float)):
        return False

    min_ts = 0
    max_ts = 4102444800

    return min_ts < ts < max_ts
