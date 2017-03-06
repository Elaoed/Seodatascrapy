# encoding=utf-8
import re
import httplib
import socket

import requests
import jieba
from lxml import etree
import sys

reload(sys)
sys.setdefaultencoding('utf-8')

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,ja;q=0.2',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1'
}


def dealDomain(domain):
    if domain == "www.163.com":
        domain = "http://www.163.com"

    ret_obj = {'url': domain, 'code': 10004,
               'msg': "can't parse url:{}".format(domain)}
    if not re.search('^http|^https', domain if domain else ""):
        try:
            conn = httplib.HTTPConnection(domain, 80, timeout=4)
            conn.request('GET', '/', headers=headers)
            res = conn.getresponse()
            if res.status == 301 or res.status == 302:
                ret_obj['url'] = res.msg['Location']
                ret_obj['code'] = 0
                ret_obj['msg'] = 'website change url to{}'.format(
                    res.msg['Location'])
            elif res.status == 200:
                ret_obj['url'] = 'http://{}'.format(domain)
                ret_obj['code'] = 0
                ret_obj['msg'] = 'return code = 200'
        except socket.gaierror as e:
            pass  # default
        except requests.ReadTimeout as e:
            ret_obj['code'] = 10005
            ret_obj['msg'] = e
        except socket.timeout as e:
            ret_obj['code'] = 10005
            ret_obj['msg'] = e
        except socket.error as e:
            pass  # default
    else:
        url = domain
        try:
            res = requests.get(url, timeout=5)
            if res and res.status_code == 200:
                ret_obj['code'] = 0
                ret_obj['msg'] = "url is full format"
            else:
                ret_obj['code'] = 10004
                ret_obj['msg'] = 'url:{}, return code:{}'.format(
                    url. res.status_code)
        except requests.exceptions.SSLError as e:
            ret_obj['code'] = 10003
            ret_obj['msg'] = e

    return ret_obj

# '^\d+(px)?$|^\w$|^h\d$|^src\d$|^\d+$'
def divArticle(content):
    content = re.sub(
        r'<!--(.*?)-->|x-src="(.*?)"|x-src=\'(.*?)\'', '', content)
    content = re.sub(r'\w+-?\w+="(.*?)"|\w+-?\w+=\'(.*?)\'', '', content)
    d = jieba.cut(content, cut_all=True)
    li = [i.encode() for i in d]
    count = {}
    exclude_li = [' ', '\r',  '\n', '<', '>', '!', 'div', 'li', 'ul', 'span', 'target',
                  'href', 'class', 'script', '\t', '=', '.', 'col', ':', '-', '#', '_',
                  'h1', '/', "'", '"', 'lg', 'h2', 'fa', 'i', 'row', 'center', 'md',
                  'icon', 'sm', 'text', 'page', 'blank', 'style', ';', 'alt', '|', 'h5',
                  'is', 'com', 'src', 'css', 'br', 'footer', 'btn', 'img', '，', ',', '；',
                  'or', '？', 'and', 'And', '[', ']', '、', '。', 'section', 'no', 'nbsp',
                  'hidden', '\n\n', 'id', '\n\n\n', '\xe7\x9a\x84', 'meta', 'data',
                  '\xe6\x88\x91\xe4\xbb\xac', '\xe6\x98\xaf', '\xe6\x9b\xb4', 'button',
                  'role', 'rel', 'link', 'strong', 'stylesheet', 'slide', '\xe5\x85\xb3\xe4\xba\x8e',
                  '\xe4\xb8\xba', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n',
                  'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'current', 'typeof', 'td', 'url3',
                  'y', 'z', 'var', 'function', 'this', 'return', 'name', 'nav', 'margin', 'top', 'tab',
                  'left', 'position', 'width', 'em', 'if', 'height', 'http', 'background', 'rgb', 'list', 'con', 'color',
                  'padding', 'url2', 'window', 'length', 'image', 'linear', 'float', '+', 'right', 'null', 'display',
                  'auto', 'str', 'js', 'hover', 'else', 'solid', 'font', 'document', 'border', 'gradient', 'overflow',
                  'bottom', 'none', 'entry', 'line', 'prototype', 'index', 'content', 'addEvent', 'px', 'new', 'value',
                  'for', 'special', 'bobo', 'xf', 'bd', 'ad', 'util', 'size', 'app', 'level', 'box', 'house',
                  'layout', 'webkit', 'ctrl', 'hd', 'slider', 'main', 'html', 'repeat', 'innerHTML', 'inline',
                  'cacje', 'absolute', 'align', 'moz', 'elements', 'arguments', 'search', 'title',
                  'www', 'trigger', 'subtab', 'item', 'url1', 'png', 'config', '00774ISL', 'select', 'img1',
                  'event', 'extend', '#js', 'cache', 'src2', 'src3', 'sub', 'net', 'site',
                  'render', 'call', 'indexOf', 'body', 'stc2, animation', 'true', 'Math', 'inc', 'attr', 'undefined',
                  'replace', 'elm', 'EVENT', 'false', 'sn', 'obj', 'src1', 'relative', 'area', 'apply', 'get', 'mail', 'type'
                  'arr', 'context', 'namespace', 'setTimeout', 'recommend', 'from', 'refresh', 'each',
                  'stock', 'core', 'constructor', 'imglist', 'DS', 'login', 'arr', 'animation', 'cursor', 'all', 'transform',
                  'start', 'pointer', 'parentNode', 'visited', 'click', 'in', 'type', 'appendChild', 'el', 'images', 'i++',
                  'push', 'layout', 'block', 'iframe', 'textarea', 'url', 'mouseover', 'fold', 'bind', 'to', 'addCss', 'shop',
                  'transparent', 'base', 'len', 'num', 'decoration', '163ws1', 'NTESCommonNavigator', 'R', 'S', 'T', 'U',
                  'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'V', 'W', 'X', 'Y', 'Z',
                  'NTES', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'time', 'int', 'now', 'distance', 'client', 'minute', 'hour', 'second'
                  'Date', 'floor', 'getTime', 'end', 'day', 'second', 'DOCTYPE', 'head', 'max', '\xe6\x97\xb6\xe9\x97\xb4',
                  '\xe5\x89\xa9\xe4\xbd\x99', 'ext', 'qm', 'gtimg', 'mat1', 'info', 'htm', 'qhome', 'txtArea', 'hide',
                  'self', 'gxh', 'ninja', 'city', 'random', 'bold', 'contentRight', 'that', 'title+', 'AutoSiteSearch', 'indent',
                  'hot', 'getElementById', 'mininavInner', 'items', 'tubd', 'yw', 'ft', 'loginGray', 'tubdYwArr', '\xe5\x9b\xbe\xe6\xa0\x87',
                  '\xe5\xb7\x9e\xe5\xb8\x82', '\xe6\x9c\x80\xe5\xa4\xa7', 'Date', '\xe6\x9b\xb4\xe5\xa4\x9a', 'test',
                  'mh', '\xe6\x9f\xa5\xe7\x9c\x8b', 'addClass', '\xe5\x89\xa9\xe4\xbd\x99\xe6\x97\xb6\xe9\x97\xb4', 'cookie', 'sStat',
                  'path'] + ['%dpx' % i for i in range(100)] + ['%d' % i for i in range(100)]

    for i in li:

        if i and len(i) > 1 and i not in exclude_li:
            try:
                int(i)
                continue
            except ValueError as e:
                pass
            if re.search('#|\n', i):
                continue
            if re.search('^[^\u4e00-\u9fa5]', i.decode()):
                if not re.search('^[^\u4e00-\u9fa5]{2,}', i.decode()):
                    continue
            if not count.has_key(i):
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
