# encoding=utf-8
import re
import requests
import jieba
from lxml import etree
import chardet

from kits.constants import HEADERS
from kits.constants import COOKIES
from kits.log import ROOT_PATH

with open(ROOT_PATH + '/config/filter_list', 'r') as f:
    EXCLUDE_LIST = [x[:-1] for x in f.readlines()]


def vice_get_response(domain):

    url = domain if 'http' in domain else 'http://' + domain

    try:
        res = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=3)
        if 200 <= res.status_code < 400:
            return res

    except requests.exceptions.RequestException:
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

    li = jieba.cut(content, cut_all=True)
    count = {}
    exclude_li = EXCLUDE_LIST + ['%d' % i for i in range(100)] + \
                 ['%dpx' % i for i in range(100)] + \
                 [' ', '\r', '\t', "'", '"', '\n', '\n\n', '\n\n\n']

    for piece in li:
        if len(piece) > 1 and piece not in exclude_li:
            try:
                int(piece)
                continue
            except ValueError:
                pass
            if re.search('#|\n', piece):
                continue
            if re.search('^[^\u4e00-\u9fa5]', piece):
                if not re.search('^[^\u4e00-\u9fa5]{2,}', piece):
                    continue
            if piece not in count:
                count[piece] = 1
            else:
                count[piece] += 1
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
