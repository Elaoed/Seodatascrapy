# encoding=utf-8
from functools import wraps
import json
import os
from os import path
import Queue
import re
import sys
import time
import gzip
import threading
reload(sys)

from bs4 import BeautifulSoup
import redis
from lxml import etree
import requests
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from kits.config import ROOT_PATH
from kits.log import get_logger
from kits.dealDomain import dealDomain, divArticle, deal_encoding
from kits.MyException import MyException

sys.setdefaultencoding('utf-8')
QUEUE_NAME = 'request_queue'
webQueue = Queue.Queue()
BufSize = 1024*8

with open(path.join(ROOT_PATH, 'config/db.conf'), 'r') as f:
    redis_conf = json.load(f)
r = redis.StrictRedis(
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

cookies = {'ABTEST': '8|1480486710|v17', 'IPLOC': 'CN3301',
           'SUV': '00022B8973C7A1E9583E6F378BBF2990', 'pgv_pvi': '6522359808',
           'CXID': 'E956BE05F59EE72F925850993B6EDEE3',
           'sw_uuid': '2757471428', 'sg_uuid': '1914649634',
           'ad': '@Z4MSZllll2Y5f@3lllllVPydTkllllltDWPfyllll9lllllRklll5@@@@@@@@@@',
           'SUID': '0B25797D556C860A580095E0000ACAF9', 'SNUID': 'AE7F60E6D9DF99663127B35BDAB0F736',
           'sct': '24', 'ld': 's5n52lllll2Y5uDTlllllVPFvoZllllltDWPfyllll9lllll9llll5@@@@@@@@@@',
           'browerV': '3', 'osV': '2', 'sst0': '888'}


_LOGGER = get_logger("seoScrapy")

ENGINE = {
    'baidu': {'base_url': 'http://www.baidu.com/s?wd=',
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


class SeoScrapy(object):

    def __init__(self):
        self.url = ''
        self.pro_type = ''
        self.res = ''
        self.include = None
        self.pre_size = ''
        self.post_size = ''
        self.gRate = ''

    def web_info(self, domain):
        url = r.get(domain)
        if not url:
            url_obj = dealDomain(domain)
            if url_obj['code'] != 0:
                raise MyException(url_obj['msg'], url_obj['code'])
            url = url_obj['url']
            r.set(domain, url)

        res = requests.get(url, headers=headers, cookies=cookies, timeout=5)

        selector = etree.HTML(res.content)
        desc = selector.xpath('//*[@name="description"]/@content')
        title = selector.xpath('//title/text()')
        keywords = selector.xpath('//*[@name="keywords"]/@content')
        keywords = "" if not keywords else keywords[0]
        # keyword_list = divArticle(res.content)

        for i in divArticle(res.content):
            keywords += " %s " % i[0].encode()

        webInfo = dict()
        webInfo['title'] = None if not title else title[0]
        webInfo['keywords'] = keywords
        webInfo['description'] = None if not desc else desc[0]

        retobj = {"status": {"msg": '%s in web_info good' % domain,  "code": 1000,
                             "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                  "info": webInfo, "list": []}
        return retobj

    def friend_link(self, url):
        u'''Get friend links of url'''

        res = requests.get(url, headers=headers, timeout=5)
        html = deal_encoding(res.content, res.encoding)
        selector = etree.HTML(html)
        footer = selector.xpath('//a/@href')
        contents = []
        domain = url.split('/')[2]
        exclude_li = []

        black_list = ['http://weibo.com', 'https://twitter.com/', 'gov.cn',
                      'http://szcert.ebs.org.cn/', 'shang.qq.com', 'ss.knet.cn', domain]
        blfilter = lambda i, url: True if i in url else False
        if footer:
            for url in footer:
                if url not in contents and re.match('^http[s]?', url) and url[-3:] not in ['jpg', 'png', 'pdf', 'exe', 'rar', 'mp3'] and url.split('/')[2] not in exclude_li:
                    if True not in [blfilter(i, url) for i in black_list]:
                        contents.append(url)
                        exclude_li.append(url.split('/')[2])

        link_queue = Queue.Queue()
        frilink = {}
        for link in contents:
            link_queue.put(link)
            frilink[link] = -1

        return link_queue, frilink

    def dead_link(self, domain):
        url = r.get(domain)
        if not url:
            url_obj = dealDomain(domain)
            if url_obj['code'] != 0:
                raise MyException(url_obj['msg'], url_obj['code'])
            url = url_obj['url']
            r.set(domain, url)

        qlinks, link_status = self.friend_link(url)
        retobj = {"status": {"msg": 'part of dead link', "code": 10020,
                             "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                  "info": link_status, "list": []}
        r.set('dead_link:::%s' % domain, json.dumps(retobj))
        threads = []

        def testLink():

            while True:
                try:
                    link = qlinks.get(timeout=5)
                except Queue.Empty:
                    return
                try:
                    res = requests.get(
                        link.strip(), timeout=5, headers=headers, cookies=cookies)
                    if res.status_code == 200:
                        link_status[link] = 0
                    else:
                        link_status[link] = 1
                except Exception as e:
                    _LOGGER.info('test_link %s, reason:%s', link, e)
                    link_status[link] = 1

        thread_total = 20 if len(link_status) > 30 else len(link_status)
        for i in range(thread_total):
            threads.append(
                threading.Thread(target=testLink))
            threads[-1].start()

        for i in threads:
            i.join()

        retobj = {"status": {"msg": "%s get DeadLink good" % url, "code": 1000, "time": time.strftime(
            '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": link_status, "list": []}
        return retobj

    def get_weight(self, domain):

        appkey = '618e7a46808573be2401596582de62fb'
        baidu_weight = {
            "To": "0",
            "From": "0",
            "Weight": "0"
        }
        code = 10010
        res = requests.post(
            'http://op.juhe.cn/baiduWeight/index', data={'key': appkey, 'domain': domain}, timeout=5)

        if res and res.status_code == 200 and res.content:
            jres = json.loads(res.content)
            if jres['error_code'] == 0:
                baidu_weight = jres['result']
                code = 1000
            else:
                _LOGGER.error('res from juhe.cn: reason:%s, error_code:%d',
                              jres['reason'], jres['error_code'])
        else:
            _LOGGER.error("baidu weight: %s no response or httpcode:%s",
                          (domain, res.status_code))
        retobj = {"status": {"msg": '%s baidu weight good' % domain,  "code": code,
                             "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                  "info": baidu_weight, "list": []}
        return retobj

    def get_alexa(self, domain):
        ''' Get alexa rank of domain from http://data.alexa.com/ 
        '''
        _LOGGER.info("In getAlexa")
        alexa = 0
        code = 10012
        try:
            html = requests.get(
                'http://data.alexa.com/data?cli=10&&url=%s' % domain, timeout=8, headers=headers).content
            tree = ET.fromstring(html)
            alexa = tree[0][1].attrib['RANK']
            code = 1000
        except IndexError as err:
            _LOGGER.info('get_alexa, %s %s', domain, err)
            code = 1000
        except Exception as err:
            _LOGGER.info('get_alexa, %s %s', domain, err)

        retobj = {"status": {"msg": '%s alexa good' % domain, "code": code,
                             "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                  "info": {'alexa': alexa}, "list": []}
        return retobj

    def get_include(self, domain):
        try:
            html = requests.get(
                'https://www.baidu.com/s?wd=site:%s' % domain, headers=headers, timeout=5).content
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
                'https://www.so.com/s?q=site:%s' % domain, timeout=5).content
            res2 = re.search('找到相关结果约(.*?)个', html)
            _360 = 0 if res2 == None else res2.group(1)

            html = requests.get(
                'https://www.sogou.com/web?query=site:%s' % domain, cookies=cookies, timeout=5).content
            selector = etree.HTML(html)
            res3 = selector.xpath(
                '//div[@class="vr-webmsg150521"]/p/em/text()')
            sogou = 0 if not res3 else res3[0]
            include = {
                'baidu': baidu, '360': _360, 'sogou': sogou, 'google': 0}

            retobj = {"status": {"msg": '%s include good' % domain,  "code": 1000,
                                 "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                      "info": include, "list": []}
        except Exception as e:
            _LOGGER.ERROR('ERROR in get include, %s', e)
            retobj = {"status": {"msg": '%s include error' % domain,  "code": 10011,
                                 "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                      "info": include, "list": []}
        return retobj

    def get_url(self, div, search_engine):
        url = div.xpath(ENGINE[search_engine]['url_xpath'])
        if not url:
            return None
        url = url[0]
        try:
            if search_engine in 'baidu':
                _LOGGER.debug("before request to %s", url)
                res = requests.get(url, timeout=4, headers=headers, cookies=cookies)
                _LOGGER.debug("hey middle")
                nurl = res.url
                _LOGGER.debug("finish request to %s", url)
            else:
                nurl = re.search(
                    "URL='(.*?)'", requests.get(url, timeout=2, headers=headers, cookies=cookies).content)
                nurl = nurl.group(1) if nurl else None
            return nurl
        except requests.ReadTimeout as e:
            _LOGGER.debug("timeout request to %s", url)
            return None
        except Exception as e:
            return None

    def engine_data(self, div, count, search_engine, content):
        _LOGGER.debug('%d before get url', count)
        url = self.get_url(div, search_engine)
        _LOGGER.debug('%d after get url', count)
        if not url:
            return
        title = div.xpath(ENGINE[search_engine]['title_xpath'])
        title = title[0].xpath('string(.)').strip() if title else ""
        desc = div.xpath(ENGINE[search_engine]['desc_xpath'])
        desc = desc[0].xpath('string(.)') if desc else ""

        content.append(
            {'title': title, 'desc': desc, 'url': url, 'count': count})
        _LOGGER.debug('%d finish append', count)

    def top_ten(self, search_engine, keyword):
        u'''Get top ten '''

        _LOGGER.debug("start")
        base_url = ENGINE[search_engine]['base_url'] + keyword
        res = requests.get(base_url).content
        _LOGGER.debug("get first page content")
        content = []
        selector = etree.HTML(res)
        divs = selector.xpath(ENGINE[search_engine]['content_xpath'])[:10]
        _LOGGER.debug("get divs") 
        count = 0
        threads = []
        for div in divs:
            count += 1
            threads.append(
                threading.Thread(target=self.engine_data, args=(div, count, search_engine, content))
            )
            threads[-1].start()
        for i in threads:
            i.join()
        _LOGGER.debug("finish xpath from div")
        content = sorted(content, key=lambda info: info['count'])
        _LOGGER.debug("sorted")
        retobj = {"status": {"msg": 'engine:%s, keyword:%s, good' % (search_engine, keyword),
                             "code": 1000, "time": time.strftime('%Y-%m-%d %H:%M:%S',
                                                                 time.localtime())},
                  "info": {}, "list": content}
        return retobj

    def get_rank(self, domain, base_url, search_engine, keyword):
        _LOGGER.info('Using search engine:%s',  search_engine)
        try:
            res = requests.get(
                base_url, headers=headers, cookies=cookies, timeout=5).content
        except requests.exceptions.ConnectionError as e:
            _LOGGER.warning("%s %s", base_url, e)
            raise MyException("%s can not be parsed" % base_url, 10004)
        selector = etree.HTML(res)
        if search_engine in 'sogou':
            try:
                total = selector.xpath(ENGINE[search_engine]['rstring'])[0]
            except IndexError as e:
                _LOGGER.error('IndexError scrapy Sogou too fast')
                raise MyException('IndexError scrapy Sogou too fast', 10005)
        else:
            total = re.search(
                ENGINE[search_engine]['rstring'], res).group(1)
        total = int(total.replace(',', ''))
        total = 5 if total > 50 else (
            (total/10 + 1) if total % 10 > 0 else total/10)

        count = 0
        divs = []
        threads = []
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

        def check_rank(domain, div, count, search_engine, content):
            url = div.xpath(ENGINE[search_engine]['url_xpath'])
            if not url:
                return
            url = url[0]
            if search_engine in 'baidu':
                try:
                    url = requests.get(url, timeout=5).url
                except requests.ReadTimeout as e:
                    return
                except Exception as e:
                    return

            elif search_engine in ['360', 'sogou']:
                try:
                    nurl = re.search(
                        "URL='(.*?)'", requests.get(url, timeout=5).content)
                except requests.ReadTimeout as e:
                    return
                except Exception as e:
                    return
                if nurl:
                    url = nurl.group(1)
            if domain in url:
                content.append(count)

        content = []
        count = 0
        for div in divs:
            count += 1
            threads.append(threading.Thread(
                target=check_rank, args=(domain, div, count, search_engine, content)))
            threads[-1].start()
        for thread in threads:
            thread.join()
        count = sorted(content)[0] if content else '50+'
        return count

    def keyword_rank(self, domain, search_engine, keyword):

        count = self.get_rank(domain, ENGINE[search_engine]['base_url'] + keyword,
                              search_engine, keyword)
        retobj = {"status": {"msg": '%s keyword get good' % domain, "code": 1000,
                             "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                  "info": {'count': count}, "list": []}
        return retobj

    def server_info(self, domain):
        url = r.get(domain)
        if not url:
            url_obj = dealDomain(domain)
            if url_obj['code'] != 0:
                _LOGGER.error(
                    '%s code:%s', url_obj['msg'], url_obj['code'])
                raise MyException(url_obj['msg'], url_obj['code'])
            url = url_obj['url']
            r.set(domain, url)
        res = requests.get(
            url, timeout=5, headers=headers, cookies=cookies)
        if res.status_code is not 200:
            _LOGGER.warning(
                "%s's return httpcode is %d", url, res.status_code)
            raise MyException("%s server_info" % url, 10004)
        content = deal_encoding(res.content, res.encoding)
        protocal_type = url.split(':')[0]
        if 'Content-Type' in res.headers.keys():
            content_type = res.headers['Content-Type']
        else:
            content_type = res.headers['content-type']

        if 'Content-Encoding' in res.headers.keys():
            gzip = 'On' if 'gzip' in res.headers[
                'Content-Encoding'] else 'Off'
        elif 'content-encoding' in res.headers.keys():
            gzip = 'On' if 'gzip' in res.headers[
                'content-encoding'] else 'Off'
        else:
            gzip = 'Off'
        pre_size, post_size, grate = self.get_web_source(content, url)

        server_info = {}
        server_info['pre_size'] = pre_size
        server_info['post_size'] = post_size
        server_info['grate'] = grate
        server_info['contentType'] = content_type
        server_info['gzip'] = gzip
        server_info['protocal_type'] = protocal_type
        retobj = {"status": {"msg": '%s server info get good' % domain, "code": 1000,
                             "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                  "info": server_info, "list": []}
        return retobj

    def get_web_source(self, content, url):
        _LOGGER.info('In getAllweb')

        soup = BeautifulSoup(content, 'lxml')
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
                useful_links.append(url + link)
            elif re.match('http', link) or re.match('https', link):
                useful_links.append(link)
            else:
                continue

        dirpath = os.path.dirname(os.path.realpath(__file__))
        before_filepath = os.path.join(dirpath, 'files/%s_files' % url)
        gzip_filepath = os.path.join(
            dirpath, 'files/%s_gzipfiles' % url)
        if not os.path.exists(before_filepath):
            os.makedirs(before_filepath)

        def downSourceFile(link, i, before_filepath):
            filename = os.path.join(before_filepath + '/' + str(i))
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
                target=downSourceFile, args=(useful_links[i], i, before_filepath))
            t.start()
            threads.append(t)

        for i in threads:
            i.join()

        with open(os.path.join(before_filepath, 'index.html'), 'wb') as f:
            f.write(content)

        pre_size = self.get_size(before_filepath)/1000
        post_size = self.gzip_file(before_filepath, gzip_filepath)/1000

        self.del_Files(before_filepath)
        self.del_Files(gzip_filepath)

        try:
            grate = str(
                (pre_size - post_size)*100/pre_size) + '%'
        except ZeroDivisionError as zerror:
            grate = '0%'

        return '%dk' % pre_size, '%dk' % post_size, grate

    def get_size(self, dirpath):
        size = 0
        for root, dirs, files in os.walk(dirpath):
            size += sum(os.path.getsize(os.path.join(root, name))
                        for name in files)
        return size

    def del_Files(self, dirpath):
        for root, dirs, files in os.walk(dirpath):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except IOError:
                    continue
                except OSError:
                    continue

    def gzip_file(self, before_filepath, gzip_filepath):
        if not os.path.exists(gzip_filepath):
            os.makedirs(gzip_filepath)
        for root, dirs, files in os.walk(before_filepath):
            for file in files:
                f = gzip.open(os.path.join(gzip_filepath, file), 'wb')
                f.write(open(os.path.join(before_filepath, file)).read())
                f.close()
        return self.get_size(gzip_filepath)


def try_except(orig_func):
    @wraps(orig_func)
    def wrapper(req):
        retobj = None

        try:
            retobj = orig_func(req)
        except requests.exceptions.MissingSchema as e:
            _LOGGER.error(e)
            retobj = {"status": {"msg": 'Missing Schema', "code": 10004,
                                 "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                      "info": {}, "list": []}
        except requests.ReadTimeout as e:
            _LOGGER.error(e)
            retobj = {"status": {"msg": 'Read Time out', "Read Time out": 10005,
                                 "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                      "info": {}, "list": []}
        except requests.exceptions.ConnectionError as e:
            _LOGGER.error(e)
            retobj = {"status": {"msg": 'Connection Error', "code": 10005, "time": time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime())}, "info": {}, "list": []}
        except MyException as e:
            _LOGGER.error("%s, code:%d", e.msg, e.code)
            retobj = {"status": {"msg": str(e.msg), "code": e.code,
                                 "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                      "info": {}, "list": []}
        except Exception as e:
            _LOGGER.critical(e)
            retobj = {"status": {"msg": 'Unknown Error...Please inform the Administrator', "code": 10001,
                                 "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())},
                      "info": {}, "list": []}
        finally:
            _LOGGER.info('%s ==============', req)
            r.set(req, json.dumps(retobj))
            r.expire(req, 43200)
            _LOGGER.info('%s **************', req)
            
    return wrapper


@try_except
def run_forever(req):
    '''
        put domain:url to redis                 domain:::url        -> json        remark: TODO
        1.getWebInfo --> get_include(domain)    domain:::include    -> json
                     --> get_alexa(domain)      domain:::alexa      -> json
                     --> get_server_info(domain)domain:::server_info-> json
                     --> get_web_info(url)      domain:::web_info   -> json
                     --> get_weight(domain)     domain:::weight     -> json

        2.dead_link(url)                        domain:::dead_link  -> json

        3.keyword_rank(url, keyword)            domain:::keyword_rank:::search_engine:::keyword   -> json       
                                                search_engine:::keyword -> json

    '''

    _LOGGER.info("Deal %s", req)
    param_string = req.split(':::')
    result = ""

    if param_string[1] in 'keyword_rank':
        result = FUNC[param_string[1]](
            param_string[0], param_string[2], param_string[3])
    elif param_string[0] in 'top_ten':
        result = FUNC[param_string[0]](param_string[1], param_string[2])
    else:
        result = FUNC[param_string[0]](param_string[1])
    return result

if __name__ == "__main__":
    seo = SeoScrapy()
    FUNC = {'keyword_rank': seo.keyword_rank, 'dead_link': seo.dead_link,
            'web_info': seo.web_info, 'get_alexa': seo.get_alexa,
            'get_include': seo.get_include, 'get_weight': seo.get_weight,
            'server_info': seo.server_info, 'top_ten': seo.top_ten}

    while True:
        req = r.rpop(QUEUE_NAME)
        if not req:
            time.sleep(1)
            continue
        task = threading.Thread(target=run_forever, args=(req, ))
        task.start()
        time.sleep(0.1)
