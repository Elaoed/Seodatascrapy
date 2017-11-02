# -*- coding: utf-8 -*-
"""accept request from users and make simple format check"""

import gevent
from gevent import monkey
monkey.patch_all()

from kits import initialize
from kits.create_app import app
from kits.seoscrapy import backend_loop

if __name__ == "__main__":
    initialize()
    gevent.spawn(backend_loop).start()
    app.run(host='0.0.0.0', port=3035)
