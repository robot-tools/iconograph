#!/usr/bin/python3

import argparse
import json
import os
import pyinotify
import ssl
import sys
import threading
from ws4py import websocket
from ws4py.server import geventserver
from ws4py.server import wsgiutils


parser = argparse.ArgumentParser(description='iconograph https_server')
parser.add_argument(
    '--ca-cert',
    dest='ca_cert',
    action='store',
    required=True)
parser.add_argument(
    '--image-path',
    dest='image_path',
    action='store',
    required=True)
parser.add_argument(
    '--image-type',
    dest='image_types',
    action='append',
    required=True)
parser.add_argument(
    '--listen-host',
    dest='listen_host',
    action='store',
    default='::')
parser.add_argument(
    '--listen-port',
    dest='listen_port',
    type=int,
    action='store',
    default=443)
parser.add_argument(
    '--server-key',
    dest='server_key',
    action='store',
    required=True)
parser.add_argument(
    '--server-cert',
    dest='server_cert',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def GetWebSocketHandler(websockets):
  class WebSocketHandler(websocket.WebSocket):
    def opened(self):
      websockets.add(self)

    def closed(self, code, reason=None):
      websockets.remove(self)

  return WebSocketHandler


class INotifyHandler(pyinotify.ProcessEvent):
  def __init__(self, websockets):
    self._websockets = websockets

  def process_IN_MOVED_TO(self, event):
    if event.name != 'manifest.json':
      return
    image_type = os.path.basename(event.path)
    for websocket in self._websockets:
      websocket.send(json.dumps({
        'type': 'new_manifest',
        'data': {
          'image_type': image_type,
        },
      }), False)


class HTTPRequestHandler(object):

  _MIME_TYPES = {
    '.iso': 'application/octet-stream',
    '.json': 'application/json',
  }
  _BLOCK_SIZE = 2 ** 16

  def __init__(self, image_path, image_types, websockets):
    self._image_path = image_path
    self._image_types = image_types
    inner_handler = GetWebSocketHandler(websockets)
    self._websocket_handler = wsgiutils.WebSocketWSGIApplication(handler_cls=inner_handler)

  def __call__(self, env, start_response):
    path = env['PATH_INFO']
    if path.startswith('/image/'):
      image_type, image_name = path[7:].split('/', 1)
      return self._ServeImageFile(start_response, image_type, image_name)
    elif path == '/ws':
      return self._websocket_handler(env, start_response)

    start_response('404 Not found', [('Content-Type', 'text/plain')])
    return [b'Not found']

  def _MIMEType(self, file_name):
    for suffix, mime_type in self._MIME_TYPES.items():
      if file_name.endswith(suffix):
        return mime_type

  def _ServeImageFile(self, start_response, image_type, image_name):
    # Sanitize inputs
    image_type = os.path.basename(image_type)
    image_name = os.path.basename(image_name)
    assert not image_type.startswith('.')
    assert not image_name.startswith('.')
    assert image_type in self._image_types

    file_path = os.path.join(self._image_path, image_type, image_name)
    try:
      with open(file_path, 'rb') as fh:
        start_response('200 OK', [('Content-Type', self._MIMEType(image_name))])
        while True:
          block = fh.read(self._BLOCK_SIZE)
          if len(block) == 0:
            break
          yield block
    except FileNotFoundError:
      start_response('404 Not found')
      return []

    return


class Server(object):

  def __init__(self, listen_host, listen_port, server_key, server_cert, ca_cert, image_path, image_types):
    websockets = set()

    wm = pyinotify.WatchManager()
    inotify_handler = INotifyHandler(websockets)
    self._notifier = pyinotify.Notifier(wm, inotify_handler)
    for image_type in image_types:
      type_path = os.path.join(image_path, image_type)
      wm.add_watch(type_path, pyinotify.IN_MOVED_TO)

    http_handler = HTTPRequestHandler(image_path, image_types, websockets)
    self._httpd = geventserver.WSGIServer(
        (listen_host, listen_port),
        http_handler,
        keyfile=server_key,
        certfile=server_cert,
        ca_certs=ca_cert,
        cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLSv1_2)

  def Serve(self):
    self._notify_thread = threading.Thread(target=self._notifier.loop)
    self._notify_thread.daemon = True
    self._notify_thread.start()
    self._httpd.serve_forever()


def main():
  server = Server(
      FLAGS.listen_host,
      FLAGS.listen_port,
      FLAGS.server_key,
      FLAGS.server_cert,
      FLAGS.ca_cert,
      FLAGS.image_path,
      set(FLAGS.image_types))
  server.Serve()


if __name__ == '__main__':
  main()
