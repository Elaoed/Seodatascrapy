# encoding=utf-8
import re
import httplib
import socket
import requests
import jieba
import socket
from lxml import etree
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


def dealDomain(url):
    if url == "www.163.com":
        url = "http://www.163.com"
    if not re.search('^http|^https', url if url else ""):
        try:
            conn = httplib.HTTPConnection(url, 80, timeout=4)
            conn.request('GET', '/')
            res = conn.getresponse()
            if res.status == 301 or res.status == 302:
                url = {
                    'url': res.msg['Location'], 'code': 0, 'msg': 'url moved to %s' % res.msg['Location']}
            elif res.status == 200:
                url = {'url': 'http://%s' %
                       url, 'code': 0, 'msg': '返回值是200'}
            else:
                url = {'url': url, 'msg': "url%s return code:%d" %
                       (url, res.status), 'code': 10008}
        except socket.gaierror as e:
            url = {'url': url, 'code': 10005, 'msg': 'cant parse %s' % url}
        except requests.ReadTimeout as e:
            url = {'url': url, 'code': 10005, 'msg': e}
        except socket.timeout as e:
            url = {'url': url, 'code': 10005, 'msg': e}
    else:          # except requests.exceptions.SSLError as e:
        try:
            res = requests.get(url, timeout=5)
            if res and res.status_code == 200:
                url = {
                    'url': url, 'code': 0, 'msg': 'url是完整的'}
            else:
                url = {'url': url, 'msg': "url%s return code:%d" %
                       (url, res.status_code), 'code': 10008}
        except requests.exceptions.SSLError as e:
            url = {'url': url, 'code': 10004, 'msg': '%s' % e}

    return url


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

    if not encoding in ['utf-8', 'UTF-8', 'utf8', 'UTF8']:
        if 'gb' in encoding or 'GB' in encoding:
            content = content.decode('gbk')
        else:
            content = content.decode(encoding)
    return content
