#! /usr/bin/env python
#-*- encoding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import os
import platform
import time
import json
import hashlib
import argparse
import signal
import base64
import webbrowser
import traceback
from io import BytesIO

import atx
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.escape
from tornado.escape import json_encode
from tornado.log import enable_pretty_logging
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor   # `pip install futures` for python2

try:
    import subprocess32 as subprocess
    from subprocess32 import PIPE
except:
    import subprocess
    from subprocess import PIPE

from weditor import uidumplib


__version__ = '0.0.2'

try:
    enable_pretty_logging()
except:
    pass

__dir__ = os.path.dirname(os.path.abspath(__file__))
__devices = {}

def get_device(serial):
    return atx.connect(None if serial == 'default' else serial)
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
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, PUT, DELETE, OPTIONS')

    def options(self, *args):
        self.set_status(204) # no body
        self.finish()


class VersionHandler(BaseHandler):
    def get(self):
        self.write({
            'name': __version__,
        })


class DeviceScreenshotHandler(BaseHandler):
    def get(self, serial):
        print("SN", serial)
        try:
            d = get_device(serial)
            buffer = BytesIO()
            d.screenshot().save(buffer, format='JPEG')
            b64data = base64.b64encode(buffer.getvalue())
            # with open('bg.jpg', 'rb') as f:

            # b64data = base64.b64encode(f.read())
            self.write({
                "type": "jpeg",
                "encoding": "base64",
                "data": b64data.decode('utf-8'),
            })
        except EnvironmentError as e:
            traceback.print_exc()
            self.set_status(430, "Environment Error")
            self.write({
                "description": str(e)
            })


class FileHandler(BaseHandler):
    def get_file(self, path):
        _real = virt2real(path)
        self.write({
            'type': 'file',
            'size': os.path.getsize(_real),
            'name': os.path.basename(path),
            'path': path,
            'content': read_file_content(_real),
            'sha': sha_file(_real),
        })

    def get_dir(self, path):
        _real = virt2real(path)
        files = os.listdir(_real) # TODO
        rets = []
        for name in files:
            _path = os.path.join(_real, name)
            if os.path.isfile(name):
                rets.append({
                    'type': 'file',
                    'name': name,
                    'path': os.path.join(path, name),
                    'size': os.path.getsize(_path),
                    'sha': sha_file(_path),
                })
            else:
                rets.append({
                    'type': 'dir',
                    'size': 0,
                    'name': name,
                    'path': _path,
                })
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json_encode(rets))

    def get(self, path):
        _real = virt2real(path)
        if os.path.isfile(_real):
            self.get_file(path)
        elif os.path.isdir(_real):
            self.get_dir(path)
        else:
            self.set_status(404)
            self.write({
                'description': 'file not exists'
            })

    def put(self, path):
        data = tornado.escape.json_decode(self.request.body)
        content = data.get('content')
        _real = virt2real(path)
        _dir = os.path.dirname(_real)
        if not os.path.isdir(_dir):
            os.makedirs(_dir)
        if os.path.isfile(_real):
            sha = sha_file(_real)
            if sha != data.get('sha'):
                self.set_status(422, 'Unprocessable Entity')
                self.write({
                    'description': 'file sha not match',
                })
                return
            write_file_content(_real, content)
            self.set_status(200)
        else:
            write_file_content(_real, content)
            self.set_status(201)
        self.write({
            'content': {
                'type': 'file',
                'name': os.path.basename(path),
                'path': path,
                'sha': sha_file(_real),
                'size': len(content),
            }
        })  

    def post(self, path):
        pass

    def delete(self, path):
        _real = virt2real(path)
        data = tornado.escape.json_decode(self.request.body)
        if not os.path.isfile(_real):
            self.set_status(404)
            self.write({
                'description': 'file not exists'
            })
            return
        # check sha
        sha = sha_file(_real)
        if not data or data.get('sha') != sha:
            self.set_status(422, 'Unprocessable Entity')
            self.write({
                'description': 'file sha not match'
            })
            return
        # delete file
        try:
            os.remove(_real)
            self.write({
                'content': None,
                'description': 'successfully deleted file',
            })
        except (IOError, WindowsError) as e:
            self.set_status(500)
            self.write({
                'description': 'file deleted error: {}'.format(e),
            })


class MainHandler(BaseHandler):
    def get(self):
        self.write("Hello")
        # self.render('index.html')

    def post(self):
        self.write("Good")


class DeviceUIViewHandler(BaseHandler):
    def get(self, serial):
        try:
            d = get_device(serial)
            self.write({
                'nodes': uidumplib.get_uiview(d)
            })
        except EnvironmentError as e:
            traceback.print_exc()
            self.set_status(430, "Environment Error")
            self.write({
                "description": str(e)
            })


class BuildWSHandler(tornado.websocket.WebSocketHandler):
    executor = ThreadPoolExecutor(max_workers=4)
    # proc = None

    def open(self):
        print("Websocket opened")
        self.proc = None

    def check_origin(self, origin):
        return True

    @run_on_executor
    @tornado.gen.coroutine
    def _run(self, device_url, code):
        try:
            print("DEBUG: run code", code)
            # read, write = os.pipe()
            # os.write(write, code)
            # os.close(write)
            env = os.environ.copy()
            env['UIAUTOMATOR_DEBUG'] = 'true'
            if device_url:
                env['ATX_CONNECT_URL'] = device_url.encode('utf-8')
            start_time = time.time()
            self.proc = subprocess.Popen(["python", "-u"],
                env=env, stdout=PIPE, stderr=subprocess.STDOUT, stdin=PIPE, bufsize=1)
            self.proc.stdin.write(code)
            self.proc.stdin.close()
            for line in iter(self.proc.stdout.readline, b''):
                print("recv subprocess:", repr(line))
                if line is None:
                    break
                self.write_message({"buffer": line.decode('utf-8')})
            exit_code = self.proc.wait()
            duration = time.time() - start_time
            self.write_message({
                "buffer": "",
                "result": {"exitCode": exit_code, "duration": int(duration)*1000}
            })
            self.close()
        except Exception:
            traceback.print_exc()

    # oper: "stop"
    # code: "print ('hello')"
    @tornado.gen.coroutine
    def on_message(self, message):
        jdata = json.loads(message)
        if self.proc is None:
            code = jdata['content']
            device_url = jdata.get('deviceUrl')
            yield self._run(device_url, code.encode('utf-8'))
        else:
            self.proc.terminate()
            # on Windows, kill is alais of terminate()
            if platform.system() == 'Windows':
                return
            yield tornado.gen.sleep(2)
            if self.poll():
                return
            print("Force to kill")
            self.proc.kill()

    def on_close(self):
        print("Websocket closed")


def make_app(settings={}):
    # REST API REFERENCE
    # https://developer.github.com/v3/repos/contents/
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/v1/version", VersionHandler),
        (r"/api/v1/contents/([^/]*)", FileHandler),
        (r"/api/v1/devices/([^/]+)/screenshot", DeviceScreenshotHandler),
        (r"/api/v1/devices/([^/]+)/uiview", DeviceUIViewHandler),
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
    if is_closing:
        # clean up here
        tornado.ioloop.IOLoop.instance().stop()
        print('exit success')


def run_web(debug=False):
    application = make_app({
        'static_path': os.path.join(__dir__, 'static'),
        'template_path': os.path.join(__dir__, 'static'),
        'debug': debug,
    })
    port = 17310
    print('listen port', port)
    signal.signal(signal.SIGINT, signal_handler)
    application.listen(port)
    tornado.ioloop.PeriodicCallback(try_exit, 100).start() 
    tornado.ioloop.IOLoop.instance().start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-q', '--quiet', action='store_true', help='quite mode, no open new browser')
    ap.add_argument('-d', '--debug', action='store_true', help='open debug mode')
    ap.add_argument('port', nargs='?', default=17310, help='local listen port for weditor')

    args = ap.parse_args()
    open_browser = not args.quiet

    if open_browser:
        # webbrowser.open(url, new=2)
        webbrowser.open('http://atx.open.netease.com', new=2)
    if args.debug:
        import uiautomator
        uiautomator.DEBUG = True
    run_web(args.debug)


if __name__ == '__main__':
    main()
