# encoding=utf-8


class MyException(Exception):

    def __init__(self, msg, code=1, key=''):
        super(MyException, self).__init__(self)
        self.code = code
        self.msg = msg
        self.key = key

    def __repr__(self):
        return self.msg

    def __str__(self):
        return self.msg
