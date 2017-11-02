# -*- coding: utf-8 -*-

from config.conf import conf
from kits.log import get_logger
from kits.redispool import Redispool

def initialize():
    if 'redis' not in conf:
        conf['redis'] = Redispool(),
    if 'logger' not in conf:

        conf['logger'] = get_logger('acceptRequest')
