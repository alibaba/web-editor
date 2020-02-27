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

from .web.handlers.page import (
    BaseHandler, BuildWSHandler, DeviceCodeDebugHandler, DeviceConnectHandler,
    DeviceHierarchyHandler, DeviceHierarchyHandlerV2, DeviceScreenshotHandler,
    DeviceWidgetListHandler, MainHandler, VersionHandler, WidgetPreviewHandler)
from .web.handlers.proxy import StaticProxyHandler
from .web.utils import current_ip, tostr
from .web.version import __version__

enable_pretty_logging()

__dir__ = os.path.dirname(os.path.abspath(__file__))

is_closing = False


def signal_handler(signum, frame):
    global is_closing
    print('exiting...')
    is_closing = True


def stop_server():
    tornado.ioloop.IOLoop.instance().stop()


def try_exit():
    global is_closing
    if is_closing:  # clean up here
        stop_server()
        logger.info('exit success')


class QuitHandler(BaseHandler):
    def get(self):
        stop_server()
        self.write({"success": True, "description": "Successfully quited"})


class CropHandler(BaseHandler):
    def get(self):
        """ used for crop image """
        pass


def make_app(settings={}):
    application = tornado.web.Application(
        [
            (r"/", MainHandler),
            (r"/api/v1/version", VersionHandler),
            (r"/api/v1/connect", DeviceConnectHandler),
            (r"/api/v1/crop", CropHandler),
            (r"/api/v1/devices/([^/]+)/screenshot", DeviceScreenshotHandler),
            (r"/api/v1/devices/([^/]+)/hierarchy", DeviceHierarchyHandler),
            (r"/api/v1/devices/([^/]+)/exec", DeviceCodeDebugHandler),
            (r"/api/v1/devices/([^/]+)/widget", DeviceWidgetListHandler),
            (r"/api/v1/widgets", DeviceWidgetListHandler),  # add widget
            (r"/api/v1/widgets/([^/]+)", DeviceWidgetListHandler),
            # v2
            (r"/api/v2/devices/([^/]+)/hierarchy", DeviceHierarchyHandlerV2),
            # widgets
            (r"/widgets/([^/]+)", WidgetPreviewHandler),
            (r"/widgets/(.+/.+)", tornado.web.StaticFileHandler, {
                "path": "./widgets"
            }),
            # cache static assets
            (r"/(unpkg.com/.*)", StaticProxyHandler),
            (r"/(cdn.jsdelivr.net/.*)", StaticProxyHandler),
            (r"/ws/v1/build", BuildWSHandler),
            (r"/quit", QuitHandler),
        ],
        **settings)
    return application


def get_running_version(addr: str):
    """
    Returns:
        None if not running
        version string if running
    """
    try:
        r = requests.get(f"{addr}/api/v1/version",
                         timeout=2.0)
        if r.status_code == 200:
            return r.json().get("version", "dev")
    except requests.exceptions.ConnectionError:
        pass
    except Exception as e:
        print("Unknown error: %r" % e)


def run_web(debug=False, port=17310, open_browser=False, force_quit=False):
    version = get_running_version(f"http://localhost:{port}")
    if version:
        if force_quit:
            logger.info(f"quit previous weditor server (version: {version})")
            requests.get(f"http://localhost:{port}/quit")
            time.sleep(.5)
        else:
            sys.exit(f"Another weditor({version}) is already running")

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
    # yapf: disable
    ap = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("-v", "--version", action="store_true", help="show version")
    ap.add_argument('-q', '--quiet', action='store_true', help='quite mode, no open new browser')
    ap.add_argument('-d', '--debug', action='store_true', help='open debug mode')
    ap.add_argument('-p', '--port', type=int, default=17310, help='local listen port for weditor')
    ap.add_argument("-f", "--force-quit", action='store_true', help="force quit before start")
    ap.add_argument('--shortcut', action='store_true', help='create shortcut in desktop')
    args = ap.parse_args()
    # yapf: enable

    if args.version:
        print(__version__)
        return

    if args.shortcut:
        create_shortcut()
        return

    if sys.platform == 'win32' and sys.version_info[:2] == (3, 8):
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    open_browser = not args.quiet
    run_web(args.debug, args.port, open_browser, args.force_quit)


if __name__ == '__main__':
    main()
