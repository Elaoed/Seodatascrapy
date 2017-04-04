# encoding=utf8
"""Redis pool using one module in different files"""
import json
import redis
import time
import os
from functools import wraps
from log import get_logger

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REDIS_LOGGER = get_logger('redis')


def redis_excepts(orig_func):
    u"""try excepts around each query
    """
    @wraps(orig_func)
    def wrapper(*args, **kwargs):
        try:
            return orig_func(*args, **kwargs)
        except redis.exceptions.ConnectionError as err:
            REDIS_LOGGER.error(err)
        except redis.exceptions.TimeoutError as err:
            REDIS_LOGGER.error(err)
        except Exception as err:
            REDIS_LOGGER.critical(err)
    return wrapper


def get_connection():
    """Expose api to context"""
    if not Redispool.redis_pool:
        try:
            with open(ROOT_PATH + '/config/db.conf') as config:
                conf = json.load(config)
                Redispool.redis_pool = redis.ConnectionPool(
                    host=conf[u'redis'][u'host'],
                    port=conf[u'redis'][u'port'],
                    db=conf[u'redis'][u'db'],
                    password=conf[u'redis'][u'password']
                )
        except IOError:
            raise Exception(ROOT_PATH + '/config/db.conf does not exist')
    return redis.StrictRedis(connection_pool=Redispool.redis_pool)


class Redispool(object):
    u"""Full function of Redis Beckend
    """

    redis_pool = None

    def __init__(self, *args, **kwargs):
        self.queue = None
        if 'queue' in kwargs:
            self.queue = kwargs['queue']

#################################################
#    Commands in key-value
#################################################
    @redis_excepts
    def set(self, key, value):
        u"""Set key and value"""
        REDIS_LOGGER.info("set %s %s", key, value)
        return get_connection().set(key, value)

    @redis_excepts
    def get(self, key):
        u"""Get from redis using key"""
        REDIS_LOGGER.info("get %s", key)
        return get_connection().get(key)

    @redis_excepts
    def setnx(self, key, value):
        u"""set value into redis if key does not exist
        """
        REDIS_LOGGER.info("setnx %s %s", key, value)
        return get_connection().setnx(key, value)

    @redis_excepts
    def setex(self, key, ttl, value):
        u"""set key-value into redis with ttl
        """
        REDIS_LOGGER.info("setex %s, %s, %s", key, ttl, value)
        return get_connection().setex(key, ttl, value)

    @redis_excepts
    def delete(self, key):
        u"""Del key
        """
        REDIS_LOGGER.info("del %s", key)
        return get_connection().delete(key)

    @redis_excepts
    def incr(self, key):
        u"""increase key by one
        """
        REDIS_LOGGER.info("incr %s", key)
        return get_connection().incr(key)

    @redis_excepts
    def expire(self, key, ttl):
        u"""indicate expire for a certain key
        """
        REDIS_LOGGER.info("expire %s %s", key, ttl)
        return get_connection().expire(key, ttl)

    @redis_excepts
    def exists(self, key):
        u"""determine if given key exist
        """
        REDIS_LOGGER.info("exists %s", key)
        return get_connection().exists(key)

    @redis_excepts
    def mset(self, **kwargs):
        u"""multiple set keys and values
            example: r.mset(hello="h", world="w")
        """
        REDIS_LOGGER.info("mset %s", kwargs)
        return get_connection().mset(kwargs)

    @redis_excepts
    def getset(self, key, value):
        u"""get value of key and update value to prameter value
            If key has no value before. return None then
        """
        REDIS_LOGGER.info("getset %s %s", key, value)
        return get_connection().getset(key, value)

    @redis_excepts
    def mget(self, *keys):
        u"""Get the value of all the given keys
        """
        if isinstance(keys[0], list):
            keys = keys[0]
        keys = [str(i) for i in keys]
        REDIS_LOGGER.info("mget %s", ' '.join(keys))
        return get_connection().mget(keys)

    @redis_excepts
    def append(self, key, value):
        u"""Append a value to a key
        """
        REDIS_LOGGER.info("append %s %s", key, value)
        return get_connection().append(key, value)

    @redis_excepts
    def substr(self, key, start, stop):
        u"""get sub string of value of key
        """
        REDIS_LOGGER.info("substr %s %d %d", key, start, stop)
        return get_connection().substr(key, start, stop)

    @redis_excepts
    def incrby(self, key, number):
        u"""increase value of gievn key by number
        """
        REDIS_LOGGER.info("incrby %s %d", key, number)
        return get_connection().incrby(key, number)

############################################################
#    Commands in list
############################################################
    @redis_excepts
    def push(self, value, queue=None):
        u"""Push item into the queue
        """
        if not queue:
            queue = self.queue
        if not queue:
            raise Exception("queue does not exist")
        REDIS_LOGGER.info("rpush %s %s", queue, value)
        return get_connection().rpush(queue, value)

    @redis_excepts
    def pop(self, queue=None):
        u"""Pop from queue"""
        if not queue:
            queue = self.queue
        if not queue:
            raise Exception("queue does not exist")
        REDIS_LOGGER.info("blpop:%s", self.queue)
        item = get_connection().blpop(queue, timeout=None)
        return item[1] if item else None

    @redis_excepts
    def lrange(self, key, start, stop):
        u"""decrease value of given key by number
        """
        REDIS_LOGGER.info("lrange %s %d %d", key, start, stop)
        return get_connection().lrange(key, start, stop)

    @redis_excepts
    def lindex(self, key, pos):
        u"""fetch individual items from the list with LINDEX.
        """
        REDIS_LOGGER.info("lindex %s %d", key, pos)
        return get_connection().lindex(key, pos)

################################
#   Commands used on SET values
################################
    @redis_excepts
    def sadd(self, name, member):
        u"""add a item into a set
        """
        REDIS_LOGGER.info("sadd %s %s", name, member)
        return get_connection().sadd(name, member)

    @redis_excepts
    def smembers(self, name):
        u"""list members of a set
        """
        REDIS_LOGGER.info("smembers %s", name)
        return get_connection().smembers(name)

    @redis_excepts
    def sismembers(self, name, member):
        u"""determine if item in set collection
        """
        REDIS_LOGGER.info("sismembers %s, %s", name, member)
        return get_connection().sismember(name, member)

    @redis_excepts
    def srem(self, name, member):
        u"""remove a item from set
        """
        REDIS_LOGGER.info("srem %s %s", name, member)
        return get_connection().srem(name, member)

#########################################
#   Hashes in Redis
#########################################
    @redis_excepts
    def hset(self, name, key, value):
        u"""Store the value at the key in the hash
        """
        REDIS_LOGGER.info("hset %s %s %s", name, key, value)
        return get_connection().hset(name, key, value)

    @redis_excepts
    def hmset(self, name, mapping):
        u"""multiple hset
            example: redispool.hmset(key, {'a':1, 'b':2})
        """
        REDIS_LOGGER.info("hmset %s %s", name, str(mapping))
        return get_connection().hmset(name, mapping)

    @redis_excepts
    def hget(self, name, key):
        u"""Fetche the value at the given hash key
        """
        REDIS_LOGGER.info("hget %s %s", name, key)
        return get_connection().hget(name, key)

    @redis_excepts
    def hgetall(self, name):
        u"""Fetche the entire hash
        """
        REDIS_LOGGER.info("hgetall %s", name)
        return get_connection().hgetall(name)

    @redis_excepts
    def hdel(self, name, key):
        u"""Remove a key from the hash, if it exists
        """
        REDIS_LOGGER.info("hdel %s %s", name, key)
        return get_connection().hdel(name, key)

    @redis_excepts
    def hincrby(self, name, key, increment):
        u"""add increment into filed of key
        """
        REDIS_LOGGER.info("hincrby %s %s %d", name, key, increment)
        return get_connection().hincrby(name, key, increment)

#########################################
#   ZSET in Redis
#########################################

    @redis_excepts
    def zadd(self, key, score, member):
        u"""Add member with the given score to the ZSET
        """
        REDIS_LOGGER.info("zadd %s %s %s", key, score, member)
        return get_connection().zadd(key, score, member)

    @redis_excepts
    def zrem(self, key, member):
        u"""Remove the item from the ZSET, if it exists
        """
        REDIS_LOGGER.info("zrem %s %s", key, member)
        return get_connection().zrem(key, member)

    @redis_excepts
    def zrange(self, key, start, stop, withscores=False):
        u"""Fetche the items in the ZSET from their positions in sorted order
        """
        REDIS_LOGGER.info("zrange %s %s %s %s", key, start, stop, withscores)
        return get_connection().zrange(key, start, stop, withscores=withscores)

    @redis_excepts
    def zrevrange(self, key, start, stop, withscores=False):
        u"""reverse range function
        """
        REDIS_LOGGER.info("zrevrange: %s %s %s %s", key, start, stop, withscores)
        return get_connection().zrevrange(key, start, stop, withscores=withscores)

    @redis_excepts
    def zrangebyscore(self, key, start, stop, withscores=False):
        u"""Fetche items in the ZSET based on a range of scores. can you sort yourself?
        """
        REDIS_LOGGER.info("zrangebyscore %s %s %s %s", key, start, stop, withscores)
        return get_connection().zrangebyscore(key, start, stop, withscores=withscores)

    @redis_excepts
    def zrevrangebyscore(self, key, start, stop, withscores=False):
        u"""pass
        """
        REDIS_LOGGER.info("zrevrangebyscore: %s %s %s", key, start, stop)
        return get_connection().zrevrangebyscore(key, start, stop, withscores=withscores)

    @redis_excepts
    def zscore(self, key, member):
        u"""return the ordered collection.
        """
        REDIS_LOGGER.info("zscore: %s %s", key, member)
        return get_connection().zscore(key, member)

    @redis_excepts
    def zincrby(self, key, member, increment):
        u"""Increment the score of a member in a sorted set
        """
        REDIS_LOGGER.info("zincrby: %s %s %f", key, member, increment)
        return get_connection().zincrby(key, member, increment)

    # @redis_excepts
    # def zinterstore(self, dest_zsets, sets_num, *args, aggregation='max'):
    #     u"""find those entries that are in all of the SETs and ZSETs, combining their scores
    #     """
    #     REDIS_LOGGER.info("zinterstore: dest_zets:%s" % (dest_zsets))
        # return get_connection().zinterstore(dest, keys)


def test():
    u"""Just test
    """
    r = Redispool()
    key = 'test'
    value = "value"
# test key-value   ################################

    def test_key_value():
        print "Test starts. key:%s ........." % key
        r.delete(key)
        assert(r.exists(key) is False)
        r.set(key, 234)
        assert(r.exists(key) is True)
        r.set(key, 1)
        r.incr(key)
        assert(int(r.get(key)) == 2)
        r.incrby(key, 3)
        assert(int(r.get(key)) == 5)
        r.expire(key, 3)
        assert(r.exists(key) is True)
        time.sleep(3)
        assert(r.exists(key) is False)
        r.mset(hello="h", world="w")
        assert(r.mget("hello", "world")[0] in "h")
        assert(r.mget("hello", "world")[1] in "w")
        r.append("hello", "eworld")
        assert(r.get("hello") in "heworld")
        assert(r.substr("hello", 0, 3) in "hewo")
        r.delete(key)
        assert(r.getset(key, "value") is None)
        assert(r.get(key) in "value")
        print "All key-value functions pass the test......\n"
    # test_key_value()

#  test List ######################################

    def test_list():
        r.delete(key)
        r.push(value, key)
        assert(r.lrange(key, 0, 0)[0] == value)
        assert(r.lindex(key, 0) == value)
        assert(r.pop(key) == value)
        r2 = Redispool(queue=key)
        r2.push(value, key)
        assert(r2.pop(key) == value)
        print "All list functions pass the test......\n"
    test_list()

#  test Set ######################################

    def test_set():
        r.delete(key)
        r.sadd(key, value)
        assert(value in r.smembers(key))
        assert(r.sismembers(key, value) is True)
        r.srem(key, value)
        assert(value not in r.smembers(key))
        assert(r.sismembers(key, value) is False)
        print "All set functions pass the test......\n"
    test_set()

#  test Hash ######################################

    def test_hash():
        r.delete(key)
        r.hset(key, "q", "q")
        r.hset(key, "w", "w")
        r.hset(key, "e", 1)
        assert(r.hget(key, "q") == "q")
        assert(r.hget(key, "w") == "w")
        assert(r.hget(key, "e") == "1")
        r.hincrby(key, "e", 3)
        assert(r.hget(key, "e") == "4")
        print r.hgetall(key)
        r.hdel(key, "e")
        print r.hgetall(key)
        r.delete(key)
        assert(r.exists(key) is False)
        r.hmset(key, {"a": "a", "b": "b", "c": 1})
        print r.hgetall(key)
        # assert(r.exists(key) is False)
        print "All hash functions pass the test......\n"
    test_hash()

#  test Zset ######################################
    def test_zset():
        r.delete(key)
        r.zadd(key, value, 100)
        r.zadd(key, value + "2", 200)
        r.zadd(key, value + "3", 300)
        r.zadd(key, value + "4", 150)
        # ==============================================
        assert("value4" in r.zrange(key, 0, -1))
        r.zrem(key, value + "4")
        assert("value4" not in r.zrange(key, 0, -1))
        print r.zrange(key, 0, -1)
        print r.zrange(key, 0, -1, withscores=True)
        print r.zrevrange(key, 0, -1)
        print r.zrevrange(key, 0, -1, withscores=True)
        assert(r.zscore(key, "value3") == 300.0)
        r.zincrby(key, "value3", 100.5)
        assert(r.zscore(key, "value3") == 400.5)
        print r.zrangebyscore(key, 0, 200)
        print r.zrangebyscore(key, 0, 200, withscores=True)
        print r.zrevrangebyscore(key, 1000, 100)
        print r.zrevrangebyscore(key, 1000, 100, withscores=True)
        print "All zset functions pass the test..........\n"
    test_zset()
    print "*******Congratulations!!! All the test have been passed ~ "

# test()
