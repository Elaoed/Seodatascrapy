# encoding=utf-8
import re
import os
import requests
import jieba
from lxml import etree
import sys
import chardet
from utils import HEADERS

reload(sys)
sys.setdefaultencoding('utf-8')
ROOT_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
with open(ROOT_PATH + '/filter_list', 'r') as f:
    e_list = f.readlnes()
EXCLUDE_LIST = [x[:-1] for x in e_list]


def dealDomain(domain):

    ret_obj = {'url': domain, 'code': 10004,
               'msg': "can't parse url:" + domain}

    if 'https' in domain or 'http' in domain:
        url = domain
    else:
        url = 'http://' + domain
    try:
        res = requests.head(url, headers=HEADERS)
        if res.status_code is 200:
            url = res.url
        elif res.status_code is 405:
            res = requests.get(url, headers=HEADERS)
            if res.status_code is 200:
                url = res.url
            else:
                url = ""
        else:
            url = ""
    except Exception:
        url = ""

    # if not re.search('^http|^https', domain if domain else ""):
    #     try:
    #         conn = httplib.HTTPConnection(domain, 80, timeout=4)
    #         conn.request('GET', '/', headers=HEADERS)
    #         res = conn.getresponse()
    #         if res.status == 301 or res.status == 302:
    #             ret_obj['url'] = res.msg['Location']
    #             ret_obj['code'] = 0
    #             ret_obj['msg'] = 'website change url to ' + res.msg['Location']
    #         elif res.status == 200:
    #             ret_obj['url'] = 'http://' + domain
    #             ret_obj['code'] = 0
    #             ret_obj['msg'] = 'return code = 200'
    #     except socket.gaierror as e:
    #         pass  # default
    #     except requests.ReadTimeout as e:
    #         ret_obj['code'] = 10005
    #         ret_obj['msg'] = e
    #     except socket.timeout as e:
    #         ret_obj['code'] = 10005
    #         ret_obj['msg'] = e
    #     except socket.error as e:
    #         pass  # default
    # else:
    #     url = domain
    #     try:
    #         res = requests.get(url, timeout=5)
    #         if res and res.status_code == 200:
    #             ret_obj['code'] = 0
    #             ret_obj['msg'] = "url is full format"
    #         else:
    #             ret_obj['code'] = 10004
    #             ret_obj['msg'] = "url:" + url + ", return code:" + res.status_code
    #     except requests.exceptions.SSLError as e:
    #         ret_obj['code'] = 10003
    #         ret_obj['msg'] = e

    return ret_obj


def divide_article(content):
    content = re.sub(
        r'<!--(.*?)-->|x-src="(.*?)"|x-src=\'(.*?)\'', '', content)
    content = re.sub(r'\w+-?\w+="(.*?)"|\w+-?\w+=\'(.*?)\'', '', content)
    d = jieba.cut(content, cut_all=True)
    li = [i.encode() for i in d]
    count = {}
    exclude_li = [' ', '\r', '\t', "'", '"', '\n', '\n\n', '\n\n\n'] + \
                 ['%dpx' % i for i in xrange(100)] + \
                 ['%d' % i for i in xrange(100)] + EXCLUDE_LIST

    for i in li:
        if i and len(i) > 1 and i not in exclude_li:
            try:
                int(i)
                continue
            except ValueError:
                pass
            if re.search('#|\n', i):
                continue
            if re.search('^[^\u4e00-\u9fa5]', i.decode()):
                if not re.search('^[^\u4e00-\u9fa5]{2,}', i.decode()):
                    continue
            if i not in count:
                count[i] = 1
            else:
                count[i] += 1
    return sorted(count.items(), key=lambda count: count[1], reverse=True)[:10]


def deal_encoding(content, encoding):

    selector = etree.HTML(content)
    metas = selector.xpath('//meta/@content')

    encoding_new = None
    for i in metas:
        if 'charset' in i:
            encoding_new = re.search('charset=(.*)', i).group(1)
    h5metas = selector.xpath('//meta/@charset')
    for i in h5metas:
        if i:
            encoding_new = i

    if not encoding_new and not encoding:
        encoding = 'utf8'
    elif not encoding_new:
        encoding = encoding
    else:
        encoding = encoding_new
    if encoding not in ['utf-8', 'UTF-8', 'utf8', 'UTF8']:
        if 'gb' in encoding or 'GB' in encoding:
            content = content.decode('gbk')
        else:
            content = content.decode(encoding)
    return content
