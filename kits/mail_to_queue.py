from redispool import _redispool
from log import get_logger


def monitor_mail(title, content):

    __mail = {
        u'from':         u'service@newdun.com',
        u'fromName':     u'Newdun',
        u'template':     u'monitor'
    }

    __email_to = ['renxiaopeng@newdun.com']
    __mail[u'to'] = u','.join(__email_to)
    __xsmtp = {u'to': __email_to}

    __warning = content
    __xsmtp[u'sub'] = {u'%warning%': [__warning]*len(__email_to)}

    __mail[u'xsmtp'] = __xsmtp
    __mail[u'subject'] = title

    __MAIL_QUEUE.put(str(__mail))


monitor_mail(
    'Wocao~ this is delphi', "Really Nice to see you how have you been")
