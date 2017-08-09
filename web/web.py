# coding: utf-8

import os

import tornado.ioloop
import tornado.web
import tornado.httpserver
from tornado.log import enable_pretty_logging
from tornado.options import define, options


enable_pretty_logging()
define('debug', type=bool, default=False, help='Open debug mode')
define('port', default=6800, help='Listen port')


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


def make_app(**settings):
    settings['template_path'] = 'templates'
    settings['static_path'] = 'static'
    settings['cookie_secret'] = 'SECRET:_'+os.environ.get("SECRET", "")
    settings['login_url'] = '/login'
    return tornado.web.Application([
        (r"/", MainHandler),
    ], **settings)


if __name__ == '__main__':
    options.parse_command_line()
    app = make_app(debug=options.debug)
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    http_server.listen(options.port)
    print("Listen on port {}".format(options.port))
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print("Try to stop server")
        tornado.ioloop.IOLoop.instance().stop()
