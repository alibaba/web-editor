#! /usr/bin/env python
# -*- encoding: utf-8 -*-

from __future__ import absolute_import, print_function

import argparse
import base64
import hashlib
import io
import json
import os
import platform
import queue
import signal
import socket
import subprocess
import sys
import time
import traceback
import uuid
import webbrowser
# `pip install futures` for python2
from concurrent.futures import ThreadPoolExecutor
from subprocess import PIPE

import requests
import six
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.websocket
from logzero import logger
from tornado import gen
from tornado.concurrent import run_on_executor
from tornado.escape import json_encode
from tornado.log import enable_pretty_logging

from .web.handlers.page import (BaseHandler, BuildWSHandler,
                                DeviceCodeDebugHandler, DeviceConnectHandler,
                                DeviceHierarchyHandler,
                                DeviceScreenshotHandler, MainHandler,
                                VersionHandler)
from .web.handlers.proxy import StaticProxyHandler
from .web.utils import current_ip, tostr

enable_pretty_logging()

__dir__ = os.path.dirname(os.path.abspath(__file__))

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


def make_app(settings={}):
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/v1/version", VersionHandler),
        (r"/api/v1/connect", DeviceConnectHandler),
        (r"/api/v1/devices/([^/]+)/screenshot", DeviceScreenshotHandler),
        (r"/api/v1/devices/([^/]+)/hierarchy", DeviceHierarchyHandler),
        (r"/api/v1/devices/([^/]+)/exec", DeviceCodeDebugHandler),
        # cache static assets
        (r"/proxy/https/(.*)", StaticProxyHandler),
        (r"/unpkg.com/.*", StaticProxyHandler),
        (r"/cdn.jsdelivr.net/.*", StaticProxyHandler),
        (r"/ws/v1/build", BuildWSHandler),
    ], **settings)
    return application


def check_running(port: int):
    """
    sys.exit if already running
    """
    try:
        r = requests.get(f"http://localhost:{port}/api/v1/version", timeout=2.0)
        if r.status_code == 200:
            version = r.json().get("version", "dev")
            sys.exit(f"Another weditor({version}) is already running")
    except requests.exceptions.ConnectionError:
        pass
    except Exception as e:
        print("Unknown error: %r" % e)


def run_web(debug=False, port=17310, open_browser=False):
    check_running(port)

    if open_browser:
        # webbrowser.open(url, new=2)
        webbrowser.open(f'http://localhost:{port}', new=2)

    application = make_app({
        'static_path': os.path.join(__dir__, 'static'),
        'template_path': os.path.join(__dir__, 'templates'),
        'debug': debug,
    })
    print('listening on http://%s:%d' % (current_ip(), port))
    if debug:
        logger.info("enable debug mode")
    signal.signal(signal.SIGINT, signal_handler)
    application.listen(port)
    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    # tornado.ioloop.IOLoop.instance().add_callback(consume_queue)
    tornado.ioloop.IOLoop.instance().start()


def create_shortcut():
    if os.name != 'nt':
        sys.exit("Only valid in Windows")

    import pythoncom  # pyint: disable=import-error
    from win32com.shell import shell
    from win32com.shell import shellcon
    # Refs
    # - https://github.com/pearu/iocbio/blob/master/installer/utils.py
    # - https://blog.csdn.net/thundor/article/details/5968581
    ilist = shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_DESKTOP)
    dtpath = shell.SHGetPathFromIDList(ilist).decode('utf-8')

    shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None,
                                          pythoncom.CLSCTX_INPROC_SERVER,
                                          shell.IID_IShellLink)
    launch_path = sys.executable
    shortcut.SetPath(launch_path)
    shortcut.SetArguments("-m weditor")
    shortcut.SetDescription(launch_path)
    shortcut.SetIconLocation(sys.executable, 0)
    shortcut.QueryInterface(pythoncom.IID_IPersistFile).Save(
        dtpath + "\\WEditor.lnk", 0)
    print("Shortcut created. " + dtpath + "\\WEditor.lnk")


def main():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('-q',
                    '--quiet',
                    action='store_true',
                    help='quite mode, no open new browser')
    ap.add_argument('-d',
                    '--debug',
                    action='store_true',
                    help='open debug mode')
    ap.add_argument('--shortcut',
                    action='store_true',
                    help='create shortcut in desktop')
    ap.add_argument('-p',
                    '--port',
                    type=int,
                    default=17310,
                    help='local listen port for weditor')

    args = ap.parse_args()
    if args.shortcut:
        create_shortcut()
        return

    open_browser = not args.quiet
    run_web(args.debug, args.port, open_browser)


if __name__ == '__main__':
    main()
