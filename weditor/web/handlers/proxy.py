# coding: utf-8
#

import os
import hashlib
import tornado.httpclient
from logzero import logger

from .page import BaseHandler


class StaticProxyHandler(BaseHandler):
    http_client = tornado.httpclient.AsyncHTTPClient()

    async def get(self, urlpath=None):
        # print(self.request.remote_ip)
        if urlpath is None:
            urlpath = "https://"+self.request.path.lstrip("/")
        else:
            urlpath = "https://" + urlpath

        #logger.debug("path: %s", urlpath)
        m = hashlib.md5()
        m.update(urlpath.encode())

        cache_dir = os.path.expanduser("~/.weditor")
        _, ext = os.path.splitext(urlpath)
        cache_path = os.path.join(cache_dir, m.hexdigest() + ext)
        if not os.path.exists(cache_path):
            response = await self.http_client.fetch(urlpath)
            if not os.path.isdir(cache_dir):
                os.makedirs(cache_dir)

            with open(cache_path, 'wb') as f:
                f.write(response.body)

        with open(cache_path, 'rb') as f:
            #logger.debug("use cache assets: %s", urlpath)
            self.write(f.read())
