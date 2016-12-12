u"""config info."""


import os


def __root():
    u"""Return root path."""
    import os
    current_path = os.path.dirname(os.path.realpath(__file__))
    # print current_path
    return os.path.dirname(current_path)


ROOT_PATH = __root()
# print os.path.realpath(__file__)
# print __file__
# print ROOT_PATH
