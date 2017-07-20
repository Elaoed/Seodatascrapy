# encoding=utf8

from functools import partial
import gevent
from gevent import monkey
# from gevent.pool import Pool
from requests import Session
monkey.patch_socket()

class AsyncRequest(object):
    """ Asynchronous request.
    Accept same parameters as ``Session.request`` and some additional:
    :param session: Session which will do request
    :param callback: Callback called on response.
                     Same as passing ``hooks={'response': callback}``
    """

    def __init__(self, method, url, **kwargs):

        self.method = method
        self.url = url

        self.session = kwargs.pop('session', None)
        if self.session is None:
            self.session = Session()

        #: The rest arguments for ``Session.request``
        self.kwargs = kwargs
        self.response = None

    def send(self, **kwargs):
        """
        Prepares request based on parameter passed to constructor and optional ``kwargs```.
        Then sends request and saves response to :attr:`response`
        :returns: ``Response``
        """
        merged_kwargs = {}
        merged_kwargs.update(self.kwargs)
        merged_kwargs.update(kwargs)
        try:
            self.response = self.session.request(self.method, self.url, **merged_kwargs)
        except Exception as e:
            self.exception = e
        return self

def send(r, pool=None, stream=False):
    """
    Sends the request object using the specified pool. If a pool isn't
    specified this method blocks. Pools are useful because you can specify size
    and can hence limit concurrency.
    """
    if pool is not None:
        return pool.spawn(r.send, stream=stream)
    return gevent.spawn(r.send, stream=stream)


get = partial(AsyncRequest, 'GET')
post = partial(AsyncRequest, 'POST')

def gmap(requests, stream=False, size=None, exception_handler=None, gtimeout=None):

    requests = list(requests)
    # pool = Pool(size) if size else None
    jobs = [gevent.spawn(r.send, stream=stream) for r in requests]
    gevent.joinall(jobs, timeout=gtimeout)

    ret = []

    for request in requests:
        if request.response is not None:
            ret.append(request.response)
        elif exception_handler and hasattr(request, 'exception'):
            ret.append(exception_handler(request, request.exception))
        else:
            ret.append(None)

    return ret

def request(method, url, **kwargs):
    return AsyncRequest(method, url, **kwargs)
