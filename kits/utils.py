# encoding=utf-8
"""utility functions"""
import time
import re

def blfilter(domain, url):
    return (False, True)[domain in url]


def get_time(timestamp=time.time()):
    return time.strftime("%Y-%m-%d %X", time.localtime(timestamp))

def if_url(url):
    # re_str = "^(?=^.{3,255}$)([a-zA-Z0-9]+(-[a-zA-Z0-9]+)*\.){1,7}[a-zA-Z0-9]{2,6}$"
    if re.match('^(http[s]?\:\/\/)?(\w+[-]?\w+\.){1,7}\w+$', url):
        return True
    return False
