# coding: utf-8
#

import json
import os
import subprocess
import sys
from subprocess import PIPE
from typing import Union

from logzero import logger

class JsonrpcConsoleServer():
    __instance = None

    @classmethod
    def get_singleton(cls):
        if cls.__instance is None:
            logger.info("create singleton process")
            cls.__instance = JsonrpcConsoleServer()
        return cls.__instance

    def __init__(self):
        self._p = self._start_jsonrpc_server()

    def _start_jsonrpc_server(self):
        curdir = os.path.dirname(os.path.abspath(__file__))
        rpcserver_path = os.path.join(curdir, "./jsonrpc-server.py")
        p = subprocess.Popen([sys.executable, "-u", rpcserver_path],
                             bufsize=1,
                             stdout=PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True)
        return p

    def read_response(self) -> dict:
        """
        Returns example:
            {"output": "hello world\n"}
            {"ready": true}
            {"finished": true}
        """
        return json.loads(self._p.stdout.readline())

    def call(self, method: str, params: Union[list, dict]):
        self._p.stdin.write(
            json.dumps({
                "jsonrpc": "2.0",
                "method": method,
                "params": params
            }))
    


if __name__ == "__main__":
    s = JsonrpcConsoleServer.get_singleton()
    s = JsonrpcConsoleServer.get_singleton()
