# coding: utf-8
#
# rpc python server
# example rpc client
#
# import xmlrpc.client
# s = xmlrpc.client.ServerProxy("http://localhost:17320")
# s.run_python_code("a = 1")
# print(s.run_python_code('print(a)))
#
## output: 1

import argparse
import io
import os
import signal
import sys
import time
import traceback
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

import uiautomator2

_globals = {
    "sys": "sys",
    "time": time,
    "uiautomator2": uiautomator2,
    "u2": uiautomator2
}


class StringBuffer():
    def __init__(self):
        self.encoding = 'utf-8'
        self.buf = io.BytesIO()

    def write(self, data):
        if isinstance(data, str):
            data = data.encode(self.encoding)
        self.buf.write(data)

    def getvalue(self):
        return self.buf.getvalue().decode(self.encoding)


class FakeOutput(object):
    def __init__(self):
        self._fakeout = StringBuffer()  #io.StringIO()

    @property
    def output(self):
        return self._fakeout.getvalue()

    def __enter__(self):
        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr
        sys.stdout = self._fakeout
        sys.stderr = self._fakeout
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr


__cached_devices = {}


def _connect(device_id: str):
    """
    Returns:
        (u2.Device, fixed-device-id)
    """
    platform, uri = device_id.split(":", maxsplit=1)
    if platform == "android":
        d = uiautomator2.connect(uri)
        _id = "android:" + d.serial
        return d, _id
    elif platform == "ios":
        import wda
        d = wda.Client(uri)
        return d.session(), device_id
    else:
        raise RuntimeError("unknown platform", platform)


def get_device(device_id: str):
    """
    Returns:
        u2.Device
    """
    d = __cached_devices.get(device_id)
    if d:
        return d
    d, _id = _connect(device_id)
    if device_id.startswith("android:"):
        __cached_devices[_id] = d
    return d


def run_python_code(device_id: str, code: str):
    is_eval = True
    compiled_code = None
    try:
        compiled_code = compile(code, "<string>", "eval")
    except SyntaxError:
        is_eval = False
        compiled_code = compile(code, "<string>", "exec")

    with FakeOutput() as c:
        try:
            _globals.update({"d": get_device(device_id)})
            if is_eval:
                ret = eval(code, _globals)
                print(">>> " + repr(ret))
            else:
                exec(compiled_code, _globals)
        except:
            traceback.print_exc()

    return c.output


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-p",
                        "--port",
                        type=int,
                        default=8000,
                        help="listen port")
    args = parser.parse_args()

    port = args.port
    server = SimpleXMLRPCServer(("0.0.0.0", port), allow_none=True)
    server.register_function(run_python_code)
    server.register_function(lambda: 'pong', 'ping')
    server.register_function(lambda x, y: x + y, 'add')
    server.register_function(lambda: os.kill(os.getpid(), signal.SIGTERM),
                             'quit')
    # server.register_function(_connect, "connect")
    server.register_multicall_functions()

    print(f'Serving XML-RPC on localhost port {port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")


if __name__ == "__main__":
    main()
