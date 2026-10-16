"""Allowed background tasks. No user-supplied code is executed."""
import time


def add_numbers(payload):
    a = payload["a"]
    b = payload["b"]
    if not isinstance(a, (int, float)) or isinstance(a, bool):
        raise ValueError("a must be a number")
    if not isinstance(b, (int, float)) or isinstance(b, bool):
        raise ValueError("b must be a number")
    return {"sum": a + b}


def uppercase(payload):
    value = payload["text"]
    if not isinstance(value, str):
        raise ValueError("text must be a string")
    return {"text": value.upper()}


def pause(payload):
    seconds = payload["seconds"]
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not 0 <= seconds <= 5:
        raise ValueError("seconds must be between 0 and 5")
    time.sleep(seconds)
    return {"slept_seconds": seconds}


TASKS = {"add_numbers": add_numbers, "uppercase": uppercase, "pause": pause}
