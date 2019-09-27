# coding: utf-8
#

import json
import os
import platform
import queue
import subprocess
import sys
import io
import base64
import time
import traceback
# `pip install futures` for python2
from concurrent.futures import ThreadPoolExecutor
from subprocess import PIPE
import six
import tornado
from tornado.concurrent import run_on_executor
from logzero import logger

from ..device import connect_device, get_device
from ..utils import tostr
from ..version import __version__


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header("Access-Control-Allow-Credentials",
                        "true")  # allow cookie
        self.set_header('Access-Control-Allow-Methods',
                        'POST, GET, PUT, DELETE, OPTIONS')

    def options(self, *args):
        self.set_status(204)  # no body
        self.finish()


class VersionHandler(BaseHandler):
    def get(self):
        ret = {
            'name': "weditor",
            'version': __version__,
        }
        self.write(ret)


class MainHandler(BaseHandler):
    def get(self):
        self.render("index.html")


gqueue = queue.Queue()


class BuildWSHandler(tornado.websocket.WebSocketHandler):
    executor = ThreadPoolExecutor(max_workers=4)

    # proc = None

    def open(self):
        print("Websocket opened")
        self.proc = None

    def check_origin(self, origin):
        return True

    @run_on_executor
    def _run(self, device_url, code):
        """
        Thanks: https://gist.github.com/mosquito/e638dded87291d313717
        """
        try:

            print("DEBUG: run code\n%s" % code)
            env = os.environ.copy()
            env['UIAUTOMATOR_DEBUG'] = 'true'
            if device_url and device_url != 'default':
                env['ATX_CONNECT_URL'] = tostr(device_url)
            start_time = time.time()

            self.proc = subprocess.Popen([sys.executable, "-u"],
                                         env=env,
                                         stdout=PIPE,
                                         stderr=subprocess.STDOUT,
                                         stdin=PIPE)
            self.proc.stdin.write(code)
            self.proc.stdin.close()

            for line in iter(self.proc.stdout.readline, b''):
                print("recv subprocess:", repr(line))
                if line is None:
                    break
                gqueue.put((self, {"buffer": line.decode('utf-8')}))
            print("Wait exit")
            exit_code = self.proc.wait()
            duration = time.time() - start_time
            ret = {
                "buffer": "",
                "result": {
                    "exitCode": exit_code,
                    "duration": int(duration) * 1000
                }
            }
            gqueue.put((self, ret))
            time.sleep(3)  # wait until write done
        except Exception:
            traceback.print_exc()

    @tornado.gen.coroutine
    def on_message(self, message):
        jdata = json.loads(message)
        if self.proc is None:
            code = jdata['content']
            device_url = jdata.get('deviceUrl')
            yield self._run(device_url, code.encode('utf-8'))
            self.close()
        else:
            self.proc.terminate()
            # on Windows, kill is alais of terminate()
            if platform.system() == 'Windows':
                return
            yield tornado.gen.sleep(0.5)
            if self.proc.poll():
                return
            yield tornado.gen.sleep(1.2)
            if self.proc.poll():
                return
            print("Force to kill")
            self.proc.kill()

    def on_close(self):
        print("Websocket closed")


class DeviceConnectHandler(BaseHandler):
    def post(self):
        platform = self.get_argument("platform").lower()
        device_url = self.get_argument("deviceUrl")

        try:
            id = connect_device(platform, device_url)
        except RuntimeError as e:
            self.set_status(410)  # 410 Gone
            self.write({
                "success": False,
                "description": str(e),
            })
        except Exception as e:
            logger.warning("device connect error: %s", e)
            self.set_status(410)  # 410 Gone
            self.write({
                "success": False,
                "description": traceback.format_exc(),
            })
        else:
            ret = {
                "deviceId": id,
                'success': True,
            }
            if platform == "android":
                ws_addr = get_device(id).device.address.replace("http://", "ws://") # yapf: disable
                ret['screenWebSocketUrl'] = ws_addr + "/minicap"
            self.write(ret)


class DeviceHierarchyHandler(BaseHandler):
    def get(self, device_id):
        d = get_device(device_id)
        self.write(d.dump_hierarchy())


class DeviceScreenshotHandler(BaseHandler):
    def get(self, serial):
        logger.info("Serial: %s", serial)
        try:
            d = get_device(serial)
            buffer = io.BytesIO()
            d.screenshot().convert("RGB").save(buffer, format='JPEG')
            b64data = base64.b64encode(buffer.getvalue())
            response = {
                "type": "jpeg",
                "encoding": "base64",
                "data": b64data.decode('utf-8'),
            }
            self.write(response)
        except EnvironmentError as e:
            traceback.print_exc()
            self.set_status(430, "Environment Error")
            self.write({"description": str(e)})
        except RuntimeError as e:
            self.set_status(410)  # Gone
            self.write({"description": traceback.print_exc()})


class StringBuffer():
    def __init__(self):
        self.encoding = 'utf-8'
        self.buf = io.BytesIO()

    def write(self, data):
        if isinstance(data, six.string_types):
            data = data.encode(self.encoding)
        self.buf.write(data)

    def getvalue(self):
        return self.buf.getvalue().decode(self.encoding)


class DeviceCodeDebugHandler(BaseHandler):
    _global = {}

    def run(self, device, code):
        buffer = StringBuffer()
        sys.stdout = buffer
        sys.stderr = buffer

        try:
            is_eval = True
            compiled_code = None
            try:
                compiled_code = compile(code, "<string>", "eval")
            except SyntaxError:
                is_eval = False
                compiled_code = compile(code, "<string>", "exec")

            self._global.update(d=device, time=time, os=os)
            if is_eval:
                ret = eval(code, self._global)
                buffer.write((">>> " + repr(ret) + "\n"))
            else:
                exec(compiled_code, self._global)
        except Exception:
            buffer.write(traceback.format_exc())
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

        return buffer.getvalue()

    def post(self, device_id):
        d = get_device(device_id)
        code = self.get_argument('code')

        start = time.time()
        output = self.run(d.device, code)

        self.write({
            "success": True,
            "duration": int((time.time() - start) * 1000),
            "content": output,
        })
