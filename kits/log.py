"""write log to file."""
import logging
import os
import sys

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def get_logger(filename, logger_name=None, formatter=None, level=None, add_sys=True):
    """Return logger."""
    if not logger_name:
        logger_name = filename

    if not formatter:
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
        # '%Y-%m-%d %X'

    if not level:
        level = logging.INFO

    logger = logging.getLogger()

    if add_sys:
        stdout_hdlr = logging.StreamHandler(sys.stdout)
        log_filter = LogFilter(logging.WARNING)
        stdout_hdlr.addFilter(log_filter)
        logger.addHandler(stdout_hdlr)

        stderr_hdlr = logging.StreamHandler(sys.stderr)
        stderr_hdlr.setLevel(logging.WARNING)
        logger.addHandler(stderr_hdlr)

    file_handler = logging.FileHandler('%s/logs/%s.log' % (ROOT_PATH, filename))
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

class LogFilter(logging.Filter):
    """Filters (lets through) all messages with level < LEVEL"""

    def __init__(self, level):
        super(LogFilter, self).__init__()
        self.level = level

    def filter(self, record):
        return record.levelno < self.level
