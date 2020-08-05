# coding: utf-8
# 
import asyncio
import json
import logging
import os
import re
import sys
import signal
import subprocess
import threading
from typing import Any

import tornado.iostream
import tornado.queues
import tornado.websocket
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.process import Subprocess

logger = logging.getLogger("weditor")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = os.name == "nt"


class WinAsyncSubprocess(object):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.io_loop = IOLoop.current()
        kwargs['bufsize'] = 0  # unbuffed
        kwargs['stdin'] = subprocess.PIPE
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.STDOUT

        self.proc = subprocess.Popen(*args, **kwargs)
        self.pid = self.proc.pid

        # https://www.tornadoweb.org/en/stable/queues.html
        self._qout = tornado.queues.Queue()
        self._qexit = tornado.queues.Queue()
        threading.Thread(name="async-subprocess",
                         target=self._drain,
                         daemon=True).start()

    def _drain(self):
        logger.info("Started drain subprocess stdout in thread")
        for line in iter(self.proc.stdout.readline, b''):
            self.io_loop.add_callback(self._qout.put, line)
        self.io_loop.add_callback(self._qout.put, None)
        logger.info("windows process stdout closed")
        self.io_loop.add_callback(self._qexit.put, self.proc.wait())

    async def wait_for_exit(self, raise_error=True):
        """ Ignore raise_error """
        exit_code = await self._qexit.get()
        return exit_code

    async def readline(self) -> bytes:
        ret = await self._qout.get()
        if ret is None:
            raise IOError("subprocess stdout closed")
        return ret

    async def stdin_write(self, data: bytes):
        return self.proc.stdin.write(data)


class PosixAsyncSubprocess(Subprocess):
    async def readline(self) -> bytes:
        return await self.stdout.read_until(b"\n")

    async def stdin_write(self, data: bytes):
        return await self.stdin.write(data)


class PythonShellHandler(tornado.websocket.WebSocketHandler):
    async def prepare(self):
        """
        Refs:
            https://www.tornadoweb.org/en/stable/process.html#tornado.process.Subprocess
            https://www.tornadoweb.org/en/stable/iostream.html#tornado.iostream.IOStream
        """
        AsyncSubprocess = WinAsyncSubprocess if IS_WINDOWS else PosixAsyncSubprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = "utf-8"
        self.__process = AsyncSubprocess(
            [sys.executable, "-u",
             os.path.join(ROOT_DIR, "../ipyshell-console.py")],
            env=env,
            stdin=Subprocess.STREAM,
            stdout=Subprocess.STREAM,
            stderr=subprocess.STDOUT)
        # self.__process = Subprocess([sys.executable, "-u", os.path.join(ROOT_DIR, "ipyshell.py")],
        #     # bufsize=1, #universal_newlines=True,
        #     stdin=Subprocess.STREAM,
        #     stdout=Subprocess.STREAM)
        IOLoop.current().add_callback(self.sync_process_output)

    async def kill_process(self):
        self.__process.proc.kill()
        ret = await self.__process.wait_for_exit(raise_error=False)
        logger.info("process quited with code %d", ret)

    async def _readline_decoded(self) -> str:
        line = await self.__process.readline()
        return line.decode("utf-8").rstrip()

    async def sync_process_output(self):
        try:
            while True:
                line = await self._readline_decoded()
                if not line:
                    logger.warning("proc-stdout read empty line")
                    break
                fields = line.split(":", 1)
                if len(fields) != 2:
                    continue
                cmdx, value = fields
                if cmdx == "LNO":
                    self.write2({"method": "gotoLine", "value": int(value)})
                elif cmdx == "DBG":
                    logger.debug("DBG: %s", value)
                    # self.write2({"method": "output", "value": "- "+value})
                elif cmdx == "WRT":
                    # here value is json_encoded string
                    self.write2({
                        "method": "output",
                        "value": json.loads(value)
                    })
                elif cmdx == "EOF":
                    logger.debug(
                        "finished running code block, time used %.1fs",
                        int(value) / 1000)
                    self.write2({"method": "finish", "value": int(value)})
                else:
                    # self.write2({"method": "output", "value": line +"\n"})
                    logger.warning("Unsupported output line: %s", line)
        except (tornado.iostream.StreamClosedError, IOError):
            pass
        finally:
            logger.debug("sync process output stopped")
            # code may never goes here
            #ret = await self.__process.wait_for_exit(raise_error=False)
            #logger.info("process exit with code %d", ret)
            #self.__process = None

    def send_keyboard_interrupt(self):
        if IS_WINDOWS:  # Windows
            # On windows, it's not working with the following code
            # - p.send_signal(signal.SIGINT)
            # - os.kill(p.pid, signal.CTRL_C_EVENT)
            # - subprocess.call(["taskkill", "/PID", str(p.pid)])
            # But the following command works find
            pid = self.__process.pid
            import ctypes
            k = ctypes.windll.kernel32

            k.FreeConsole()  # Don't understand
            k.AttachConsole(pid)
            k.SetConsoleCtrlHandler(
                None, True)  # Disable Ctrl-C handling for our program
            k.GenerateConsoleCtrlEvent(signal.CTRL_C_EVENT, 0)  # SIGINT

            # Re-enable Ctrl-C handling or any subsequently started
            # programs will inherit the disabled state.
            k.SetConsoleCtrlHandler(None, False)
        else:
            self.__process.proc.send_signal(
                signal.SIGINT)  # Linux is so simple

    async def open(self):
        logger.debug("websocket opened")
        logger.info("create process pid: %d", self.__process.pid)
        # self.write2({"method": "resetContent", "value": INIT_CODE})
        # self.write2({"method": "gotoLine", "value": 1})
        # await gen.sleep(.1)

    def write2(self, data):
        self.write_message(json.dumps(data))

    def _adjust_code(self, code: str):
        """ fix indent error, remove all line spaces """
        prefixs = re.findall(r"^\s*", code, re.M)
        space_len = min([len(pre) for pre in prefixs])
        lines = code.splitlines(keepends=True)
        return ''.join([line[space_len:] for line in lines])

    async def on_message(self, message):
        # print("Receive:", message)
        data = json.loads(message)
        method, value = data['method'], data.get('value')
        if method == 'input':
            code = self._adjust_code(value)
            code = json.dumps(code) + "\n"
            logger.debug("send to proc: %s", code.rstrip())
            await self.__process.stdin_write(code.encode('utf-8'))
        elif method == "keyboardInterrupt":
            self.send_keyboard_interrupt()
        elif method == "restartKernel":
            await self.kill_process()
            await self.prepare()
            self.write2({"method": "restarted"})
        else:
            logger.warning("Unknown received message: %s", data)

    def on_close(self):
        logger.warning("websocket closed")
        IOLoop.current().add_callback(self.kill_process)
