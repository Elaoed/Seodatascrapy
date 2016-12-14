u"""config info."""
import os


def __root():
    u"""Return root path."""
    current_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.dirname(current_path)

ROOT_PATH = __root()
