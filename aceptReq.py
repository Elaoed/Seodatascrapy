# encoding=utf-8
'''accept request from users and make simple format check'''
import re
import time
import json
from os import path
from functools import wraps
import redis
import requests
from flask import Flask, request
from kits.config import ROOT_PATH
from kits.dealDomain import dealDomain
from kits.log import get_logger
from kits.MyException import MyException

with open(path.join(ROOT_PATH, 'config/db.conf'), 'r') as f:
    redis_conf = json.load(f)
r = redis.Redis(
    port=redis_conf['redis']['port'], password=redis_conf['redis']['password'])
TOKEN_IP = redis_conf['token']
LOGGER = get_logger('acceptRequest')
QUEUE_NAME = "request_queue"
app = Flask(__name__)


def try_except(orig_func):
    @wraps(orig_func)
    def wrapper():
        try:
            if not request.remote_addr:
                raise MyException("Client IP doesn't exist", 10021)
            master_token = request.values.get('master_token')
            if not master_token:
                raise MyException("Token doesn't exist", 10010)
            # if request.remote_addr not in TOKEN_IP.values():
            #     raise MyException(
            #         '你的ip不允许访问此接口', 10010)
            # if TOKEN_IP[request.remote_addr] not in master_token:
            #     raise MyException(
            #         '你的ip对应的token错误', 10010)
            return orig_func()
        except requests.exceptions.SSLError as e:
            LOGGER.info('%s' % e)
            retobj = {"status": {"msg": 'HTTPS ERROR--for example:https://baidu.com without www', "code": 10004, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
            return json.dumps(retobj)
        except requests.exceptions.ConnectionError as e:
            LOGGER.error(e)
            retobj = {"status": {"msg": 'Connection error', "code": 10004, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
            return json.dumps(retobj)
        except MyException as e:
            LOGGER.info('%s' % e.msg)
            retobj = {"status": {"msg": '%s' % e.msg, "code": e.code, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
            return json.dumps(retobj)
        except Exception as e:
            LOGGER.info('%s' % e)
            retobj = {"status": {"msg": 'Unknown Error...Please inform the Administrator', "code": 10001, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
            return json.dumps(retobj)

    return wrapper


def query_redis(redis_key):
    result = r.get(redis_key)
    retobj = None
    if not result:
        retobj = json.dumps({"status": {"msg": 'Querying.... Please wait', "code": 10000, "time": time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []})
        r.set(redis_key, retobj)
        r.expire(redis_key, 60)
        r.lpush(QUEUE_NAME, redis_key)
    elif json.loads(result)['status']['code'] in [10008, 10011, 10009, 10005]:
        r.lpush(QUEUE_NAME, redis_key)
        retobj = result
    else:
        retobj = result
    return retobj


def if_url(url):
    if re.match('http[s]?://(\w+\.){1,}\w+', url) or re.match('(\w+\.){1,}\w+', url):
        return True
    return False


@app.route('/getKeywordRank', methods=['POST'])
@try_except
def index():
    url = request.values.get('domain')
    keyword = request.values.get('keyword')
    search_engine = request.values.get('search_engine')

    if url and keyword and search_engine:

        if search_engine not in ['baidu', 'sogou', '360']:
            raise MyException("Search_egine not right", 10006)

        res = re.match('(http[s]?\:\/\/(\w+\.){1,}\w+)', url)
        if res:
            url = res.group(1)
        elif re.match('((\w+\.){1,}\w+)', url):
            url = re.match('((\w+\.){1,}\w+)', url).group(1)
        else:
            raise MyException('Url format not correct', 10003)

        redis_key = 'getKeywordRank-%s-%s-%s' % (
            url, keyword, search_engine)
        return query_redis(redis_key)

    else:
        raise MyException("getKeywordRank--param not right", 10002)


@app.route('/getDeadLink', methods=['POST'])
@try_except
def index2():
    domain = request.values.get('domain')
    if not domain:
        raise MyException("getDeadLink--domain doesn't exist", 10002)
    if not if_url(domain):
        raise MyException('url format not correct', 10003)
    redis_key = 'getDeadLink-%s' % domain
    return query_redis(redis_key)


@app.route('/getWebInfo', methods=['POST'])
@try_except
def index3():

    domain = request.values.get('domain')
    if not domain:
        raise MyException("getWebInfo---domain doesn't exist", 10002)
    if not if_url(domain):
        raise MyException('url format not correct', 10003)

    redis_key = 'getWebInfo-%s' % domain
    return query_redis(redis_key)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5003)
