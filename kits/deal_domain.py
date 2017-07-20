# encoding=utf-8
import re
import requests
from requests.exceptions import RequestException
import jieba
from lxml import etree
import chardet

from kits.constants import HEADERS
from kits.log import ROOT_PATH

with open(ROOT_PATH + '/config/filter_list', 'r') as f:
    EXCLUDE_LIST = [x[:-1] for x in f.readlines()]


def vice_get_response(domain):

    url = domain if 'http' in domain else 'http://' + domain

    try:
        res = requests.get(url, headers=HEADERS, timeout=3)
        if 200 <= res.status_code < 400:
            return res

    except RequestException:
        return None

    return None

def get_response(domain):

    response = vice_get_response(domain)
    if response:
        refresh_str = "<meta http-equiv=\"Refresh\" content=\"0; url=(.*?)\"/>"
        refresh = re.match(refresh_str, response.text)
        if refresh:
            new_url = refresh.group(1)
            response = vice_get_response(new_url)
    return response

def divide_article(content):
    content = re.sub(
        r'<!--(.*?)-->|x-src="(.*?)"|x-src=\'(.*?)\'', '', content)
    content = re.sub(r'\w+-?\w+="(.*?)"|\w+-?\w+=\'(.*?)\'', '', content)
    d = jieba.cut(content, cut_all=True)
    li = [i.encode() for i in d]
    count = {}
    exclude_li = [' ', '\r', '\t', "'", '"', '\n', '\n\n', '\n\n\n'] + \
                 ['%dpx' % i for i in range(100)] + \
                 ['%d' % i for i in range(100)] + EXCLUDE_LIST

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
