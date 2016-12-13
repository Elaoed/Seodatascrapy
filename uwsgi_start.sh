#!/bin/bash

uwsgi --ini uwsgi.ini --wsgi-file aceptReq.py &
python seoScrapy.py &
