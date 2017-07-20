# encoding=utf8
"""Redis pool using one module in different files"""
import redis
import time
import os
from functools import wraps
from kits.log import get_logger
from config.conf import REDIS_CONF

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REDIS_LOGGER = get_logger('redis')


def redis_excepts(orig_func):
    """try excepts around each query"""
    @wraps(orig_func)
    def wrapper(*args, **kwargs):
        try:
            return orig_func(*args, **kwargs)
        except redis.exceptions.ConnectionError as err:
            REDIS_LOGGER.error(err)
        except redis.exceptions.TimeoutError as err:
            REDIS_LOGGER.error(err)
        except Exception:
            REDIS_LOGGER.critical("Exception", exc_info=True)
        return ""
    return wrapper


def get_connection():
    """Expose api to context"""
    if not Redispool.redis_pool:
        Redispool.redis_pool = redis.ConnectionPool(
            host=REDIS_CONF['host'],
            port=REDIS_CONF['port'],
            db=REDIS_CONF['db'],
            password=REDIS_CONF['password']
        )
    return redis.StrictRedis(connection_pool=Redispool.redis_pool)


class Redispool(object):
    """Full function of Redis Beckend
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
        """Set key and value"""
        REDIS_LOGGER.info("set %s %s", key, value)
        return get_connection().set(key, value)

    @redis_excepts
    def get(self, key):
        """Get from redis using key"""
        REDIS_LOGGER.info("get %s", key)
        return get_connection().get(key)

    @redis_excepts
    def setnx(self, key, value):
        """set value into redis if key does not exist
        """
        REDIS_LOGGER.info("setnx %s %s", key, value)
        return get_connection().setnx(key, value)

    @redis_excepts
    def setex(self, key, ttl, value):
        """set key-value into redis with ttl
        """
        REDIS_LOGGER.info("setex %s, %s, %s", key, ttl, value)
        return get_connection().setex(key, ttl, value)

    @redis_excepts
    def delete(self, key):
        """Del key
        """
        REDIS_LOGGER.info("del %s", key)
        return get_connection().delete(key)

    @redis_excepts
    def incr(self, key):
        """increase key by one
        """
        REDIS_LOGGER.info("incr %s", key)
        return get_connection().incr(key)

    @redis_excepts
    def exists(self, key):
        """determine if given key exist
        """
        REDIS_LOGGER.info("exists %s", key)
        return get_connection().exists(key)

    @redis_excepts
    def mset(self, **kwargs):
        """multiple set keys and values
            example: r.mset(hello="h", world="w")
        """
        REDIS_LOGGER.info("mset %s", kwargs)
        return get_connection().mset(kwargs)

    @redis_excepts
    def getset(self, key, value):
        """get value of key and update value to prameter value
            If key has no value before. return None then
        """
        REDIS_LOGGER.info("getset %s %s", key, value)
        return get_connection().getset(key, value)

    @redis_excepts
    def mget(self, *keys):
        """Get the value of all the given keys
        """
        if isinstance(keys[0], list):
            keys = keys[0]
        keys = [str(i) for i in keys]
        REDIS_LOGGER.info("mget %s", ' '.join(keys))
        return get_connection().mget(keys)

    @redis_excepts
    def append(self, key, value):
        """Append a value to a key
        """
        REDIS_LOGGER.info("append %s %s", key, value)
        return get_connection().append(key, value)

    @redis_excepts
    def getrange(self, key, start, stop):
        """get a substring of the string stored at a key
        """
        REDIS_LOGGER.info("getrange %s %d %d", key, start, stop)
        return get_connection().getrange(key, start, stop)

    @redis_excepts
    def setrange(self, key, offset, value):
        """overwrite part of a string at key starting at the specified offset
        """
        REDIS_LOGGER.info("setrange %s %d %d", key, offset, value)
        return get_connection().setrange(key, offset, value)

    @redis_excepts
    def incrby(self, key, number):
        """increase value of gievn key by number
        """
        REDIS_LOGGER.info("incrby %s %d", key, number)
        return get_connection().incrby(key, number)

    @redis_excepts
    def incrbyfloat(self, key, number):
        """increase value of gievn key by number
        """
        REDIS_LOGGER.info("incrbyfloat %s %d", key, number)
        return get_connection().incrbyfloat(key, number)

    @redis_excepts
    def getbit(self, key, offset):
        pass

    @redis_excepts
    def setbit(self, key, offset):
        pass

    @redis_excepts
    def bitcount(self, key, offset):
        pass

    @redis_excepts
    def bitop(self, key, offset):
        pass

############################################################
#    Commands in list
############################################################
    @redis_excepts
    def push(self, queue=None, value=None):
        """Push item into the queue
        """
        if not queue:
            queue = self.queue
        if not queue:
            raise Exception("queue does not exist")
        REDIS_LOGGER.info("rpush %s %s", queue, value)
        return get_connection().rpush(queue, value)

    @redis_excepts
    def pop(self, queue=None):
        """Pop from queue"""
        if not queue:
            queue = self.queue
        if not queue:
            raise Exception("queue does not exist")
        REDIS_LOGGER.info("blpop:%s", self.queue)
        item = get_connection().blpop(queue, timeout=None)
        return item[1] if item else None

    @redis_excepts
    def lrange(self, key, start, stop):
        """decrease value of given key by number
        """
        REDIS_LOGGER.info("lrange %s %d %d", key, start, stop)
        return get_connection().lrange(key, start, stop)

    @redis_excepts
    def lindex(self, key, pos):
        """fetch individual items from the list with LINDEX.
        """
        REDIS_LOGGER.info("lindex %s %d", key, pos)
        return get_connection().lindex(key, pos)

    @redis_excepts
    def ltrim(self, key, start, end):
        """Trim a list to the specified range
        """
        REDIS_LOGGER.info("ltrim %s %d %d", key, start, end)
        return get_connection().ltrim(key, start, end)

    @redis_excepts
    def rpoplpush(self, skey, dkey):
        """Remove the last element in a list,
            prepend it to another list and return it
        """
        REDIS_LOGGER.info("rpoplpush %s %s", skey, dkey)
        return get_connection().rpoplpush(skey, dkey)

    @redis_excepts
    def brpoplpush(self, skey, dkey, timeout):
        """Remove the last element in a list,
            prepend it to another list and return it
            within a timeout
        """
        REDIS_LOGGER.info("rpoplpush %s %s %d", skey, dkey, timeout)
        return get_connection().brpoplpush(skey, dkey, timeout)


################################
#   Commands used on SET values
################################
    @redis_excepts
    def sadd(self, name, member):
        """add a item into a set
        """
        REDIS_LOGGER.info("sadd %s %s", name, member)
        return get_connection().sadd(name, member)

    @redis_excepts
    def smembers(self, name):
        """list members of a set
        """
        REDIS_LOGGER.info("smembers %s", name)
        return get_connection().smembers(name)

    @redis_excepts
    def sismembers(self, name, member):
        """determine if item in set collection
        """
        REDIS_LOGGER.info("sismembers %s, %s", name, member)
        return get_connection().sismember(name, member)

    @redis_excepts
    def srem(self, name, member):
        """remove a item from set
        """
        REDIS_LOGGER.info("srem %s %s", name, member)
        return get_connection().srem(name, member)

    @redis_excepts
    def scard(self, name):
        """Get the number of members in a set
        """
        REDIS_LOGGER.info("scard %s", name)
        return get_connection().scard(name)

    @redis_excepts
    def spop(self, name):
        """Remove and return a random members from a set
        """
        REDIS_LOGGER.info("spop %s", name)
        return get_connection().spop(name)

    @redis_excepts
    def smove(self, sname, dname, member):
        """Move  a member from one set to another
        """
        REDIS_LOGGER.info("smove %s %s %s", sname, dname, member)
        return get_connection().smove(sname, dname, member)

    @redis_excepts
    def srandmember(self, key, count):
        """Get one or multiple(count) random members from a set
            if count > 0. No repeat member returns
            if count < 0. May return repeat members
        """
        REDIS_LOGGER.info("srandmember %s %s", key, count)
        return get_connection().srandmember(key, count)

#########################################
#   Hashes in Redis
#########################################
    @redis_excepts
    def hset(self, name, key, value):
        """Store the value at the key in the hash
        """
        REDIS_LOGGER.info("hset %s %s %s", name, key, value)
        return get_connection().hset(name, key, value)

    @redis_excepts
    def hmset(self, name, mapping):
        """multiple hset
            example: redispool.hmset(key, {'a':1, 'b':2})
        """
        REDIS_LOGGER.info("hmset %s %s", name, str(mapping))
        return get_connection().hmset(name, mapping)

    @redis_excepts
    def hget(self, name, key):
        """Fetche the value at the given hash key
        """
        REDIS_LOGGER.info("hget %s %s", name, key)
        return get_connection().hget(name, key)

    @redis_excepts
    def hgetall(self, name):
        """Fetche the entire hash
        """
        REDIS_LOGGER.info("hgetall %s", name)
        return get_connection().hgetall(name)

    @redis_excepts
    def hdel(self, name, key):
        """Remove a key from the hash, if it exists
        """
        REDIS_LOGGER.info("hdel %s %s", name, key)
        return get_connection().hdel(name, key)

    @redis_excepts
    def hincrby(self, name, key, increment):
        """add increment into filed of key
        """
        REDIS_LOGGER.info("hincrby %s %s %d", name, key, increment)
        return get_connection().hincrby(name, key, increment)

#########################################
#   ZSET in Redis
#########################################

    @redis_excepts
    def zadd(self, key, score, member):
        """Add member with the given score to the ZSET
        """
        REDIS_LOGGER.info("zadd %s %s %s", key, score, member)
        return get_connection().zadd(key, score, member)

    @redis_excepts
    def zrem(self, key, member):
        """Remove the item from the ZSET, if it exists
        """
        REDIS_LOGGER.info("zrem %s %s", key, member)
        return get_connection().zrem(key, member)

    @redis_excepts
    def zrange(self, key, start, stop, withscores=False):
        """Fetche the items in the ZSET from their positions in sorted order
        """
        REDIS_LOGGER.info("zrange %s %s %s %s", key, start, stop, withscores)
        return get_connection().zrange(key, start, stop, withscores=withscores)

    @redis_excepts
    def zrevrange(self, key, start, stop, withscores=False):
        """reverse range function
        """
        REDIS_LOGGER.info("zrevrange: %s %s %s %s", key, start, stop, withscores)
        return get_connection().zrevrange(key, start, stop, withscores=withscores)

    @redis_excepts
    def zrangebyscore(self, key, start, stop, withscores=False):
        """Fetche items in the ZSET based on a range of scores. can you sort yourself?
        """
        REDIS_LOGGER.info("zrangebyscore %s %s %s %s", key, start, stop, withscores)
        return get_connection().zrangebyscore(key, start, stop, withscores=withscores)

    @redis_excepts
    def zrevrangebyscore(self, key, start, stop, withscores=False):
        """pass
        """
        REDIS_LOGGER.info("zrevrangebyscore: %s %s %s", key, start, stop)
        return get_connection().zrevrangebyscore(key, start, stop, withscores=withscores)

    @redis_excepts
    def zscore(self, key, member):
        """return the ordered collection.
        """
        REDIS_LOGGER.info("zscore: %s %s", key, member)
        return get_connection().zscore(key, member)

    @redis_excepts
    def zincrby(self, key, member, increment):
        """Increment the score of a member in a sorted set
        """
        REDIS_LOGGER.info("zincrby: %s %s %f", key, member, increment)
        return get_connection().zincrby(key, member, increment)

    # @redis_excepts
    # def zinterstore(self, dest_zsets, sets_num, *args, aggregation='max'):
    #     """find those entries that are in all of the SETs and ZSETs, combining their scores
    #     """
    #     REDIS_LOGGER.info("zinterstore: dest_zets:%s" % (dest_zsets))
        # return get_connection().zinterstore(dest, keys)

    @redis_excepts
    def zrank(self, key, member):
        """return the position of the given member in the ZSET.
            return None if not exists
        """
        REDIS_LOGGER.info("zrank: %s %s", key, member)
        return get_connection().zrank(key, member)

#########################################
#   ELSE in Redis
#########################################
    @redis_excepts
    def sort(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

    @redis_excepts
    def _exec(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

    @redis_excepts
    def pipline(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

    @redis_excepts
    def ttl(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

    @redis_excepts
    def pttl(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

    @redis_excepts
    def persist(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

    @redis_excepts
    def expire(self, key, ttl):
        """indicate expire for a certain key
        """
        REDIS_LOGGER.info("expire %s %s", key, ttl)
        return get_connection().expire(key, ttl)

    @redis_excepts
    def expireat(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

    @redis_excepts
    def pexpire(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

    @redis_excepts
    def pexpireat(self, key, alpha=False):
        """Sort list, set by number, even use alphabet
        """
        REDIS_LOGGER.info("sort: %s %s", key, alpha)
        return get_connection().sort(key, alpha)

#########################################
# Test start
#########################################


def test():
    """Just test
    """
    r = Redispool()
    key = 'test'
    value = "value"
# test key-value   ################################

    def test_key_value():
        print("Test starts. key:%s ........." % key)
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
        print("All key-value functions pass the test......\n")
    # test_key_value()

#  test List ######################################

    def test_list():
        r.delete(key)
        r.push(value, key)
        assert(r.lrange(key, 0, 0)[0].decode('utf8') == value)
        assert(r.lindex(key, 0).decode('utf8') == value)
        assert(r.pop(key).decode('utf8') == value)
        r2 = Redispool(queue=key)
        r2.push(value, key)
        assert(r2.pop(key).decode('utf8') == value)
        print("All list functions pass the test......\n")
    test_list()

#  test Set ######################################

    def test_set():
        r.delete(key)
        r.sadd(key, value)
        assert(value.encode('utf8') in r.smembers(key))
        assert(r.sismembers(key, value) is True)
        r.srem(key, value)
        assert(value.encode('utf8') not in r.smembers(key))
        assert(r.sismembers(key, value) is False)
        print("All set functions pass the test......\n")
    test_set()

#  test Hash ######################################

    def test_hash():
        r.delete(key)
        r.hset(key, "q", "q")
        r.hset(key, "w", "w")
        r.hset(key, "e", 1)
        assert(r.hget(key, "q") == "q".encode('utf8'))
        assert(r.hget(key, "w") == "w".encode('utf8'))
        assert(r.hget(key, "e") == "1".encode('utf8'))
        r.hincrby(key, "e", 3)
        assert(r.hget(key, "e") == "4".encode('utf8'))
        print(r.hgetall(key))
        r.hdel(key, "e")
        print(r.hgetall(key))
        r.delete(key)
        assert(r.exists(key) is False)
        r.hmset(key, {"a": "a", "b": "b", "c": 1})
        print(r.hgetall(key))
        # assert(r.exists(key) is False)
        print("All hash functions pass the test......\n")
    test_hash()

#  test Zset ######################################
    def test_zset():
        r.delete(key)
        r.zadd(key, 100.0, value)
        r.zadd(key, 200.0, value + "2")
        r.zadd(key, 300.0, value + "3")
        r.zadd(key, 150.0, value + "4")
        # ==============================================
        assert("value4".encode('utf8') in r.zrange(key, 0, -1))
        r.zrem(key, value + "4")
        assert("value4".encode('utf8') not in r.zrange(key, 0, -1))
        print(r.zrange(key, 0, -1))
        print(r.zrange(key, 0, -1, withscores=True))
        print(r.zrevrange(key, 0, -1))
        print(r.zrevrange(key, 0, -1, withscores=True))
        assert(r.zscore(key, "value3") == 300.0)
        r.zincrby(key, "value3", 100.5)
        assert(r.zscore(key, "value3") == 400.5)
        print(r.zrangebyscore(key, 0, 200))
        print(r.zrangebyscore(key, 0, 200, withscores=True))
        print(r.zrevrangebyscore(key, 1000, 100))
        print(r.zrevrangebyscore(key, 1000, 100, withscores=True))
        print("All zset functions pass the test..........\n")
    test_zset()
    print("*******Congratulations!!! All the test have been passed ~ ")

# test()
