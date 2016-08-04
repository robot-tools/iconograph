#!/usr/bin/python3

import argparse
import json
import os
import pyinotify
import ssl
import subprocess
import sys
import threading
import time
import uuid
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
parser.add_argument(
    '--static-path',
    dest='static_paths',
    action='append')
parser.add_argument(
    '--exec-handler',
    dest='exec_handlers',
    action='append')
FLAGS = parser.parse_args()


class WebSockets(object):
  def __init__(self):
    self.slaves = set()
    self.masters = set()
    self.targets = {}

  def __iter__(self):
    return iter(self.slaves | self.masters)

  @staticmethod
  def Broadcast(targets, msg):
    msgstr = json.dumps(msg)
    for target in targets:
      target.send(msgstr)

  def BroadcastTargets(self):
    self.Broadcast(self.masters, {
      'type': 'targets',
      'data': {
        'targets': list(self.targets.keys()),
      },
    })


class BaseWSHandler(websocket.WebSocket):
  def opened(self, image_types):
    self.send(json.dumps({
      'type': 'image_types',
      'data': {
        'image_types': list(image_types),
      },
    }))


def GetSlaveWSHandler(image_types, websockets):

  class SlaveWSHandler(BaseWSHandler):
    _hostname = None

    def opened(self):
      super().opened(image_types)
      websockets.slaves.add(self)

    def closed(self, code, reason=None):
      websockets.slaves.remove(self)
      if self._hostname:
        del websockets.targets[self._hostname]
        websockets.BroadcastTargets()

    def received_message(self, msg):
      parsed = json.loads(str(msg))
      if parsed['type'] == 'report':
        newmsg = {
          'type': 'report',
          'id': str(uuid.uuid4()),
          'received': int(time.time()),
          'client': self.peer_address,
          'data': parsed['data'],
        }
        websockets.Broadcast(websockets.masters, newmsg)

        if 'hostname' in parsed['data']:
          self._hostname = parsed['data']['hostname']
          websockets.targets[self._hostname] = self
          websockets.BroadcastTargets()

  return SlaveWSHandler


def GetMasterWSHandler(image_types, websockets):
  class MasterWSHandler(BaseWSHandler):
    def opened(self):
      super().opened(image_types)
      websockets.masters.add(self)
      self.send(json.dumps({
        'type': 'targets',
        'data': {
          'targets': list(websockets.targets.keys()),
        },
      }))

    def closed(self, code, reason=None):
      websockets.masters.remove(self)

    def received_message(self, msg):
      parsed = json.loads(str(msg))
      if parsed['type'] == 'command':
        target = parsed['target']
        if target not in websockets.targets:
          return
        newmsg = {
          'type': 'command',
          'target': target,
          'id': str(uuid.uuid4()),
          'received': int(time.time()),
          'client': self.peer_address,
          'data': parsed['data'],
        }
        websockets.targets[target].send(json.dumps(newmsg))

  return MasterWSHandler


class INotifyHandler(pyinotify.ProcessEvent):
  def __init__(self, websockets):
    self._websockets = websockets

  def process_IN_MOVED_TO(self, event):
    if event.name != 'manifest.json':
      return
    image_type = os.path.basename(event.path)
    print('New manifest for:', image_type)
    self._websockets.Broadcast(self._websockets, {
      'type': 'new_manifest',
      'data': {
        'image_type': image_type,
      },
    })


class HTTPRequestHandler(object):

  _MIME_TYPES = {
    '.css': 'text/css',
    '.html': 'text/html',
    '.iso': 'application/octet-stream',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.tar': 'application/x-tar',
    '.woff': 'application/font-woff',
  }
  _BLOCK_SIZE = 2 ** 16

  def __init__(self, image_path, image_types, exec_handlers, static_paths, websockets):
    self._image_path = image_path
    self._image_types = image_types
    self._exec_handlers = exec_handlers
    self._static_paths = static_paths
    self._static_paths['static'] = os.path.join(os.path.dirname(sys.argv[0]), 'static')

    slave_ws_handler = GetSlaveWSHandler(image_types, websockets)
    self._slave_ws_handler = wsgiutils.WebSocketWSGIApplication(
      protocols=['iconograph-slave'],
      handler_cls=slave_ws_handler)

    master_ws_handler = GetMasterWSHandler(image_types, websockets)
    self._master_ws_handler = wsgiutils.WebSocketWSGIApplication(
      protocols=['iconograph-master'],
      handler_cls=master_ws_handler)

  def __call__(self, env, start_response):
    path = env['PATH_INFO']

    if path == '/':
      path = '/static/root.html'

    for url, file_path in self._static_paths.items():
      if path.startswith('/%s/' % url):
        file_name = path[len(url) + 2:]
        return self._ServeStaticFile(start_response, file_path, file_name)

    if path.startswith('/image/'):
      image_type, image_name = path[7:].split('/', 1)
      return self._ServeImageFile(start_response, image_type, image_name)
    elif path.startswith('/exec/'):
      method = path[6:]
      return self._ServeExec(start_response, method, env['QUERY_STRING'])
    elif path == '/ws/slave':
      return self._slave_ws_handler(env, start_response)
    elif path == '/ws/master':
      return self._master_ws_handler(env, start_response)

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
      start_response('404 Not found', [('Content-Type', 'text/plain')])
      return []

  def _ServeStaticFile(self, start_response, file_path, file_name):
    file_name = os.path.basename(file_name)
    assert not file_name.startswith('.')

    full_path = os.path.join(file_path, file_name)
    try:
      with open(full_path, 'rb') as fh:
        start_response('200 OK', [('Content-Type', self._MIMEType(file_name))])
        return [fh.read()]
    except FileNotFoundError:
      start_response('404 Not found', [('Content-Type', 'text/plain')])
      return []

  def _ServeExec(self, start_response, method, arg):
    handler = self._exec_handlers[method]
    start_response('200 OK', [])
    proc = subprocess.Popen(
        [handler, arg],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    while True:
      block = proc.stdout.read(self._BLOCK_SIZE)
      if len(block) == 0:
        break
      yield block
    proc.wait()


class Server(object):

  def __init__(self, listen_host, listen_port, server_key, server_cert, ca_cert, image_path, image_types, exec_handlers, static_paths):
    websockets = WebSockets()

    wm = pyinotify.WatchManager()
    inotify_handler = INotifyHandler(websockets)
    self._notifier = pyinotify.Notifier(wm, inotify_handler)
    for image_type in image_types:
      type_path = os.path.join(image_path, image_type)
      wm.add_watch(type_path, pyinotify.IN_MOVED_TO)

    exec_handlers = dict(x.split('=', 1) for x in (exec_handlers or []))
    static_paths = dict(x.split('=', 1) for x in (static_paths or []))
    http_handler = HTTPRequestHandler(image_path, image_types, exec_handlers, static_paths, websockets)
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
      set(FLAGS.image_types),
      FLAGS.exec_handlers,
      FLAGS.static_paths)
  server.Serve()


if __name__ == '__main__':
  main()
