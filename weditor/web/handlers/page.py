# coding: utf-8
#

import base64
import io
import json
import os
import math
import traceback
import aiofiles
import time
import tornado
from logzero import logger
from PIL import Image
from tornado.escape import json_decode

from ..utils import current_ip

from ..device import connect_device, get_device
from ..version import __version__

pathjoin = os.path.join


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "*")
        self.set_header("Access-Control-Allow-Credentials",
                        "true")  # allow cookie
        self.set_header('Access-Control-Allow-Methods',
                        'POST, GET, PUT, DELETE, OPTIONS')

    def options(self, *args):
        self.set_status(204)  # no body
        self.finish()

    def check_origin(self, origin):
        """ allow cors request """
        return True


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


class DeviceConnectHandler(BaseHandler):
    def post(self):
        platform = self.get_argument("platform").lower()
        device_url = self.get_argument("deviceUrl")

        try:
            id = platform + ":" + device_url
            d = get_device(id)
            ret = {
                "deviceId": id,
                'success': True,
            }
            if platform == "android":
                ret['deviceAddress'] = d.device.address.replace("http://", "ws://") # yapf: disable
                ret['miniCapUrl'] = "ws://" + self.request.host + "/ws/v1/minicap?deviceId=" + id
                ret['miniTouchUrl'] = "ws://" + self.request.host + "/ws/v1/minitouch?deviceId=" + id
            self.write(ret)
        except RuntimeError as e:
            self.set_status(500)
            self.write({
                "success": False,
                "description": str(e),
            })
        except Exception as e:
            logger.warning("device connect error: %s", e)
            self.set_status(500)
            self.write({
                "success": False,
                "description": traceback.format_exc(),
            })

class DeviceHierarchyHandler(BaseHandler):
    def get(self, device_id):
        d = get_device(device_id)
        self.write(d.dump_hierarchy())


class DeviceHierarchyHandlerV2(BaseHandler):
    def get(self, device_id):
        d = get_device(device_id)
        self.write(d.dump_hierarchy2())


class WidgetPreviewHandler(BaseHandler):
    def get(self, id):
        self.render("widget_preview.html", id=id)


class DeviceWidgetListHandler(BaseHandler):
    __store_dir = os.path.expanduser("~/.weditor/widgets")

    def generate_id(self):
        os.makedirs(self.__store_dir, exist_ok=True)
        names = [
            name for name in os.listdir(self.__store_dir)
            if os.path.isdir(os.path.join(self.__store_dir, name))
        ]
        return "%05d" % (len(names) + 1)

    def get(self, widget_id: str):
        data_dir = os.path.join(self.__store_dir, widget_id)
        with open(pathjoin(data_dir, "hierarchy.xml"), "r",
                  encoding="utf-8") as f:
            hierarchy = f.read()

        with open(os.path.join(data_dir, "meta.json"), "rb") as f:
            meta_info = json.load(f)
            meta_info['hierarchy'] = hierarchy
            self.write(meta_info)

    def json_parse(self, source):
        with open(source, "r", encoding="utf-8") as f:
            return json.load(f)

    def put(self, widget_id: str):
        """ update widget data """
        data = json_decode(self.request.body)
        target_dir = os.path.join(self.__store_dir, widget_id)
        with open(pathjoin(target_dir, "hierarchy.xml"), "w",
                  encoding="utf-8") as f:
            f.write(data['hierarchy'])

        # update meta
        meta_path = pathjoin(target_dir, "meta.json")
        meta = self.json_parse(meta_path)
        meta["xpath"] = data['xpath']
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(meta, indent=4, ensure_ascii=False))

        self.write({
            "success": True,
            "description": f"widget {widget_id} updated",
        })

    def post(self):
        data = json_decode(self.request.body)
        widget_id = self.generate_id()
        target_dir = os.path.join(self.__store_dir, widget_id)
        os.makedirs(target_dir, exist_ok=True)

        image_fd = io.BytesIO(base64.b64decode(data['screenshot']))
        im = Image.open(image_fd)
        im.save(pathjoin(target_dir, "screenshot.jpg"))

        lx, ly, rx, ry = bounds = data['bounds']
        im.crop(bounds).save(pathjoin(target_dir, "template.jpg"))

        cx, cy = (lx + rx) // 2, (ly + ry) // 2
        # TODO(ssx): missing offset
        # pprint(data)
        widget_data = {
            "resource_id": data["resourceId"],
            "text": data['text'],
            "description": data["description"],
            "target_size": [rx - lx, ry - ly],
            "package": data["package"],
            "activity": data["activity"],
            "class_name": data['className'],
            "rect": dict(x=lx, y=ly, width=rx-lx, height=ry-ly),
            "window_size": data['windowSize'],
            "xpath": data['xpath'],
            "target_image": {
                "size": [rx - lx, ry - ly],
                "url": f"http://localhost:17310/widgets/{widget_id}/template.jpg",
            },
            "device_image": {
                "size": im.size,
                "url": f"http://localhost:17310/widgets/{widget_id}/screenshot.jpg",
            },
            # "hierarchy": data['hierarchy'],
        } # yapf: disable

        with open(pathjoin(target_dir, "meta.json"), "w",
                  encoding="utf-8") as f:
            json.dump(widget_data, f, ensure_ascii=False, indent=4)

        with open(pathjoin(target_dir, "hierarchy.xml"), "w",
                  encoding="utf-8") as f:
            f.write(data['hierarchy'])

        self.write({
            "success": True,
            "id": widget_id,
            "note": data['text'] or data['description'],  # 备注
            "data": widget_data,
        })


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
            self.set_status(500, "Environment Error")
            self.write({"description": str(e)})
        except RuntimeError as e:
            self.set_status(500)  # Gone
            self.write({"description": traceback.format_exc()})

class DeviceScreenrecordHandler(BaseHandler):
    root = None
    def initialize(self, path: str) -> None:
        self.root = path
    def get(self, serial, action):
        d = get_device(serial)
        if action == "start":
            self.write(d.start_screenrecord(self.root))
        elif action == "stop":
            self.write(d.stop_screenrecord(self.root))
        else:
            self.set_status(404)
            self.write("action " + action + " invalid")

class DeviceSizeHandler(BaseHandler):
    def post(self):
        serial = self.get_argument("serial")
        logger.info("Serial: %s", serial)
        d = get_device(serial)
        w, h = d.device.window_size()
        self.write({"width": w, "height": h})

class DeviceTouchHandler(BaseHandler):
    def post(self):
        serial = self.get_argument("serial")
        action = self.get_argument("action")
        x = int(self.get_argument("x"))
        y = int(self.get_argument("y"))
        logger.info("Serial: %s", serial)
        d = get_device(serial)
        if action == 'down':
            d.device.touch.down(x, y)
        elif action == 'move':
            d.device.touch.move(x, y)
        elif action == 'up':
            d.device.touch.up(x, y)
        else:
            d.device.click(x, y)
        self.write({"success": True})

class DevicePressHandler(BaseHandler):
    def post(self):
        serial = self.get_argument("serial")
        key = self.get_argument("key")
        logger.info("Serial: %s", serial)
        d = get_device(serial)
        ret = d.device.keyevent(key)
        self.write({"ret": ret})

def formatsize(size: int):
    if size < 1024:
        return str(size)
    
    logger.info("size = %d", size)
    i = math.floor(math.log(size, 1024))
    logger.info("i = %d", i)
    unit = "BKMGT"
    return "{:.3f}".format(size / math.pow(1024, i)) + unit[i]

def filetime(item):
    return item["time"]

class ListHandler(BaseHandler):
    root = None
    def initialize(self, path: str) -> None:
        self.root = path
    def get(self):
        files = []
        for name in os.listdir(self.root):
            st = os.stat(os.path.join(self.root, name))
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
            files.append({"name": name, "size": st.st_size, "fsize": formatsize(st.st_size), "time": t})
        files.sort(key = filetime, reverse = True)
        self.render("list.html", files=files)
