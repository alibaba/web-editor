#! /usr/bin/env python
# -*- encoding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import platform
import time
import json
import hashlib
import argparse
import signal
import base64
import webbrowser
import traceback
import uuid
from io import BytesIO

import six
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.escape
from tornado import gen
from tornado.escape import json_encode
from tornado.log import enable_pretty_logging
from tornado.concurrent import run_on_executor
# `pip install futures` for python2
from concurrent.futures import ThreadPoolExecutor

try:
    import Queue as queue
except:
    import queue

try:
    import subprocess32 as subprocess
    from subprocess32 import PIPE
except:
    import subprocess
    from subprocess import PIPE

from weditor import uidumplib


__version__ = '0.0.3'

try:
    enable_pretty_logging()
except:
    pass

__dir__ = os.path.dirname(os.path.abspath(__file__))
cached_devices = {}
gqueue = queue.Queue()


def tostr(s, encoding='utf-8'):
    if six.PY2:
        return s.encode(encoding)
    if isinstance(s, bytes):
        return s.decode(encoding)
    return s


def get_device(id):
    return cached_devices.get(id)
    # return atx.connect(None if serial in ['-', 'default'] else serial)
    # d = __devices.get(serial)
    # if d:
    #     return d
    # __devices[serial] = atx.connect(None if serial == 'default' else serial)
    # return __devices.get(serial)


def read_file_content(filename, default=''):
    if not os.path.isfile(filename):
        return default
    with open(filename, 'rb') as f:
        return f.read()


def write_file_content(filename, content):
    with open(filename, 'w') as f:
        f.write(content.encode('utf-8'))


def sha_file(path):
    sha = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha.update(data)
    return sha.hexdigest()


def virt2real(path):
    return os.path.join(os.getcwd(), path.lstrip('/'))


def real2virt(path):
    return os.path.relpath(path, os.getcwd()).replace('\\', '/')


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
            'name': __version__,
        }
        self.write(ret)


class DeviceScreenshotHandler(BaseHandler):
    def get(self, serial):
        print("SN", serial)
        try:
            d = get_device(serial)
            buffer = BytesIO()
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
            self.write({
                "description": str(e)
            })


class MainHandler(BaseHandler):
    def get(self):
        self.render("index.html")


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
                                         env=env, stdout=PIPE, stderr=subprocess.STDOUT, stdin=PIPE)
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
                "result": {"exitCode": exit_code, "duration": int(duration)*1000}
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
            try:
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
            except WindowsError as e:
                print("Kill error on windows " + str(e))

    def on_close(self):
        print("Websocket closed")


class DeviceConnectHandler(BaseHandler):
    def post(self):
        platform = self.get_argument("platform").lower()
        device_url = self.get_argument("deviceUrl")
        id = str(uuid.uuid4())
        try:
            if platform == 'android':
                import uiautomator2 as u2
                d = u2.connect(device_url)
                d.platform = 'android'
                cached_devices[id] = d
            elif platform == 'ios':
                import atx
                d = atx.connect(device_url)
                cached_devices[id] = d
            else:
                import neco
                d = neco.connect(device_url or 'localhost')
                cached_devices[id] = d
        except Exception as e:
            self.set_status(430, "Connect Error")
            self.write({
                "success": False,
                "description": traceback.format_exc().encode('utf-8'),
            })
        else:
            self.write({
                "deviceId": id,
                'success': True,
            })


class DeviceHierarchyHandler(BaseHandler):
    def get(self, device_id):
        d = get_device(device_id)
        if d.platform == 'ios':
            self.write(uidumplib.get_ios_hierarchy(d))
        elif d.platform == 'android':
            self.write(uidumplib.get_android_hierarchy(d))
        elif d.platform == 'neco':
            dump = d.dump_hierarchy()
            self.write(dump)
        else:
            self.write("Unknown platform")


class DeviceCodeDebugHandler(BaseHandler):
    def post(self, device_id):
        d = get_device(device_id)
        code = self.get_argument('code')
        start = time.time()
        buffer = BytesIO()
        sys.stdout = buffer
        sys.stderr = buffer

        is_eval = True
        compiled_code = None
        try:
            compiled_code = compile(code, "<string>", "eval")
        except SyntaxError:
            is_eval = False
            compiled_code = compile(code, "<string>", "exec")
        try:
            if is_eval:
                ret = eval(code, {'d': d})
                buffer.write((">>> " + repr(ret) + "\n").encode('utf-8'))
            else:
                exec(compiled_code, {'d': d})
        except:
            buffer.write(traceback.format_exc().encode('utf-8'))
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
        self.write({
            "success": True,
            "duration": int((time.time()-start)*1000),
            "content": buffer.getvalue().decode('utf-8'),
        })


def make_app(settings={}):
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/v1/version", VersionHandler),
        (r"/api/v1/connect", DeviceConnectHandler),
        (r"/api/v1/devices/([^/]+)/screenshot", DeviceScreenshotHandler),
        (r"/api/v1/devices/([^/]+)/hierarchy", DeviceHierarchyHandler),
        (r"/api/v1/devices/([^/]+)/exec", DeviceCodeDebugHandler),
        (r"/ws/v1/build", BuildWSHandler),
    ], **settings)
    return application


is_closing = False


def signal_handler(signum, frame):
    global is_closing
    print('exiting...')
    is_closing = True


def try_exit():
    global is_closing
    if is_closing:  # clean up here
        tornado.ioloop.IOLoop.instance().stop()
        print('exit success')


@gen.coroutine
def consume_queue():
    # print("Consume task queue")
    while True:
        try:
            (wself, value) = gqueue.get_nowait()
            wself.write_message(value)
        except queue.Empty:
            yield gen.sleep(.2)
        except Exception as e:
            print("Error in consume: " + str(e))
            yield gen.sleep(.5)


def run_web(debug=False, port=17310):
    application = make_app({
        'static_path': os.path.join(__dir__, 'static'),
        'template_path': os.path.join(__dir__, 'templates'),
        'debug': debug,
    })
    print('listen port', port)
    signal.signal(signal.SIGINT, signal_handler)
    application.listen(port)
    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().add_callback(consume_queue)
    tornado.ioloop.IOLoop.instance().start()


def create_shortcut():
    import os
    import sys
    if os.name != 'nt':
        sys.exit("Only valid in Windows")

    import pythoncom
    from win32com.shell import shell
    from win32com.shell import shellcon
    # Refs
    # - https://github.com/pearu/iocbio/blob/master/installer/utils.py
    # - https://blog.csdn.net/thundor/article/details/5968581
    ilist = shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_DESKTOP)
    dtpath = shell.SHGetPathFromIDList(ilist).decode('utf-8')

    shortcut = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None,
        pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    launch_path = sys.executable
    shortcut.SetPath(launch_path)
    shortcut.SetArguments("-m weditor")
    shortcut.SetDescription(launch_path)
    shortcut.SetIconLocation(sys.executable, 0)
    shortcut.QueryInterface(
        pythoncom.IID_IPersistFile).Save(dtpath + "\\WEditor.lnk", 0)
    print("Shortcut created. " + dtpath + "\\WEditor.lnk")


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('-q', '--quiet', action='store_true',
                    help='quite mode, no open new browser')
    ap.add_argument('--debug', action='store_true',
                    help='open debug mode')
    ap.add_argument('--shortcut', action='store_true',
                    help='create shortcut in desktop')
    ap.add_argument('-p', '--port', type=int, default=17310,
                    help='local listen port for weditor')

    args = ap.parse_args()
    if args.shortcut:
        create_shortcut()
        return

    open_browser = not args.quiet

    if open_browser:
        # webbrowser.open(url, new=2)
        webbrowser.open('http://localhost:'+str(args.port), new=2)
    run_web(args.debug, args.port)


if __name__ == '__main__':
    main()
