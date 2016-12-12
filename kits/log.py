u"""write log to file."""
import logging
from .config import ROOT_PATH


def get_logger(name):
    u"""Return logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(u'{}/logs/{}.log'.format(ROOT_PATH,
                                                                name))
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter\
        (u'%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
