# coding: utf-8
#

import uuid
import json
import os
import signal
import subprocess
import sys
from subprocess import PIPE
from typing import Union

from logzero import logger


class ConsoleKernel():
    __instance = {}

    @classmethod
    def get_singleton(cls, name='default'):
        if cls.__instance.get(name) is None:
            logger.info("create singleton process")
            cls.__instance[name] = ConsoleKernel()
        return cls.__instance[name]

    def __init__(self):
        self._p = None
        self._magic = "M:" + str(uuid.uuid4()).replace("-", "") + "=="
        self._start_jsonrpc_server()

    def _start_jsonrpc_server(self):
        curdir = os.path.dirname(os.path.abspath(__file__))
        rpcserver_path = os.path.join(curdir, "./jsonrpc_server.py")
        self._p = subprocess.Popen([sys.executable, "-u", rpcserver_path, "--magic", self._magic],
                                   bufsize=1,
                                   stdin=PIPE,
                                   stdout=PIPE,
                                   stderr=subprocess.STDOUT,
                                   universal_newlines=True) # yapf: disable
        data, finished = self.read_response()
        assert finished == True, 'jsonrpc_server started failed'

    def send_interrupt(self):
        if not self.is_closed():
            self._p.send_signal(signal.SIGINT)

    def is_closed(self):
        return self._p.poll() is not None

    def read_response(self) -> tuple:
        """
        Returns:
            tuple: (output, finished: bool)
        """
        
        line = self._p.stdout.readline()
        logger.info("READ: %r", line)
        if self.is_closed():
            self._p = None
            return line, True
        if line.rstrip().endswith(self._magic):
            return line.rstrip()[:-len(self._magic)], True
        return line, False

    def read_until_finished(self):
        output = ""
        while True:
            data, finished = self.read_response()
            output += data
            if finished:
                break
        return output

    def call(self, method: str, params: Union[list, dict]):
        send_data = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        })
        logger.info("SEND: %s", send_data)
        self._p.stdin.write(send_data + "\n")

    def call_output(self, method: str, params: Union[list, dict]) -> str:
        self.call(method, params)
        return self.read_until_finished()


if __name__ == "__main__":
    s = ConsoleKernel.get_singleton()
    s = ConsoleKernel.get_singleton()
    s.call("pow", [2, 5])
    output = s.read_until_finished()
    print("Output:", output)
    s.call("run_device_code", ["android:", "d.info"])
    output = s.read_until_finished()
    print("Output:", output)

    output = s.call_output("run_device_code", ["android:", "d.info"])
    print("Output:", output)