# coding: utf-8
#

import os
from typing import Optional

import tornado.httpclient
import tornado.web


class StaticProxyHandler(tornado.web.StaticFileHandler):
    CACHE_DIR = os.path.expanduser("~/.weditor/cache")
    http_client = tornado.httpclient.AsyncHTTPClient()

    def initialize(self, path: str = None, default_filename: str = None) -> None:
        self.root = path if path else os.path.expanduser("~")
        self.default_filename = default_filename

    def validate_absolute_path(self, root: str, absolute_path: str) -> Optional[str]:
        """
        Override in order to fix error "xxxx is not in root static directory"
        """
        if not os.path.isfile(absolute_path):
            raise tornado.web.HTTPError(403, "%s is not a file", self.path)
        return absolute_path

    async def download_file(self, path: str) -> str:
        """
        Returns:
            download file path
        
        Raises:
            tornado.web.HTTPError
        """
        cache_path = os.path.join(self.settings.get("static_path"), "cdn_libraries", path)
        if os.path.exists(cache_path):
            return cache_path
        
        if not self.settings['debug']:
            # cache to local directory
            # self.settings.get("static_path"), "cdn_libraries", path)
            cache_path = os.path.join(self.CACHE_DIR, path)

            if os.path.exists(cache_path):
                return cache_path
        
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        request = tornado.httpclient.HTTPRequest(
            url="https://"+path,
            method="GET",
            validate_cert=False  # fix certificate validate error
        )

        response = await self.http_client.fetch(request, raise_error=False)
        if response.code != 200:
            raise tornado.web.HTTPError(404)
        
        with open(cache_path, 'wb') as f:
            f.write(response.body)
        
        return cache_path

    async def get(self, path: str, include_body: bool = True) -> None:
        abspath = await self.download_file(path)
        await super().get(abspath, include_body)
