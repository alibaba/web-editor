# coding: utf-8
#
# JSONRPC 2.0 protocol https://wiki.geekdream.com/Specification/json-rpc_2.0.html
#

import json
import os
import subprocess
import sys
import time
import traceback
from pprint import pprint

import uiautomator2
import wda

_globals = {
    "os": os,
    "sys": sys,
    "time": time,
    "uiautomator2": uiautomator2,
    "u2": uiautomator2
}

MAGIC = "--IM-SEPARATOR--"


def sleep(seconds):
    print("Wow")
    time.sleep(seconds)
    print("End")


__cached_devices = {}


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


def run_device_code(device_id: str, code: str):
    is_eval = True
    compiled_code = None
    try:
        compiled_code = compile(code, "<string>", "eval")
    except SyntaxError:
        is_eval = False
        compiled_code = compile(code, "<string>", "exec")

    try:
        _globals.update({"d": get_device(device_id)})
        if is_eval:
            ret = eval(code, _globals)
            print(">>> " + repr(ret))
        else:
            exec(compiled_code, _globals)
    except:
        traceback.print_exc()


def _handle_input(line: str, methods: dict):
    data = json.loads(line)
    assert data['jsonrpc'] == '2.0'
    method_name = data["method"]
    if method_name not in methods:
        raise TypeError("method not implemented", method_name)
    params = data.get("params", [])
    method = methods[method_name]
    if isinstance(params, list):
        ret = method(*params)
    elif isinstance(params, dict):
        ret = method(**params)
    else:
        raise TypeError("invalid params, only list or dict if accepted",
                        params)
    print(">>> " + repr(ret))


class FakeOutput(object):
    def __init__(self):
        self._fakeout = self  #StringBuffer()  #io.StringIO()

    def write(self, data):
        self.write_json({"output": data})

    def write_json(self, data: dict):
        self.sys_stdout.write(json.dumps(data) + "\n")
        # self.sys_stdout.flush()

    def __enter__(self):
        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr
        sys.stdout = self._fakeout
        sys.stderr = self._fakeout
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr


def main():
    methods = {
        "run_device_code": run_device_code,
        "pow": pow,
        "add": lambda a, b: a + b,
    }
    with FakeOutput() as c:
        c.write_json({"ready": True})

        for line in sys.stdin:
            _handle_input(line, methods)
            # print(MAGIC)
            c.write_json({"finished": True})

    c.write_json({"quit": True})


# {"jsonrpc": "2.0", "method": "pow", "params": [2, 5]}
# {"jsonrpc": "2.0", "method": "run_device_code", "params": ["android:", "d.info"]}

if __name__ == "__main__":
    main()
