# encoding=utf-8
"""Constants"""
from kits.utils import get_time

# BUFSIZE = 1024 * 8
QUEUE_NAME = "request_queue"
RETOBJ = {
    "status": {
        "msg": "Query.... Please wait",
        "code": 10000,
        "time": get_time()
    },
    "info": {},
    "list": {}
}

ENGINE = {
    'baidu': {
        'base_url': 'http://www.baidu.com/s?wd=',
        'rstring': '百度为您找到相关结果约(.*?)个',
        'content_xpath': '//div[contains(@class, "c-container")]',
        'title_xpath': './descendant::h3[contains(@class,"t")]/a[@target="_blank"]',
        'url_xpath': './descendant::h3[contains(@class, "t")]/a[@target="_blank"]/@href',
        'desc_xpath': './descendant::div[@class="c-abstract" or contains(@class, "c-span-last")]'},
    'sogou': {
        'base_url': 'https://www.sogou.com/web?query=',
        'rstring': '//*[@id="scd_num"]/text()',
        'content_xpath': '//div[@class="results"]/div',
        'title_xpath': './descendant::h3[@class="pt" or @class="vrTitle" or @class="vrt"]/a',
        'url_xpath': './descendant::h3[@class="pt" or @class="vrTitle" or @class="vrt"]/a/@href',
        'desc_xpath': './descendant::p[@class="str_info" or @class="str-text-info"]|div[@class="ft" \
        or @class="str-text-info" or @class="div-p2"]'},
    '360': {
        'base_url': 'http://www.so.com/s?q=',
        'rstring': '找到相关结果约(.*?)个',
        'content_xpath': '//ul[@id="m-result"]/li',
        'title_xpath': './descendant::h3[contains(@class, "title")]/a[@target="_blank"]',
        'url_xpath': './descendant::h3[contains(@class, "title")]/a[@target="_blank"]/@href',
        'desc_xpath': './descendant::*[contains(@class, "res-desc") or \
        contains(@class, "res-comm-con") or contains(@class, "res-rich")]'}}

HEADERS = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 \
    (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,ja;q=0.2',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1'}

COOKIES = {
    'ABTEST': '8|1480486710|v17', 'IPLOC': 'CN3301',
    'SUV': '00022B8973C7A1E9583E6F378BBF2990', 'pgv_pvi': '6522359808',
    'CXID': 'E956BE05F59EE72F925850993B6EDEE3', 'sw_uuid': '2757471428',
    'sg_uuid': '1914649634',
    'ad': '@Z4MSZllll2Y5f@3lllllVPydTkllllltDWPfyllll9lllllRklll5@@@@@@@@@@',
    'SUID': '0B25797D556C860A580095E0000ACAF9',
    'SNUID': 'AE7F60E6D9DF99663127B35BDAB0F736', 'sct': '24',
    'ld': 's5n52lllll2Y5uDTlllllVPFvoZllllltDWPfyllll9lllll9llll5@@@@@@@@@@',
    'browerV': '3', 'osV': '2', 'sst0': '888'}
