# encoding=utf-8
import sys
import socket
reload(sys)
sys.setdefaultencoding('utf-8')
import jieba
import re
from lxml import etree
import requests
import httplib
from bs4 import BeautifulSoup
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import time
import os
from os import path
from kits.config import ROOT_PATH
import gzip
from flask import Flask, request
import json
BufSize = 1024*8
import redis
from functools import wraps
from kits.log import get_logger
from kits.dealDomain import dealDomain, divArticle, deal_encoding
from kits.MyException import MyException
import threading
import Queue
import time
QUEUE_NAME = 'request_queue'

with open(path.join(ROOT_PATH, 'config/db.conf'), 'r') as f:
    redis_conf = json.load(f)
r = redis.Redis(
    port=redis_conf['redis']['port'], password=redis_conf['redis']['password'])

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

cookies = {'ABTEST': '8|1480486710|v17', 'IPLOC': 'CN3301', 'PHPSESSID': 'okc1fr4p9b8m0rq96723nlk527',
           'SNUID': '074E299DEFEAAD9043686FF5EF9A4E23', 'SUID': 'E9A1C7732B0B940A00000000583E6F36',
           'SUIR': '1480486710', 'SUV': '00022B8973C7A1E9583E6F378BBF2990', 'browerV': '3',
           'ld': 'N@n52lllll2Y5uDTlllllVkMN$6llllltDWPfyllll7lllll4klll5@@@@@@@@@@', 'osV': '2',
           'pgv_pvi': '6522359808', 'pgv_si': 's2382888960', 'sct': '6', 'sst0': '509', 'taspeed': 'taspeedexist'}


_LOGGER = get_logger("seoScrapy")

ENGINE = {
    'baidu': {'base_url': 'https://www.baidu.com/s?wd=',
              'rstring': '百度为您找到相关结果约(.*?)个',
              'content_xpath': '//div[contains(@class, "c-container")]',
              'title_xpath': './descendant::h3[contains(@class,"t")]/a[@target="_blank"]',
              'url_xpath': './descendant::h3[contains(@class, "t")]/a[@target="_blank"]/@href',
              'desc_xpath': './descendant::div[@class="c-abstract" or contains(@class, "c-span-last")]'},

    'sogou': {'base_url': 'https://www.sogou.com/web?query=',
              'rstring': '//*[@id="scd_num"]/text()',
              'content_xpath': '//div[@class="results"]/div',
              'title_xpath': './descendant::h3[@class="pt" or @class="vrTitle" or @class="vrt"]/a',
              'url_xpath': './descendant::h3[@class="pt" or @class="vrTitle" or @class="vrt"]/a/@href',
              'desc_xpath': './descendant::p[@class="str_info" or @class="str-text-info"]|div[@class="ft" or @class="str-text-info" or @class="div-p2"]'},

    '360': {'base_url': 'http://www.so.com/s?q=',
            'rstring': '找到相关结果约(.*?)个',
            'content_xpath': '//ul[@id="m-result"]/li',
            'title_xpath': './descendant::h3[contains(@class, "title")]/a[@target="_blank"]',
            'url_xpath': './descendant::h3[contains(@class, "title")]/a[@target="_blank"]/@href',
            'desc_xpath': './descendant::*[contains(@class, "res-desc") or contains(@class, "res-comm-con") or contains(@class, "res-rich")]'}
}


class SEOscrapy(object):

    def __init__(self):
        self.url = ''
        self.pro_type = ''
        self.res = ''
        self.include = None

    def getResponse(self, url):

        _LOGGER.info('In getResponse')

        self.url = url
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            self.content = deal_encoding(res.content, res.encoding)
            self.protocal_type = url.split(':')[0]
            self.pre_size = ''
            self.post_size = ''
            self.gRate = ''
            if 'Content-Type' in res.headers.keys():
                self.content_type = res.headers['Content-Type']
            else:
                self.content_type = res.headers['content-type']

            if 'Content-Encoding' in res.headers.keys():
                self.gzip = 'On' if 'gzip' in res.headers[
                    'Content-Encoding'] else 'Off'
            elif 'content-encoding' in res.headers.keys():
                self.gzip = 'On' if 'gzip' in res.headers[
                    'content-encoding'] else 'Off'
            else:
                self.gzip = 'Off'
            self.res = res
            selector = etree.HTML(self.content)
            desc = selector.xpath('//*[@name="description"]/@content')
            self.desc = desc
            title = selector.xpath('//title/text()')
            self.title = title
            keywords = selector.xpath('//*[@name="keywords"]/@content')
            keywords = "" if not keywords else keywords[0]
            keyword_list = divArticle(self.content)

            for i in divArticle(self.content):
                keywords += " %s " % i[0].encode()
            self.keywords = keywords

        else:
            _LOGGER.warning("%s's status_code is %d" % (url, res.status_code))
            raise MyException("%s site can not be access" % url, 10004)

    def getBaiduWeight(self, url):
        _LOGGER.info('In getBaiduWeight')

        appkey = '618e7a46808573be2401596582de62fb'
        res = requests.post(
            'http://op.juhe.cn/baiduWeight/index', data={'key': appkey, 'domain': url}, timeout=5)
        if res and res.status_code == 200:
            jres = json.loads(res.content)
            if jres['error_code'] == 0:
                self.baiduWeight = jres['result']
            else:
                _LOGGER.error(
                    'res from juhe.cn: reason:%s, error_code:%d' % (jres['reason'], jres['error_code']), 10005)
                self.baiduWeight = {
                    "To": "0",
                    "From": "0",
                    "Weight": "0"
                }

        else:
            _LOGGER.error(
                "On getBaiduWeight---res didnt response or status_code:%s" % res.status_code, 10007)
            self.baiduWeight = {
                "To": "0",
                "From": "0",
                "Weight": "0"
            }

    def getWebInfo(self, domain):
        _LOGGER.info('In getWebInfo')

        url = dealDomain(domain)
        if url['code'] != 0:
            raise MyException(url['msg'], url['code'])
        url = url['url']

        self.getResponse(url)
        t1 = threading.Thread(target=self.getBaiduWeight, args=(domain, ))
        t1.start()
        t2 = threading.Thread(target=self.getAllweb)
        t2.start()
        t4 = threading.Thread(target=self.getInclude, args=(domain, ))
        t4.start()
        t5 = threading.Thread(target=self.getAlexa, args=(url, ))
        t5.start()

        t1.join()
        t2.join()
        t4.join()
        t5.join()
        webInfo = dict()
        webInfo['title'] = None if not self.title else self.title[0]
        if not self.baiduWeight:
            raise MyException("oops can't get baidu Weight", 10009)
        else:
            webInfo['baiduWeight'] = self.baiduWeight
        webInfo['keywords'] = self.keywords
        webInfo['description'] = None if not self.desc else self.desc[0]
        webInfo['pre_size'] = self.pre_size
        webInfo['post_size'] = self.post_size
        webInfo['grate'] = self.grate
        webInfo['contentType'] = self.content_type
        webInfo['gzip'] = self.gzip
        webInfo['protocal_type'] = self.protocal_type
        webInfo['alexa'] = self.alexa if self.alexa else 0

        if not self.include:
            raise MyException("ooops can't get include", 10011)
        else:
            webInfo['include'] = self.include

        retobj = {"status": {"msg": 'WebInfo get Successfully',  "code": 1000, "time": time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": webInfo, "list": []}

        return retobj

    def getfriendLinks(self, url):
        _LOGGER.info('In getFriendLinks url:%s' % url)
        res = requests.get(url, headers=headers, timeout=5)
        html = deal_encoding(res.content, res.encoding)
        selector = etree.HTML(html)
        footer = selector.xpath('//a/@href')
        contents = []
        domain = url.split('.')[-2]

        exclude_li = []

        black_list = ['http://weibo.com', 'https://twitter.com/', 'gov.cn',
                      'http://szcert.ebs.org.cn/', 'shang.qq.com', 'ss.knet.cn', domain]
        blfilter = lambda i, url: True if i in url else False
        if footer:
            for url in footer:
                if url not in contents and re.match('^http[s]?', url) and  url[-3:] not in ['jpg', 'png', 'pdf'] \
                        and url.split('/')[2] not in exclude_li:
                    if True not in [blfilter(i, url) for i in black_list]:
                        contents.append(url)
                        exclude_li.append(url.split('/')[2])

        return contents

    def getAlexa(self, url):
        _LOGGER.info("In getAlexa")
        # Element ALEXA is root  openfile has to getroot fromstring dont
        try:
            html = requests.get(
                'http://data.alexa.com/data?cli=10&&url=%s' % url, timeout=8).content
        except requests.ReadTimeout as e:
            self.alexa = None
            return
        tree = ET.fromstring(html)
        try:
            alexa = tree[0][1].attrib['RANK']
        except IndexError as e:
            alexa = 0
        self.alexa = alexa

    def getDeadLink(self, url):
        _LOGGER.info("In getDeadLink")
        url = dealDomain(url)
        if url['code'] != 0:
            raise MyException(url['msg'], url['code'])
        url = url['url']

        links = self.getfriendLinks(url)
        qlinks = Queue.Queue()
        for i in links:
            qlinks.put(i)
        link_status = dict()
        threads = []

        def testLink():

            try:
                link = qlinks.get(timeout=5)
            except Queue.Empty:
                return

            try:
                res = requests.get(link.strip(), timeout=5)
                if res.status_code in [200, 301, 302]:
                    link_status[link] = 0
            except requests.exceptions.ConnectionError as e:
                _LOGGER.info('In testLink--%s:%s' % (link, 'url unreachable'))
                link_status[link] = 1
            except requests.exceptions.ConnectTimeout as e:
                _LOGGER.info('In testLink--%s:%s' % (link, 'timeout'))
                link_status[link] = 1
            except requests.ReadTimeout as e:
                _LOGGER.info('In testLink--%s:%s' % (link, 'unreachable too'))
                link_status[link] = 1
            except requests.exceptions.ReadTimeout as e:
                _LOGGER.info('In testLink--%s:%s' % (link, 'unreachable too'))
                link_status[link] = 1
            except Exception as e:
                _LOGGER.info('In testLink--%s:%s' % (link, 'Invilid url'))
                link_status[link] = 1

        for i in range(60):
            threads.append(
                threading.Thread(target=testLink))
            threads[-1].start()

        for i in threads:
            i.join()

        retobj = {"status": {"msg": "DeadLink get successfully", "code": 1000, "time": time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": link_status, "list": []}
        return retobj

    def getInclude(self, url):
        _LOGGER.info('In getInclude')

        if 'http' in url or 'https' in url:
            url = '.'.join(url.split('/')[2].split('.')[-2:])
        html = requests.get(
            'https://www.baidu.com/s?wd=site:%s' % url, headers=headers, timeout=5).content
        res = re.search(
            '找到相关结果数约(.*?)个|该网站共有 (.*?) 个网页被百度收录', html, re.M | re.S)
        if res:
            if res.group(1):
                baidu = res.group(1)
            else:
                baidu = re.search('>(.*?)<', res.group(2))
                baidu = baidu.group(1)
        else:
            baidu = 0

        html = requests.get(
            'https://www.so.com/s?q=site:%s' % url, timeout=5).content
        res2 = re.search('找到相关结果约(.*?)个', html)
        _360 = 0 if res2 == None else res2.group(1)

        html = requests.get(
            'https://www.sogou.com/web?query=site:%s' % url, cookies=cookies, timeout=5).content
        selector = etree.HTML(html)
        res3 = selector.xpath('//div[@class="vr-webmsg150521"]/p/em/text()')
        sogou = 0 if not res3 else res3[0]
        include = {'baidu': baidu, '360': _360, 'sogou': sogou, 'google': 0}
        self.include = include

    def getBySearchEngine(self, domain, base_url, search_engine):

        def checkEngine(domain, div, count, search_engine, topten, content):
            url = div.xpath(
                ENGINE[search_engine]['url_xpath'])
            if not url:
                return
            url = url[0]
            if search_engine in 'baidu':
                try:
                    url = requests.get(url, timeout=5).url
                except requests.ReadTimeout as e:
                    return

            elif search_engine in ['360', 'sogou']:
                try:
                    nurl = re.search(
                        "URL='(.*?)'", requests.get(url, timeout=5).content)
                except requests.ReadTimeout as e:
                    return
                if nurl:
                    url = nurl.group(1)
            if not topten and domain not in url:
                return
            title = div.xpath(ENGINE[search_engine]['title_xpath'])
            title = title[0].xpath('string(.)').strip() if title else ""
            desc = div.xpath(ENGINE[search_engine]['desc_xpath'])
            desc = desc[0].xpath('string(.)') if desc else ""
            content.append(
                {'title': title, 'desc': desc, 'url': url, 'count': count})
########################## embeded function finished  ####################
        _LOGGER.info('In %s' % search_engine)

        try:
            res = requests.get(
                base_url, headers=headers, cookies=cookies, timeout=5).content
        except requests.exceptions.ConnectionError as e:
            raise MyException("%s can not be parsed" % search_engine, 10004)
        first_page = res
        selector = etree.HTML(res)
        if search_engine in 'sogou':
            total = selector.xpath(
                ENGINE[search_engine]['rstring'])[0]
        else:
            total = re.search(
                ENGINE[search_engine]['rstring'], res).group(1)
        total = int(total.replace(',', ''))
        total = 5 if total > 50 else (
            (total/10 + 1) if total % 10 > 0 else total/10)

        count = 0
        divs = []
        threads = []
        result = []
        for i in range(total):
            if i:
                if search_engine in 'baidu':
                    nurl = base_url + '&pn=%d' % (i*10)
                elif search_engine in '360':
                    nurl = base_url + "&pn=%d" % (i+1)
                else:
                    nurl = base_url + "&page=%d" % (i+1)
                res = requests.get(
                    nurl, headers=headers, cookies=cookies, timeout=5).content
                selector = etree.HTML(res)

            divs += selector.xpath(
                ENGINE[search_engine]['content_xpath'])

        for div in divs[:10]:
            count += 1
            threads.append(
                threading.Thread(target=checkEngine, args=(domain, div, count, search_engine, False, result)))
            threads[-1].start()

        for i in threads:
            i.join()

        result = sorted(result, key=lambda info: info['count'])
        if result:
            result = result[0]

        else:
            url = dealDomain(domain)
            if url['code'] == 0:
                try:
                    self.getResponse(url['url'])
                    result = {'title': self.title[0] if self.title else "",
                              'desc': self.desc[0] if self.desc else "",
                              'url': url['url'], 'count': "50+"}
                except Exception as e:
                    _LOGGER.info(e)
                    result = {
                        'title': '', 'desc': '', 'url': url['url'], 'count': ''}

            else:
                result = {
                    'title': '', 'desc': '', 'url': url['url'], 'count': ''}

        ###############################################
        #     前十
        ###############################################

        count = 0
        content = []
        selector = etree.HTML(first_page)
        divs = selector.xpath(ENGINE[search_engine]['content_xpath'])[:10]
        for div in divs:
            count += 1
            threads.append(
                threading.Thread(target=checkEngine, args=(domain, div, count, search_engine, True, content)))
            threads[-1].start()

        for i in threads:
            i.join()
        content = sorted(content, key=lambda info: info['count'])
        return result, content

    def getKeywordRank(self, domain, keyword, search_engine):
        _LOGGER.info('In getKeywordRank ')

        redis_key = 'getKeywordRank-%s-%s-%s' % (
            domain, keyword, search_engine)

        result, content = self.getBySearchEngine(
            domain, ENGINE[search_engine]['base_url'] + keyword, search_engine)

        retobj = {"status": {"msg": 'KeywordRank data get successful', "code": 1000, "time": time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": result, "list": content}

        return retobj

    def getAllweb(self):
        _LOGGER.info('In getAllweb')

        soup = BeautifulSoup(self.content, 'lxml')
        jss = soup.find_all('script')
        css = soup.find_all('link')
        imgs = soup.find_all('img')
        links = [i.get('src') for i in jss] + [i.get('href')
                                               for i in css] + [i.get('src') for i in imgs]
        useful_links = []
        for link in links:
            if not link:
                continue
            if re.match('//', link):
                useful_links.append('http:' + link)
            elif re.match('/', link):
                useful_links.append(self.url + link)
            elif re.match('http', link) or re.match('https', link):
                useful_links.append(link)
            else:
                print link

        dirpath = os.path.dirname(os.path.realpath(__file__))
        if not os.path.exists(dirpath + '/files'):
            os.mkdir(dirpath + '/files')

        def downSourceFile(link, i):
            filename = os.path.join(dirpath, 'files/%d' % i)
            with open(filename, 'wb') as f:
                try:
                    source_file = requests.get(link, timeout=2).content
                    f.write(source_file)
                except requests.ConnectionError as e:
                    return
                except requests.ReadTimeout as e:
                    return

        threads = []
        for i in range(len(useful_links)):
            t = threading.Thread(
                target=downSourceFile, args=(useful_links[i], i))
            t.start()
            threads.append(t)

        for i in threads:
            i.join()

        with open(dirpath + '/files/index.html', 'wb') as f:
            f.write(self.content)
        pre_size = (int(self.getsize(dirpath + '/files'))/1000)
        self.pre_size = '%dk' % pre_size
        post_size = (int(self.gzipfile(dirpath))/1000)
        self.post_size = '%dk' % post_size
        self.delFiles(dirpath + '/files')
        self.delFiles(dirpath + '/gzipFiles')

        try:
            self.grate = str(
                (pre_size - post_size)*100/pre_size) + '%'
        except ZeroDivisionError as zerror:
            self.grate = '0%'

    def getsize(self, dirpath):
        size = 0
        for root, dirs, files in os.walk(dirpath):
            size += sum(os.path.getsize(os.path.join(root, name))
                        for name in files)
        return size

    def delFiles(self, dirpath):
        for root, dirs, files in os.walk(dirpath):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except IOError:
                    continue
                except OSError:
                    continue

    def gzipfile(self, dirpath):
        if not os.path.exists(dirpath + '/gzipFiles'):
            os.mkdir(dirpath + '/gzipFiles')
        for root, dirs, files in os.walk(dirpath + '/files'):
            for file in files:
                f = gzip.open(dirpath + '/gzipFiles/%s.gz' % file, 'wb')
                f.write(open(dirpath + '/files/%s' % file).read())
                f.close()
        return self.getsize(dirpath+'/gzipFiles')


def try_except(orig_func):
    @wraps(orig_func)
    def wrapper(req):
        retobj = None

        try:
            retobj = orig_func(req)
            _LOGGER.info('=========================')
        except requests.exceptions.MissingSchema as e:
            _LOGGER.error(e)
            retobj = json.dumps({"status": {"msg": 'Missing Schema', "code": 10004, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []})
        except requests.ReadTimeout as e:
            _LOGGER.error(e)
            retobj = json.dumps({"status": {"msg": 'Read Time out', "Read Time out": 10005, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []})
        except requests.exceptions.ConnectionError as e:
            _LOGGER.error(e)
            retobj = json.dumps({"status": {"msg": 'Connection Error', "code": 10005, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []})
        except MyException as e:
            _LOGGER.error(e.msg)
            retobj = {"status": {"msg": str(e.msg), "code": e.code, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
        except Exception as e:
            _LOGGER.critical(e)
            retobj = {"status": {"msg": 'Unknown Error...Please inform the Administrator', "code": 10001, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}

        finally:
            r.set(req, json.dumps(retobj))
            r.expire(req, 43200)
    return wrapper


@try_except
def run_forever(req):

    param_string = req.split('-')
    result = ""
    if param_string[0] in 'getKeywordRank':
        result = FUNC[param_string[0]](
            param_string[1], param_string[2], param_string[3])
    elif param_string[0] in 'getWebInfo':
        result = FUNC[param_string[0]](param_string[1])
    else:
        result = FUNC[param_string[0]](param_string[1])

    return result

if __name__ == "__main__":
    seo = SEOscrapy()
    FUNC = {'getKeywordRank': seo.getKeywordRank,
            'getDeadLink': seo.getDeadLink, 'getWebInfo': seo.getWebInfo}
    while True:
        req = r.rpop(QUEUE_NAME)
        if not req:
            time.sleep(1)
            continue
        _LOGGER.info("Deal with %s" % req)
        run_forever(req)
