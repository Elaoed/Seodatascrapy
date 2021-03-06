# -*- coding: utf-8 -*-
"""Main module of dealing with seo scrapy request"""

import gevent
from gevent import monkey
monkey.patch_socket()

import os
import re
import json
import time
import gzip
import copy
import shutil
from functools import wraps

import requests
from bs4 import BeautifulSoup
from lxml import etree
import xml.etree.cElementTree as ET

from kits.log import get_logger
from kits.log import ROOT_PATH
from kits.utils import blfilter
from kits.utils import gget
from kits.redispool import Redispool

from config.conf import config
from kits.constants import RETOBJ
from kits.constants import ENGINE
from kits.constants import COOKIES
from kits.constants import HEADERS
from kits.constants import QUEUE_NAME
from kits.deal_domain import get_response
from kits.deal_domain import divide_article
from kits.my_exception import MyException

config['redis'] = Redispool(queue=QUEUE_NAME)
config['logger'] = get_logger("seoScrapy")

class SeoScrapy(object):
    """SEO data Scrapy"""

    def __init__(self):
        self.domain = ''
        self.url = ''
        self.pro_type = ''
        self.res = ''
        self.include = None
        self.pre_size = ''
        self.post_size = ''
        self.gRate = ''
        self.response = None

    def web_info(self, domain):

        self.response = get_response(domain)
        selector = etree.HTML(self.response.text)
        desc = selector.xpath('//*[@name="description"]/@content')
        title = selector.xpath('//title/text()')
        keywords = selector.xpath('//*[@name="keywords"]/@content')
        keywords = "" if not keywords else keywords[0]

        divide_result = divide_article(self.response.text)
        for res in divide_result:
            keywords += " %s " % res[0]

        web_info = dict()
        web_info['title'] = "" if not title else title[0]
        web_info['keywords'] = keywords
        web_info['description'] = "" if not desc else desc[0]

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = domain + ' in web_info good'
        retobj['status']['code'] = 1000
        retobj['info'] = web_info
        return retobj

    def get_all_links(self, domain):
        self.response = get_response(domain)
        if not self.response:
            raise MyException("Has no Response object returned", 10030)

        html = self.response.text
        selector = etree.HTML(html)
        urls = selector.xpath('//a/@href')
        return urls

    def friend_link(self, domain):
        """Get friend links of given website"""

        urls = self.get_all_links(domain)
        black_list = ['weibo.com', 'twitter.com', 'gov.cn', 'shang.qq.com',
                      'szcert.ebs.org.cn', 'ss.knet.cn']
        exclude_suffix = ['jpg', 'png', 'pdf', 'exe', 'rar', 'mp3']

        # remove links without http[s] or suffix in files suffix or in black list
        def filter_url(url):
            if re.match('^http[s]?', url) and url[-3:] not in exclude_suffix:
                if not any([blfilter(_domain, url) for _domain in black_list]):
                    return url
        urls = [filter_url(url) for url in urls]
        urls = [url for url in urls if url]

        domain_url = []
        not_domain_url = []
        for url in urls:
            if domain in url:
                domain_url.append(url)
            else:
                not_domain_url.append(url)

        session = requests.Session()
        urls = [res.url for res in gget(domain_url, session=session) if res]
        frilink = []
        for url in urls + not_domain_url:
            if url not in frilink and domain not in url:
                frilink.append(url)

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = "part of dead link"
        retobj['status']['code'] = 10020
        retobj['info'] = frilink
        config['redis'].set('dead_link:::' + domain, json.dumps(retobj))

        return frilink

    def dead_link(self, domain):

        urls = self.get_all_links(domain)
        frilink = dict()
        res = gget(urls, timeout=3)

        for index, url in enumerate(res):
            if not url:
                frilink[urls[index]] = 1
            elif 200 <= url.status_code < 400:
                frilink[urls[index]] = 0
            else:
                frilink[urls[index]] = 1

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = domain + " get DeadLink good"
        retobj['status']['code'] = 1000
        retobj['info'] = frilink
        config['logger'].debug(retobj)
        return retobj

    def get_weight(self, domain):

        url = 'http://op.juhe.cn/baiduWeight/index'
        appkey = '618e7a46808573be2401596582de62fb'
        data = {
            'key': appkey,
            'domain': domain
        }
        baidu_weight = {
            "To": "0",
            "From": "0",
            "Weight": "0"
        }
        code = 10010
        res = requests.post(url, data=data, timeout=5)

        if res.status_code is 200:
            jres = res.json()
            if jres['error_code'] == 0:
                baidu_weight = jres['result']
                code = 1000
            else:
                err_msg = ("res from juhe.cn: reason:" + jres['reason'] +
                           ", error_code:" + jres['err_code'])
                config['logger'].error(err_msg)
        else:
            err_msg = ("baidu weight: " + domain + " no response or httpcode:" + res.status_code)
            config['logger'].error(err_msg)

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['code'] = code
        retobj['status']['msg'] = domain + ' baidu weight good'
        retobj['info'] = baidu_weight
        config['logger'].debug(retobj)
        return retobj

    def get_alexa(self, domain):
        """Get alexa rank of domain from http://data.alexa.com/"""
        config['logger'].info("In getAlexa")
        alexa = 0
        code = 10012
        try:
            res = requests.get('http://data.alexa.com/data?cli=10&&url=' + domain,
                               timeout=8,
                               headers=HEADERS)
            html = res.content
            tree = ET.fromstring(html)
            alexa = tree[0][1].attrib['RANK']
            code = 1000
        except IndexError as err:
            config['logger'].info('get_alexa, %s %s', domain, err)
            code = 1000
        except Exception as err:
            config['logger'].info('get_alexa, %s %s', domain, err)

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['code'] = code
        retobj['status']['msg'] = domain + " alexa good"
        retobj['info'] = alexa
        config['logger'].debug(retobj)
        return retobj

    def get_include(self, domain):

        baidu_str = 'https://www.baidu.com/s?wd=site:%s' + domain
        html = requests.get(baidu_str, headers=HEADERS, timeout=5).text

        pattern = '找到相关结果数约(.*?)个|该网站共有 (.*?) 个网页被百度收录'
        res = re.search(pattern, html, re.M | re.S)

        if res:
            if res.group(1):
                baidu = res.group(1)
            else:
                baidu = re.search('>(.*?)<', res.group(2))
                baidu = baidu.group(1)
        else:
            baidu = 0

        _360_str = 'https://www.so.com/s?q=site:' + domain
        html = requests.get(_360_str, timeout=5).text
        res2 = re.search('找到相关结果约(.*?)个', html)
        _360 = 0 if res2 is None else res2.group(1)

        sogou_str = 'https://www.sogou.com/web?query=site:' + domain
        html = requests.get(sogou_str, cookies=COOKIES, timeout=5).text
        selector = etree.HTML(html)
        res3 = selector.xpath('//div[@class="vr-webmsg150521"]/p/em/text()')
        sogou = 0 if not res3 else res3[0]

        include = {'baidu': baidu,
                   '360': _360,
                   'sogou': sogou,
                   'google': 0}

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['code'] = 1000
        retobj['status']['msg'] = domain + " get include successful"
        retobj['info'] = include
        config['logger'].debug(retobj)
        return retobj

    def get_url(self, div, search_engine):
        url = div.xpath(ENGINE[search_engine]['url_xpath'])
        if not url:
            return None
        url = url[0]
        try:
            if search_engine in 'baidu':
                res = requests.get(url, timeout=4, headers=HEADERS, cookies=COOKIES)
                nurl = res.url
            else:
                res = requests.get(url, timeout=2, headers=HEADERS, cookies=COOKIES)
                nurl = re.search("URL='(.*?)'", res.text)
                nurl = nurl.group(1) if nurl else None
            return nurl
        except requests.ReadTimeout:
            config['logger'].error("%s Timeout", url)
            return None
        except Exception:
            return None

    def engine_data(self, div, search_engine):

        url = self.get_url(div, search_engine)
        if not url:
            return

        title = div.xpath(ENGINE[search_engine]['title_xpath'])
        title = title[0].xpath('string(.)').strip() if title else ""
        desc = div.xpath(ENGINE[search_engine]['desc_xpath'])
        desc = desc[0].xpath('string(.)') if desc else ""

        return {'title': title, 'desc': desc, 'url': url, 'count': 0}

    def top_ten(self, search_engine, keyword):
        """Get top ten"""
        base_url = ENGINE[search_engine]['base_url'] + keyword
        res = requests.get(base_url, headers=HEADERS, cookies=COOKIES, timeout=3).text
        content = []
        selector = etree.HTML(res)
        divs = selector.xpath(ENGINE[search_engine]['content_xpath'])[:10]
        for index, div in enumerate(divs):
            res = self.engine_data(div, search_engine)
            res['count'] = index
            content.append(res)

        content = sorted(content, key=lambda info: info['count'])

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = 'top_ten engine:%s, keyword:%s, good' % (search_engine, keyword)
        retobj['list'] = content
        config['logger'].debug(retobj)
        return retobj

    # def get_rank(self, domain, base_url, search_engine):
    #     config['logger'].info('Using search engine:' + search_engine)
    #     try:
    #         res = requests.get(base_url,
    #                            headers=HEADERS,
    #                            cookies=COOKIES,
    #                            timeout=5).text

    #     except requests.exceptions.ConnectionError:
    #         config['logger'].warning(base_url + " Connection error")
    #         raise MyException(base_url + " can not be parsed", 10004)

    #     selector = etree.HTML(res)
    #     if search_engine == 'sogou':
    #         try:
    #             total = selector.xpath(ENGINE[search_engine]['rstring'])[0]
    #         except IndexError:
    #             config['logger'].error('IndexError scrapy Sogou too fast')
    #             raise MyException('IndexError scrapy Sogou too fast', 10005)
    #     else:
    #         total = re.search(ENGINE[search_engine]['rstring'], res).group(1)

    #     total = int(total.replace(',', ''))
    #     total = 5 if total > 50 else (
    #         (total // 10 + 1) if total % 10 > 0 else total // 10)

    #     count = 0
    #     divs = []
    #     urls = []
    #     for i in range(1, total):
    #         if search_engine == 'baidu':
    #             nurl = base_url + '&pn=' + str(i * 10)
    #         elif search_engine == '360':
    #             nurl = base_url + "&pn=" + str(i + 1)
    #         else:
    #             nurl = base_url + "&page=" + str(i + 1)
    #         urls.append(nurl)

    #     reses = gget(urls, timeout=3)
    #     for res in reses:
    #         selector = etree.HTML(res.text)
    #         divs += selector.xpath(ENGINE[search_engine]['content_xpath'])

    #     def check_baidu_rank(divs):

    #         urls = []
    #         for div in divs:
    #             url = div.xpath(ENGINE[search_engine]['url_xpath'])
    #             urls += url
    #         return urls

    #     def check_sogou_360_rank(divs):

    #         urls = []
    #         for div in divs:
    #             url = div.xpath(ENGINE[search_engine]['url_xpath'])
    #             urls.append(url)

    #         reses = gget(urls, timeout=3)

    #         urls = []
    #         for res in reses:
    #             urls.append(re.search("URL='(.*?)'", res.text))
    #         return urls

    #     if search_engine == 'baidu':
    #         urls = check_baidu_rank(divs)
    #         print("urls from check rank")
    #     elif search_engine in ['360', 'sogou']:
    #         urls = check_sogou_360_rank(divs)

    #     count = None
    #     # print(urls)
    #     start = int(time.time())
    #     reses = gget(urls, timeout=3)
    #     print(int(time.time()) - start)
    #     urls = {}
    #     for index, res in enumerate(reses, 1):
    #         if res:
    #             if domain in res.url:
    #                 count = str(index)
    #                 break
    #     else:
    #         count = '50+'

    #     return count

    # def keyword_rank(self, domain, search_engine, keyword):

    #     count = self.get_rank(domain,
    #                           ENGINE[search_engine]['base_url'] + keyword,
    #                           search_engine)

    #     retobj = copy.deepcopy(RETOBJ)
    #     retobj['status']['msg'] = domain + ' keyword get good'
    #     retobj['info'] = {'count': count}
    #     config['logger'].debug(retobj)
    #     return retobj

    def server_info(self, domain):

        self.domain = domain
        self.response = get_response(domain)
        if not self.response:
            msg = domain + "Connection Error"
            config['logger'].warning(msg)
            raise Exception(domain + " server_info", 10004)

        res = self.response
        self.url = res.url

        if res.status_code is not 200:
            msg = ''.join([res.url, "'s return httpcode is ", str(res.status_code)])
            config['logger'].warning(msg)
            raise MyException(res.url + " server_info", 10004)

        protocal_type = self.response.url.split(':')[0]
        if 'Content-Type' in res.headers:
            content_type = res.headers['Content-Type']
        else:
            content_type = res.headers['content-type']

        if 'Content-Encoding' in res.headers:
            gzip_compress = 'On' if 'gzip' in res.headers['Content-Encoding'] else 'Off'
        elif 'content-encoding' in res.headers:
            gzip_compress = 'On' if 'gzip' in res.headers['content-encoding'] else 'Off'
        else:
            gzip_compress = 'Off'
        pre_size, post_size, grate = self.get_web_source()

        server_info = {}
        server_info['pre_size'] = pre_size
        server_info['post_size'] = post_size
        server_info['grate'] = grate
        server_info['contentType'] = content_type
        server_info['gzip'] = gzip_compress
        server_info['protocal_type'] = protocal_type

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = domain + ' server info get good'
        retobj['info'] = server_info
        config['logger'].debug(retobj)
        return retobj

    def get_web_source(self):

        soup = BeautifulSoup(self.response.text, 'lxml')
        jss = [i.get('src') for i in soup.find_all('script')]
        css = [i.get('href') for i in soup.find_all('link')]
        imgs = [i.get('src') for i in soup.find_all('img')]
        links = jss + css + imgs

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
                continue

        before_filepath = os.path.join(ROOT_PATH, 'files/' + self.domain + '_files')
        gzip_filepath = os.path.join(ROOT_PATH, 'files/' + self.domain + '_gzipfiles')

        if not os.path.exists(before_filepath):
            os.makedirs(before_filepath)

        if not os.path.exists(gzip_filepath):
            os.makedirs(gzip_filepath)

        reses = gget(useful_links, timeout=3)
        for index, res in enumerate(reses):
            if res and res.status_code is 200:
                filename = os.path.join(before_filepath, str(index))
                with open(filename, 'wb') as file_handler:
                    file_handler.write(res.content)

        with open(os.path.join(before_filepath, 'index.html'), 'wb') as file_handler:
            file_handler.write(self.response.content)

        pre_size = self.get_size(before_filepath) // 1000
        post_size = self.gzip_file(before_filepath, gzip_filepath) // 1000

        self.del_Files(before_filepath)
        self.del_Files(gzip_filepath)

        try:
            grate = str((pre_size - post_size) * 100 // pre_size) + '%'
        except ZeroDivisionError:
            grate = '0%'

        return '%dk' % pre_size, '%dk' % post_size, grate

    def get_size(self, dirpath):
        size = 0
        for root, _, files in os.walk(dirpath):
            size += sum(os.path.getsize(os.path.join(root, name))
                        for name in files)
        return size

    def del_Files(self, dirpath):
        shutil.rmtree(dirpath, True)

    def gzip_file(self, before_filepath, gzip_filepath):

        for _, _, files in os.walk(before_filepath):
            for file_name in files:
                gzip_fd = gzip.open(os.path.join(gzip_filepath, file_name), 'wb')
                filename = os.path.join(before_filepath, file_name)
                with open(filename, 'rb') as f:
                    content = f.read()
                gzip_fd.write(content)
                gzip_fd.close()
        return self.get_size(gzip_filepath)


def try_except(orig_func):

    @wraps(orig_func)
    def wrapper(req):
        retobj = None

        try:
            retobj = orig_func(req)

        except MyException as err_msg:
            config['logger'].error(err_msg.msg)
            retobj = copy.deepcopy(RETOBJ)
            retobj['status']['msg'] = err_msg.msg
            retobj['status']['code'] = err_msg.code

        except requests.exceptions.ConnectTimeout:
            err_msg = "Connect Time out"
            config['logger'].error(err_msg)
            retobj = copy.deepcopy(RETOBJ)
            retobj['status']['msg'] = err_msg
            retobj['status']['code'] = 10005

        except requests.exceptions.ReadTimeout:
            err_msg = "Read Time out"
            config['logger'].error(err_msg)
            retobj = copy.deepcopy(RETOBJ)
            retobj['status']['msg'] = err_msg
            retobj['status']['code'] = 10005

        except requests.exceptions.ConnectionError:
            err_msg = "Connection error"
            config['logger'].error(err_msg)
            retobj = copy.deepcopy(RETOBJ)
            retobj['status']['msg'] = err_msg
            retobj['status']['code'] = 10005

        except Exception:
            config['logger'].critical("Exceptions", exc_info=True)
            retobj = copy.deepcopy(RETOBJ)
            retobj['status']['msg'] = 'Unknown Error...Please inform the Administrator'
            retobj['status']['code'] = 10001

        finally:
            config['logger'].info('%s ==============', req)
            config['redis'].setex(req, json.dumps(retobj), 43200)
            config['logger'].info('%s **************', req)

    return wrapper


@try_except
def run_forever(req):
    """
        put domain:url to redis                 url:::domain        -> json        remark: TODO
        1.getWebInfo --> get_include(domain)    include:::domain    -> json
                     --> get_alexa(domain)      alexa:::domain      -> json
                     --> get_server_info(domain)server_info:::domain-> json
                     --> get_web_info(url)      web_info:::domain   -> json
                     --> get_weight(domain)     weight:::domain     -> json

        2.dead_link(url)                        dead_link:::domain   -> json
        2.friend_link(url)                      friend_link:::domain -> json

        3.keyword_rank(url, keyword)(canceled)  domain:::keyword_rank:::search_engine:::keyword
                                                search_engine:::keyword -> json.
        4.whois core data

    """
    config['logger'].info("Deal " + req)
    param_string = req.split(':::')

    if param_string[1] in 'keyword_rank':
        FUNC[param_string[1]](param_string[0],
                              param_string[2],
                              param_string[3])
    elif param_string[0] in 'top_ten':
        FUNC[param_string[0]](param_string[1], param_string[2])
    else:
        FUNC[param_string[0]](param_string[1])


def backend_loop():
    seo = SeoScrapy()
    global FUNC
    FUNC = {'dead_link': seo.dead_link, 'server_info': seo.server_info,
            'web_info': seo.web_info, 'get_alexa': seo.get_alexa,
            'get_include': seo.get_include, 'get_weight': seo.get_weight,
            # 'keyword_rank': seo.keyword_rank, 'top_ten': seo.top_ten
            }

    # single test
    # seo.dead_link("www.iplaysoft.com")
    # seo.web_info("www.iplaysoft.com")
    # seo.get_weight("www.iplaysoft.com")
    # seo.get_alexa("www.iplaysoft.com")
    # seo.get_include("www.iplaysoft.com")
    # seo.server_info("www.iplaysoft.com")
    # seo.top_ten("baidu", keyword="异次元")
    # seo.keyword_rank("www.jianshu.com", "baidu", "简书")
    # seo.friend_link("www.iplaysoft.com")

    while True:
        if config['redis'].exists(QUEUE_NAME) is False:
            time.sleep(3)
            continue
        request_li = config['redis'].lrange(QUEUE_NAME, 0, -1)
        task_li = []
        for request in request_li:
            task_li.append(gevent.spawn(run_forever, request))
        gevent.joinall(task_li)
