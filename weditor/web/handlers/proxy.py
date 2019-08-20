# coding: utf-8
#

import os
import hashlib
import tornado.httpclient
from logzero import logger

from .page import BaseHandler


class StaticProxyHandler(BaseHandler):
    http_client = tornado.httpclient.AsyncHTTPClient()

    async def get(self, urlpath: str):
        print(self.request.remote_ip)
        logger.debug("path: %s", urlpath)
        m = hashlib.md5()
        m.update(urlpath.encode())

        _, ext = os.path.splitext(urlpath)
        cache_path = os.path.join("cache", m.hexdigest() + ext)
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                logger.debug("use cache assets: https://%s", urlpath)
                self.write(f.read())
                return

        response = await self.http_client.fetch("https://" + urlpath)
        if not os.path.isdir("cache"):
            os.makedirs("cache")
        self.write(response.body)
        with open(cache_path, 'wb') as f:
            f.write(response.body)
