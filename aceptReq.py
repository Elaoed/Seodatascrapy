# encoding=utf-8
from flask import Flask, request
import redis
from kits.log import get_logger
from functools import wraps
import re
import time
import json
from kits.dealDomain import dealDomain
import requests


r = redis.Redis()

app = Flask(__name__)
LOGGER = get_logger('acceptRequest')
from kits.MyException import MyException
QUEUE_NAME = "request_queue"


def try_except(orig_func):
    @wraps(orig_func)
    def wrapper():
        try:

            TOKEN_IP = {'ip_address': 'NuFOOb2OokoO2YrI6DkNHqWjBXUhvZdV'}
            if not request.remote_addr:
                raise MyException('客户端IP不存在', 10010)
            master_token = request.args.get('master_token')
            master_token = 'NuFOOb2OokoO2YrI6DkNHqWjBXUhvZdV'
            if not master_token:
                raise MyException("token不存在", 10010)
            # if request.remote_addr not in TOKEN_IP.values():
            #     raise MyException(
            #         '你的ip不允许访问此接口', 10010)
            # if TOKEN_IP[request.remote_addr] not in master_token:
            #     raise MyException(
            #         '你的ip对应的token错误', 10010)
            return orig_func()
        except requests.exceptions.ConnectionError as e:
            LOGGER.error(e)
            retobj = {"status": {"msg": '网页链接错误'.format(
                e), "code": 10004, "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
            return json.dumps(retobj)
        except requests.exceptions.SSLError as e:
            LOGGER.info('%s' % e)
            retobj = {"status": {"msg": 'URL错误', "code": 10004, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
            return json.dumps(retobj)

        except MyException as e:
            LOGGER.info('%s' % e.msg)
            retobj = {"status": {"msg": '%s' % e.msg, "code": e.code, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
            return json.dumps(retobj)
        except Exception as e:
            LOGGER.info('%s' % e)
            retobj = {"status": {"msg": '未知错误', "code": 10001, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
            return json.dumps(retobj)

    return wrapper


def query_redis(redis_key):
    result = r.get(redis_key)
    retobj = None
    if not result:
        retobj = json.dumps({"status": {"msg": '正在查询中', "code": 10000, "time": time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []})
        r.set(redis_key, retobj)
        r.lpush(QUEUE_NAME, redis_key)

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
    url = request.form['domain']
    keyword = request.form['keyword']
    search_engine = request.form['search_engine']

    if url and keyword and search_engine:

        if search_engine not in ['baidu', 'sogou', '360']:
            raise MyException("搜索引擎不存在", 10006)

        res = re.match('(http[s]?\:\/\/(\w+\.){1,}\w+)', url)
        if res:
            url = res.group(1)
        elif re.match('((\w+\.){1,}\w+)', url):
            url = re.match('((\w+\.){1,}\w+)', url).group(1)
        else:
            raise MyException('url格式不正确', 10003)

        redis_key = 'getKeywordRank-%s-%s-%s' % (
            url, keyword, search_engine)
        return query_redis(redis_key)

    else:
        raise MyException("获取关键字--参数不正确", 10002)


@app.route('/getDeadLink', methods=['POST'])
@try_except
def index2():
    domain = request.form['domain']
    if not domain:
        raise MyException("获取友情链接--参数不正确", 10002)
    if not if_url(domain):
        raise MyException('url格式不正确', 10003)
    redis_key = 'getDeadLink-%s' % domain
    return query_redis(redis_key)


@app.route('/getWebInfo', methods=['POST'])
@try_except
def index3():

    domain = request.form['domain']
    if not domain:
        raise MyException("获取网页信息--参数不正确", 10002)
    if not if_url(domain):
        raise MyException('url格式不正确', 10003)

    redis_key = 'getWebInfo-%s' % domain
    return query_redis(redis_key)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5003, debug=True)
