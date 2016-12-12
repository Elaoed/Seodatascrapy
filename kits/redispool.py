# -*- coding: utf-8 -*-
u"""Queue to send emails to verify register user."""
import json
from functools import wraps
import redis
from .config import ROOT_PATH
from .log import get_logger


REDIS_LOGGER = get_logger(u'redis')

def redis_excepts():
    u"""Catch MySQLdb.OperationalError."""

    def decorator(func):
        u"""Decorate funcs cursor called."""
        wraps(func)

        def decorated_function(*args, **kwargs):
            u"""Decorated function that will be returned."""
            try:
                return func(*args, **kwargs)
            except redis.ConnectionError:
                REDIS_LOGGER.error(u'redis.ConnectionError')
                return None
            except:
                REDIS_LOGGER.error(u'UndefinedError')
                return None

        return decorated_function

    return decorator


def get_connection():
    u"""Get redis connection from connection pool."""
    if not _redispool.redis_pool:
        with open(ROOT_PATH + u'/conf/db.conf') as config:
            conf = json.load(config)
            _redispool.redis_pool = redis.ConnectionPool(
                host=conf[u'redis'][u'host'],
                port=conf[u'redis'][u'port'],
                db=conf[u'redis'][u'db'],
                password=conf[u'redis'][u'password'])
    return redis.StrictRedis(connection_pool=_redispool.redis_pool)


class _redispool(object):
    u"""Simple Queue with Redis Backend"""
    redis_pool = None

    def __init__(self, name=u'', namespace='pool'):
        u"""The default connection parameters are:
                host='localhost', port=6379, db=0."""
        self.namespace = namespace
        self.key = str(u'{}:{}'.format(namespace, name))

    def __map_key(self, key):
        u"""Generate unique key."""
        return str(u'{}:{}'.format(self.namespace, key))

    #########################################
    ### set key-value namespace:key-value ###
    #########################################
    @redis_excepts()
    def setex(self, key, value, expire=600):
        u"""Set key value with expire."""
        REDIS_LOGGER.info(u'SETEX: %s %s %s',
                          self.__map_key(key), value, expire)
        get_connection().setex(self.__map_key(key), value, expire)

    #######################################
    ### get value by key: namespace:key ###
    #######################################
    @redis_excepts()
    def get(self, key):
        u"""Get key value."""
        REDIS_LOGGER.info(u'GET: %s', self.__map_key(key))
        return get_connection().get(self.__map_key(key))

    ##########################################
    ### delete value by key: namespace:key ###
    ##########################################
    @redis_excepts()
    def delete(self, key):
        u"""Get key value."""
        REDIS_LOGGER.info(u'DELETE: %s', self.__map_key(key))
        return get_connection().delete(self.__map_key(key))

    #########################################
    ### put value to queue namespace:name ###
    #########################################
    @redis_excepts()
    def put(self, value):
        u"""Put item into the queue."""
        REDIS_LOGGER.info(u'PUT: %s-%s', self.key, value)
        get_connection().rpush(self.key, value)

    ###########################################
    ### pop value from queue namespace:name ###
    ###########################################
    @redis_excepts()
    def pop(self):
        u"""return an item from the queue."""
        item = get_connection().blpop(self.key, timeout=None)
        REDIS_LOGGER.info(u'POP: %s', item[1] if item else u'')
        return item[1] if item else None
