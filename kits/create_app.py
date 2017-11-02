# -*- coding: utf-8 -*-

import copy
import json
from functools import wraps

from flask import Flask
from flask import request

from config.conf import conf
from config.conf import TOKENS
from kits.utils import if_url
from kits.constants import RETOBJ
from kits.constants import QUEUE_NAME
from kits.my_exception import MyException

app = Flask("__main__")

def try_except(orig_func):

    @wraps(orig_func)
    def wrapper():
        try:
            master_token = request.form.get('master_token', type=str, default="")
            err_msg = ""

            if not master_token:
                err_msg = "Token doesn't exist"
            elif request.remote_addr not in TOKENS.keys():
                err_msg = "Your ip is not allow to acess"
            elif TOKENS[request.remote_addr] not in master_token:
                err_msg = "Token Wrong"
            if err_msg:
                raise MyException(err_msg, 10009)

            return orig_func()

        except MyException as why:
            conf['logger'].info(why.msg)
            retobj = copy.deepcopy(RETOBJ)
            retobj["status"]["msg"] = why.msg
            retobj["status"]["code"] = why.code
            return json.dumps(retobj)
        except Exception:
            conf['logger'].info("Exception", exc_info=True)
            retobj = copy.deepcopy(RETOBJ)
            retobj["status"]["code"] = 10001
            retobj["status"]["msg"] = "Unknown Error...Please inform the Administrator"
            return json.dumps(retobj)

    return wrapper


def url_format(origin_func):

    @wraps(origin_func)
    def wrapper():
        domain = request.form.get('domain', type=str, default=None)

        if not domain:
            raise MyException(origin_func.__name__ + " - domain doesn't exist", 10002)
        if not if_url(domain):
            raise MyException('url format not correct', 10003)

        redis_key = '%s:::%s' % (origin_func.__name__, domain)
        return origin_func(redis_key)

    return wrapper


def query_redis(redis_key):
    result = conf['redis'].get(redis_key)
    if not result:
        retobj = json.dumps(copy.deepcopy(RETOBJ))
        conf['redis'].set(redis_key, retobj)
        conf['redis'].expire(redis_key, 60)
        conf['redis'].push(QUEUE_NAME, redis_key)
    elif json.loads(result)['status']['code'] in [10005, 10008, 10010, 10011, 10012]:
        conf['redis'].push(QUEUE_NAME, redis_key)
        retobj = result
    else:
        retobj = result
    return retobj

# @app.route('/getKeywordRank', methods=['POST'])
# @try_except
# def keyword_rank():
#     url = request.values.get('domain', type=str, default=None)
#     keyword = request.values.get('keyword', type=str, default=None)
#     search_engine = request.values.get('search_engine', type=str, default=None)

#     if url and keyword and search_engine:

#         if search_engine not in ['baidu', 'sogou', '360']:
#             raise MyException("Param not valied - Search_egine not right", 10003)

#         if not if_url(url):
#             raise MyException('Param not valied - Url format not correct', 10003)

#         redis_key = '%s:::keyword_rank:::%s:::%s' % (url, search_engine, keyword)
#         return query_redis(redis_key)

#     else:
#         raise MyException("Keyword_rank - Lack of param", 10002)

@app.route('/getDeadLink', methods=['POST'])
@try_except
@url_format
def dead_link(redis_key):
    return query_redis(redis_key)

@app.route('/getFriendLink', methods=['POST'])
@try_except
@url_format
def friend_link(redis_key):
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

# @app.route('/getTopten', methods=['POST'])
# @try_except
# def get_top_ten():
#     keyword = request.values.get('keyword')
#     search_engine = request.values.get('search_engine')
#     if keyword and search_engine:
#         if search_engine not in ['baidu', 'sogou', '360']:
#             raise MyException("Search_egine not right", 10006)
#         redis_key = "top_ten:::%s:::%s" % (search_engine, keyword)
#         return query_redis(redis_key)
#     else:
#         raise MyException("top_ten - param not right", 10002)

# @app.route('/', methods=['GET'])
# def index():
#     return render_template('index.html')
