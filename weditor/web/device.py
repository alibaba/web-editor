# coding: utf-8
#

import abc
import os
import time

import uiautomator2 as u2
import wda
from logzero import logger
from PIL import Image

from . import uidumplib
from tornado.ioloop import PeriodicCallback

class DeviceMeta(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def screenshot(self) -> Image.Image:
        pass

    def dump_hierarchy(self) -> str:
        pass

    @abc.abstractproperty
    def device(self):
        pass


class _AndroidDevice(DeviceMeta):
    isScreenRecord = False
    screenRecordTime = None
    screenrecordTimeout = None
    
    def __init__(self, device_url):
        self._d = u2.connect(device_url)

    def start_screenrecord(self, path):
        r = self._d.http.post("/screenrecord")
        logcat = 0
        dmesg = 0
        if r.status_code == 200:
            t = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time()))
            stdout = os.path.join(path, "logcat-" + t + ".log")
            stderr = os.path.join(path, "logcat-" + t + ".err")
            logcat = os.system("daemon -rU --name logcat --stdout " + stdout + " --stderr " + stderr + " -- adb logcat")
            stdout = os.path.join(path, "dmesg-" + t + ".log")
            stderr = os.path.join(path, "dmesg-" + t + ".err")
            dmesg = os.system("daemon -rU --name dmesg --stdout " + stdout + " --stderr " + stderr + " -- adb shell 'echo \"while dmesg -c;do echo ;done\" | su'")
            self.isScreenRecord = True
            self.screenRecordTime = t
            
            def do_timeout():
                self.stop_screenrecord(path)
            
            self.screenrecordTimeout = PeriodicCallback(do_timeout, 30 * 60 * 1000)
            self.screenrecordTimeout.start()
        
        return {"status": r.status_code == 200, "message": str(r.text).strip(), "logcat": logcat, "dmesg": dmesg}

    def stop_screenrecord(self, path):
        if self.screenrecordTimeout is not None:
            self.screenrecordTimeout.stop()
            self.screenrecordTimeout = None
        
        r = self._d.http.put("/screenrecord")
        if r.status_code == 200:
            if self.isScreenRecord:
                t = self.screenRecordTime
                self.isScreenRecord = False
            else:
                t = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time()))
            
            videos = r.json()["videos"]
            if len(videos) > 0:
                files = []
                cmdargs = ["rm", "-f"]
                
                for f in videos:
                    name = "screenrecord-" + t + "-" + os.path.basename(f)
                    self._d.pull(f, os.path.join(path, name))
                    cmdargs.append(f)
                    files.append(name)
                r = self._d.shell(cmdargs)
                logcat = os.system("daemon --stop --name logcat")
                dmesg = os.system("daemon --stop --name dmesg")
                return {"status": True, "files": files, "rmCode": r.exit_code, "output": r.output, "logcat": logcat, "dmesg": dmesg}
            else:
                return {"status": True, "files": [], "exitCode": 0, "output": ""}
        else:
            return {"status": False, "message": str(r.text).strip()}

    def screenshot(self):
        return self._d.screenshot()

    def dump_hierarchy(self):
        return uidumplib.get_android_hierarchy(self._d)

    def dump_hierarchy2(self):
        current = self._d.app_current()
        page_xml = self._d.dump_hierarchy(pretty=True)
        page_json = uidumplib.android_hierarchy_to_json(
            page_xml.encode('utf-8'))
        return {
            "xmlHierarchy": page_xml,
            "jsonHierarchy": page_json,
            "activity": current['activity'],
            "packageName": current['package'],
            "windowSize": self._d.window_size(),
        }

    @property
    def device(self):
        return self._d


class _AppleDevice(DeviceMeta):
    def __init__(self, device_url):
        logger.info("ios connect: %s", device_url)
        if device_url == "":
            c = wda.USBClient()
        else:
            c = wda.Client(device_url)
        self._client = c
        self.__scale = c.scale

    def screenshot(self):
        try:
            return self._client.screenshot(format='pillow')
        except:
            import tidevice
            return tidevice.Device().screenshot()

    def dump_hierarchy(self):
        return uidumplib.get_ios_hierarchy(self._client, self.__scale)

    def dump_hierarchy2(self):
        return {
            "jsonHierarchy":
            uidumplib.get_ios_hierarchy(self._client, self.__scale),
            "windowSize":
            self._client.window_size(),
        }

    @property
    def device(self):
        return self._client


cached_devices = {}

def connect_device(platform, device_url):
    """
    Returns:
        deviceId (string)
    """
    device_id = platform + ":" + device_url
    if platform == 'android':
        d = _AndroidDevice(device_url)
    elif platform == 'ios':
        d = _AppleDevice(device_url)
    else:
        raise ValueError("Unknown platform", platform)

    cached_devices[device_id] = d
    return device_id


def get_device(id):
    d = cached_devices.get(id)
    if d is None:
        platform, uri = id.split(":", maxsplit=1)
        connect_device(platform, uri)
    return cached_devices[id]

def stop_device(path):
    for d in cached_devices.values():
        d.stop_screenrecord(path)
        d.device.reset_uiautomator('Stop Device')
