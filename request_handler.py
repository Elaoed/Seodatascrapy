# encoding=utf-8
"""accept request from users and make simple format check"""
import copy
import json
from functools import wraps

import requests
from flask import Flask, request

from kits.log import get_logger
from config.conf import TOKENS
from kits.utils import if_url
from kits.constants import RETOBJ
from kits.constants import QUEUE_NAME
from kits.redispool import Redispool
from kits.my_exception import MyException

__REDIS = Redispool()
__LOGGER = get_logger('acceptRequest')
config = {
    'redis': __REDIS,
    'logger': __LOGGER
}

app = Flask(__name__)


def try_except(orig_func):
    @wraps(orig_func)
    def wrapper():
        try:
            master_token = request.values.get('master_token', [])
            err_msg = ""
            err_code = 10009

            if not master_token:
                err_msg = "Token doesn't exist"
            elif request.remote_addr not in TOKENS.keys():
                err_msg = "your Ip is not allow to acess this interface"
            elif TOKENS[request.remote_addr] not in master_token:
                err_msg = "the token of corresponding ip is wrong"
            if err_msg:
                raise MyException(err_msg, err_code)

            return orig_func()

        except requests.exceptions.ConnectionError as why:
            config['logger'].error(why.message)
            retobj = copy.deepcopy(RETOBJ)
            retobj["status"]["msg"] = "Connection Error"
            retobj["status"]["code"] = 10004
            return json.dumps(retobj)
        except MyException as why:
            config['logger'].info(why.msg)
            retobj = copy.deepcopy(RETOBJ)
            retobj["status"]["msg"] = why.msg
            retobj["status"]["code"] = why.code
            return json.dumps(retobj)
        except Exception:
            config['logger'].info("Exception", exc_info=True)
            retobj = copy.deepcopy(RETOBJ)
            retobj["status"]["code"] = 10001
            retobj["status"]["msg"] = "Unknown Error...Please inform the Administrator"
            return json.dumps(retobj)

    return wrapper


def url_format(origin_func):
    @wraps(origin_func)
    def wrapper():
        domain = request.values.get('domain')
        if not domain:
            raise MyException(origin_func.__name__ + " - domain doesn't exist", 10002)
        if not if_url(domain):
            raise MyException('url format not correct', 10003)

        redis_key = '%s:::%s' % (origin_func.__name__, domain)
        return origin_func(redis_key)

    return wrapper


def query_redis(redis_key):
    result = config['redis'].get(redis_key)
    if not result:
        retobj = json.dumps(copy.deepcopy(RETOBJ))
        config['redis'].set(redis_key, retobj)
        config['redis'].expire(redis_key, 60)
        config['redis'].push(QUEUE_NAME, redis_key)
    elif json.loads(result)['status']['code'] in [10005, 10008, 10010, 10011, 10012]:
        config['redis'].push(QUEUE_NAME, redis_key)
        retobj = result
    else:
        retobj = result
    return retobj

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
        raise MyException("keyword_rank - param not right", 10002)

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
        raise MyException("top_ten - param not right", 10002)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3035)
