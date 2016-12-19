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
            master_token = request.values.get('master_token')
            if not master_token:
                raise MyException("Token doesn't exist", 10009)

            if request.remote_addr not in TOKEN_IP.keys():
                raise MyException(
                    'your Ip is not allow to acess this interface', 10009)
            if TOKEN_IP[request.remote_addr] not in master_token:
                raise MyException(
                    'the token of corresponding ip is wrong', 10009)
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


def url_format(origin_func):
    @wraps(origin_func)
    def wrapper():
        domain = request.values.get('domain')
        if not domain:
            raise MyException(
                "%s---domain doesn't exist" % origin_func.__name__, 10002)
        if not if_url(domain):
            raise MyException('url format not correct', 10003)

        redis_key = '%s:::%s' % (origin_func.__name__, domain)
        return origin_func(redis_key)

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
    elif json.loads(result)['status']['code'] in [10005, 10008, 10010, 10011, 10012, 10020]:
        r.lpush(QUEUE_NAME, redis_key)
        retobj = result
    else:
        retobj = result
    return retobj


def if_url(url):
    if re.match('^(http[s]?\:\/\/)?(\w+\.){1,7}\w+$', url):
        return True
    return False


@app.route('/getKeywordRank', methods=['POST'])
@try_except
def keyword_rank():
    url = request.values.get('domain')
    keyword = request.values.get('keyword')
    search_engine = request.values.get('search_engine')

    if url and keyword and search_engine:

        if search_engine not in ['baidu', 'sogou', '360']:
            raise MyException("Search_egine not right", 10006)

        if not if_url(url):
            raise MyException('url format not correct', 10003)

        redis_key = '%s:::keyword_rank:::%s:::%s' % (
            url, search_engine, keyword)
        return query_redis(redis_key)

    else:
        raise MyException("keyword_rank--param not right", 10002)


@app.route('/getDeadLink', methods=['POST'])
@try_except
@url_format
def dead_link(redis_key):
    return query_redis(redis_key)


@app.route('/getWebInfo', methods=['POST'])
@try_except
@url_format
def web_info(redis_key):
    return query_redis(redis_key)


@app.route('/getAlexa', methods=['POST'])
@try_except
@url_format
def get_alexa(redis_key):
    return query_redis(redis_key)


@app.route('/getInclude', methods=['POST'])
@try_except
@url_format
def get_include(redis_key):
    return query_redis(redis_key)


@app.route('/getServerInfo', methods=['POST'])
@try_except
@url_format
def server_info(redis_key):
    return query_redis(redis_key)


@app.route('/getWeight', methods=['POST'])
@try_except
@url_format
def get_weight(redis_key):
    return query_redis(redis_key)


@app.route('/getTopten', methods=['POST'])
@try_except
def get_top_ten():
    keyword = request.values.get('keyword')
    search_engine = request.values.get('search_engine')
    if keyword and search_engine:
        if search_engine not in ['baidu', 'sogou', '360']:
            raise MyException("Search_egine not right", 10006)
        redis_key = "top_ten:::%s:::%s" % (search_engine, keyword)
        return query_redis(redis_key)
    else:
        raise MyException("top_ten--param not right", 10002)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3035, debug=True)
