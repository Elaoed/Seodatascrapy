# encoding=utf-8
"""Main module of dealing with seo scrapy request"""
import json
import os
import copy
import re
import gzip
from functools import wraps

import requests
import gevent
from gevent import monkey
from bs4 import BeautifulSoup
from lxml import etree
import xml.etree.cElementTree as ET

from kits.log import get_logger
from kits.utils import blfilter
from kits.utils import gget
from kits.redispool import Redispool

from kits.constants import ENGINE
from kits.constants import COOKIES
from kits.constants import HEADERS
from kits.constants import RETOBJ
from kits.constants import QUEUE_NAME
from kits.deal_domain import get_response
from kits.deal_domain import divide_article
from kits.my_exception import MyException


monkey.patch_socket()

BufSize = 1024 * 8
config = {
    'redis': Redispool(queue=QUEUE_NAME),
    'logger': get_logger("seoScrapy")
}

class SeoScrapy(object):
    """SEO data Scrapy"""

    def __init__(self):
        self.url = ''
        self.pro_type = ''
        self.res = ''
        self.include = None
        self.pre_size = ''
        self.post_size = ''
        self.gRate = ''
        self.response = None

    def web_info(self, domain):

        url = get_url(domain)
        res = requests.get(url, headers=HEADERS, cookies=COOKIES, timeout=5)
        jump = re.match("<meta http-equiv=\"Refresh\" content=\"0; url=(.*?)\"/>", res.content)
        if jump:
            new_url = jump.group(1)
            res = requests.get(new_url, headers=HEADERS, cookies=COOKIES, timeout=5)
        selector = etree.HTML(res.content)
        desc = selector.xpath('//*[@name="description"]/@content')
        title = selector.xpath('//title/text()')
        keywords = selector.xpath('//*[@name="keywords"]/@content')
        keywords = "" if not keywords else keywords[0]

        for i in divide_article(res.content):
            keywords += " %s " % i[0].encode()

        web_info = dict()
        web_info['title'] = "" if not title else title[0]
        web_info['keywords'] = keywords
        web_info['description'] = "" if not desc else desc[0]

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = domain + ' in web_info good'
        retobj['status']['code'] = 1000
        retobj['info'] = web_info
        return retobj

    def friend_link(self, domain):
        """Get friend links of given website"""
        html = self.response.text
        selector = etree.HTML(html)
        urls = selector.xpath('//a/@href')
        contents = []
        exclude_li = []
        black_list = ['http://weibo.com', 'https://twitter.com/', 'gov.cn',
                      'http://szcert.ebs.org.cn/', 'shang.qq.com', 'ss.knet.cn', domain]
        exclude_suffix = ['jpg', 'png', 'pdf', 'exe', 'rar', 'mp3']

        for url in urls:
            if url not in contents and re.match('^http[s]?', url) and \
                    url[-3:] not in exclude_suffix and url.split('/')[2] not in exclude_li:
                if not any([blfilter(_domain, url) for _domain in black_list]):
                    contents.append(url)
                    exclude_li.append(url.split('/')[2])

        frilink = dict()
        for link in contents:
            frilink[link] = -1

        return frilink

    def dead_link(self, domain):

        self.response = get_response(domain)
        if not self.response:
            raise MyException("Has no Response object returned", 10030)

        link_status = self.friend_link(domain)

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = "part of dead link"
        retobj['status']['code'] = 10020
        retobj['info'] = link_status

        config['redis'].set('dead_link:::' + domain, json.dumps(retobj))

        urls = list(link_status.keys())
        res = gget(urls, timeout=3)
        for index, url in enumerate(res):
            if not url:
                link_status[urls[index]] = 1
            elif 200 <= url.status_code < 400:
                link_status[urls[index]] = 0
            else:
                link_status[urls[index]] = 1

        retobj['status']['msg'] = domain + " get DeadLink good"
        retobj['status']['code'] = 1000
        retobj['info'] = link_status
        return retobj

    def get_weight(self, domain):

        appkey = '618e7a46808573be2401596582de62fb'
        baidu_weight = {
            "To": "0",
            "From": "0",
            "Weight": "0"
        }
        code = 10010
        res = requests.post('http://op.juhe.cn/baiduWeight/index',
                            data={'key': appkey, 'domain': domain},
                            timeout=5)

        if res.status_code is 200 and res.content:
            jres = json.loads(res.content)
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
        return retobj

    def get_include(self, domain):

        html = requests.get('https://www.baidu.com/s?wd=site:%s' + domain,
                            headers=HEADERS,
                            timeout=5).content
        res = re.search('找到相关结果数约(.*?)个|该网站共有 (.*?) 个网页被百度收录',
                        html,
                        re.M | re.S)

        if res:
            if res.group(1):
                baidu = res.group(1)
            else:
                baidu = re.search('>(.*?)<', res.group(2))
                baidu = baidu.group(1)
        else:
            baidu = 0

        html = requests.get('https://www.so.com/s?q=site:' + domain,
                            timeout=5).content

        res2 = re.search('找到相关结果约(.*?)个', html)
        _360 = 0 if res2 is None else res2.group(1)

        html = requests.get('https://www.sogou.com/web?query=site:%s' % domain,
                            cookies=COOKIES,
                            timeout=5).content
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
                nurl = re.search("URL='(.*?)'",
                                 requests.get(url,
                                              timeout=2,
                                              headers=HEADERS,
                                              cookies=COOKIES)
                                 .content)
                nurl = nurl.group(1) if nurl else None
            return nurl
        except requests.ReadTimeout:
            config['logger'].error("%s Timeout", url)
            return None
        except Exception:
            return None

    def engine_data(self, div, count, search_engine, content):
        config['logger'].debug('%d before get url', count)
        url = self.get_url(div, search_engine)
        config['logger'].debug('%d after get url', count)
        if not url:
            return
        title = div.xpath(ENGINE[search_engine]['title_xpath'])
        title = title[0].xpath('string(.)').strip() if title else ""
        desc = div.xpath(ENGINE[search_engine]['desc_xpath'])
        desc = desc[0].xpath('string(.)') if desc else ""

        content.append(
            {'title': title, 'desc': desc, 'url': url, 'count': count})
        config['logger'].debug('%d finish append', count)

    def top_ten(self, search_engine, keyword):
        """Get top ten"""
        base_url = ENGINE[search_engine]['base_url'] + keyword
        res = requests.get(base_url).content
        content = []
        selector = etree.HTML(res)
        divs = selector.xpath(ENGINE[search_engine]['content_xpath'])[:10]
        threads = []
        for index, div in enumerate(divs):
            threads.append(gevent.spawn(self.engine_data, div, index, search_engine, content))
        gevent.joinall(threads)

        content = sorted(content, key=lambda info: info['count'])

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = 'engine:%s, keyword:%s, good' % (search_engine, keyword)
        retobj['list'] = content

        return retobj

    def get_rank(self, domain, base_url, search_engine):
        config['logger'].info('Using search engine:%s', search_engine)
        try:
            res = requests.get(base_url,
                               headers=HEADERS,
                               cookies=COOKIES,
                               timeout=5).content

        except requests.exceptions.ConnectionError:
            config['logger'].warning(base_url + " Connection error")
            raise MyException(base_url + " can not be parsed", 10004)
        selector = etree.HTML(res)
        if search_engine in 'sogou':
            try:
                total = selector.xpath(ENGINE[search_engine]['rstring'])[0]
            except IndexError:
                config['logger'].error('IndexError scrapy Sogou too fast')
                raise MyException('IndexError scrapy Sogou too fast', 10005)
        else:
            total = re.search(
                ENGINE[search_engine]['rstring'], res).group(1)
        total = int(total.replace(',', ''))
        total = 5 if total > 50 else (
            (total / 10 + 1) if total % 10 > 0 else total / 10)

        count = 0
        divs = []
        for i in range(total):
            if i:
                if search_engine in 'baidu':
                    nurl = base_url + '&pn=%d' % (i * 10)
                elif search_engine in '360':
                    nurl = base_url + "&pn=%d" % (i + 1)
                else:
                    nurl = base_url + "&page=%d" % (i + 1)
                res = requests.get(
                    nurl, headers=HEADERS, cookies=COOKIES, timeout=5).content
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
                except requests.ReadTimeout:
                    return
                except Exception:
                    return

            elif search_engine in ['360', 'sogou']:
                try:
                    nurl = re.search(
                        "URL='(.*?)'", requests.get(url, timeout=5).content)
                except requests.ReadTimeout:
                    return
                except Exception:
                    return
                if nurl:
                    url = nurl.group(1)
            if domain in url:
                content.append(count)

        threads = []
        content = []
        for index, div in enumerate(divs):
            threads.append(gevent.spawn(check_rank, domain, div, index, search_engine, content))
        gevent.joinall(threads)

        count = sorted(content)[0] if content else '50+'
        return count

    def keyword_rank(self, domain, search_engine, keyword):

        count = self.get_rank(domain,
                              ENGINE[search_engine]['base_url'] + keyword,
                              search_engine)

        retobj = copy.deepcopy(RETOBJ)
        retobj['status']['msg'] = domain + ' keyword get good'
        retobj['info'] = {'count': count}

        return retobj

    def server_info(self, domain):

        url = get_url(domain)
        res = requests.get(url,
                           timeout=5,
                           headers=HEADERS,
                           cookies=COOKIES)

        if res.status_code is not 200:
            msg = ''.join([url, "'s return httpcode is ", str(res.status_code)])
            config['logger'].warning(msg)
            raise MyException(url + " server_info", 10004)

        # content = deal_encoding(res.content, res.encoding)
        content = res.text
        protocal_type = url.split(':')[0]
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
        pre_size, post_size, grate = self.get_web_source(content, url)

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

        return retobj

    def get_web_source(self, content, url):

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
            try:
                source_file = requests.get(link, timeout=2).content
                with open(filename, 'wb') as file_handler:
                    file_handler.write(source_file)
            except requests.ConnectionError:
                return
            except requests.ReadTimeout:
                return

        threads = []
        for index, url in enumerate(useful_links):
            threads.append(gevent.spawn(downSourceFile, url, index, before_filepath))
        gevent.joinall(threads)

        with open(os.path.join(before_filepath, 'index.html'), 'wb') as file_handler:
            file_handler.write(content)

        pre_size = self.get_size(before_filepath) / 1000
        post_size = self.gzip_file(before_filepath, gzip_filepath) / 1000

        self.del_Files(before_filepath)
        self.del_Files(gzip_filepath)

        try:
            grate = str(
                (pre_size - post_size) * 100 / pre_size) + '%'
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
        for root, _, files in os.walk(dirpath):
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
        for _, _, files in os.walk(before_filepath):
            for file_name in files:
                gzip_fd = gzip.open(os.path.join(gzip_filepath, file_name), 'wb')
                gzip_fd.write(open(os.path.join(before_filepath, file_name)).read())
                gzip_fd.close()
        return self.get_size(gzip_filepath)


def try_except(orig_func):

    @wraps(orig_func)
    def wrapper(req):
        retobj = None

        try:
            retobj = orig_func(req)
        except requests.ReadTimeout:
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

        except MyException as err_msg:
            config['logger'].error(err_msg.msg)
            retobj = copy.deepcopy(RETOBJ)
            retobj['status']['msg'] = err_msg.msg
            retobj['status']['code'] = err_msg.code

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

        2.dead_link(url)                        dead_link:::domain  -> json

        3.keyword_rank(url, keyword)            domain:::keyword_rank:::search_engine:::keyword
                                                search_engine:::keyword -> json

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


if __name__ == "__main__":
    seo = SeoScrapy()
    FUNC = {'keyword_rank': seo.keyword_rank, 'dead_link': seo.dead_link,
            'web_info': seo.web_info, 'get_alexa': seo.get_alexa,
            'get_include': seo.get_include, 'get_weight': seo.get_weight,
            'server_info': seo.server_info, 'top_ten': seo.top_ten}
    seo.dead_link("www.iplaysoft.com")

    # while True:
    #     if config['redis'].exists(QUEUE_NAME) is False:
    #         time.sleep(3)
    #         continue
    #     request_li = config['redis'].lrange(QUEUE_NAME, 0, -1)
    #     task_li = []
    #     for request in request_li:
    #         task_li.append(gevent.spawn(run_forever, request))
    #     gevent.joinall(task_li)
