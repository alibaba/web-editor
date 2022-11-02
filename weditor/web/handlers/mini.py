# coding: utf-8
#
from asyncio import Future
from logzero import logger
from weditor.web.device import get_device
from tornado.websocket import websocket_connect, WebSocketHandler

cached_devices = {}

class BaseHandler(WebSocketHandler):
    def check_origin(self, origin: str):
        return True

class ClientHandler(object):
    conn = None
    handlers = None
    strs = None
    
    def __init__(self, id: str, name: str):
        self.handlers = []
        self.strs = {}
        self.id = id + "/" + name
        d = get_device(id)
        ws_addr = d.device.address.replace("http://", "ws://") # yapf: disable
        url = ws_addr + "/" + name
        
        websocket_connect(url, callback=self.on_open, on_message_callback=self.on_message, connect_timeout=10)
        
        cached_devices[self.id] = self
    
    def on_open(self, future: Future = None):
        logger.info("client open")
        try:
            self.conn = future.result()
        except:
            self.on_close()
    
    def on_message(self, message):
        if message is None:
            self.on_close()
        else:
            # logger.debug("client message: %s", message)
            for handler in self.handlers:
                handler.write_message(message, isinstance(message, bytes))
            if isinstance(message, str) and message.__contains__(" "):
                key, val = message.split(" ", maxsplit=1)
                self.strs[key] = val
    
    def on_close(self):
        logger.info("client close")
        
        for handler in self.handlers:
            handler.close()
        
        self.handlers.clear()
        del cached_devices[self.id]
    
    def add_handler(self, handler: BaseHandler):
        self.handlers.append(handler)
        for key, val in self.strs.items():
            handler.write_message(key + " " + val)
    
    def del_handler(self, handler: BaseHandler):
        self.handlers.remove(handler)
    
    def write_message(self, message):
        if self.conn is not None:
            return self.conn.write_message(message, isinstance(message, bytes))

def get_client(id, name):
    key = id + "/" + name
    c = cached_devices.get(key)
    if c is None:
        c = ClientHandler(id, name)
    return c

class MiniCapHandler(BaseHandler):
    id = ""
    d = None
    def open(self):
        self.id = self.get_query_argument("deviceId")
        self.d = get_client(self.id, 'minicap')
        self.d.add_handler(self)
        
        logger.info("MiniCap opened: %s", self.id)

    def on_message(self, message):
        logger.info("MiniCap message: %s", message)
        self.d.write_message(message)

    def on_close(self):
        logger.info("MiniCap closed")
        self.d.del_handler(self)
        self.d = None

class MiniTouchHandler(BaseHandler):
    id = ""
    d = None
    def open(self):
        self.id = self.get_query_argument("deviceId")
        self.d = get_client(self.id, "minitouch")
        self.d.add_handler(self)
        
        logger.info("MiniTouch opened: %s", id)

    def on_message(self, message):
        logger.info("MiniTouch message: %s", message)
        self.d.write_message(message)

    def on_close(self):
        logger.info("MiniTouch closed")
        self.d.del_handler(self)
        self.d = None
