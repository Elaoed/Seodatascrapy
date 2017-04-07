u"""write log to file."""
import logging
import os

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def get_logger(filename, logger_name=None):
    u"""Return logger."""
    if not logger_name:
        logger_name = filename

    logger = logging.getLogger(logger_name)

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(name)s:%(lineno)d - %(message)s',
        '%Y-%m-%d %X')

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    file_handler = logging.FileHandler(u'%s/logs/%s.log' % (ROOT_PATH, filename))
    file_handler.setLevel(logging.INFO)

    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # logger.addHandler(stream_handler)
    logger.setLevel(logging.INFO)

    return logger
