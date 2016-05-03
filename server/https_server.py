#!/usr/bin/python3

import argparse
import os
from gevent import pywsgi
import ssl


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


class ImageRequestHandler(object):

  _MIME_TYPES = {
    '.iso': 'application/octet-stream',
    '.json': 'application/json',
  }
  _BLOCK_SIZE = 2 ** 16

  def __init__(self, image_path):
    self._image_path = image_path

  def __call__(self, env, start_response):
    path = env['PATH_INFO']
    if path.startswith('/image/'):
      image_type, image_name = path[7:].split('/', 1)
      return self._ServeImageFile(start_response, image_type, image_name)

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


class ImageServer(object):

  def __init__(self, listen_host, listen_port, server_key, server_cert, ca_cert, image_path):

    self._handler = ImageRequestHandler(image_path)

    self._httpd = pywsgi.WSGIServer(
        (listen_host, listen_port),
        self._handler,
        keyfile=server_key,
        certfile=server_cert,
        ca_certs=ca_cert,
        cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLSv1_2)

  def Serve(self):
    self._httpd.serve_forever()


def main():
  server = ImageServer(
      FLAGS.listen_host,
      FLAGS.listen_port,
      FLAGS.server_key,
      FLAGS.server_cert,
      FLAGS.ca_cert,
      FLAGS.image_path)
  server.Serve()


if __name__ == '__main__':
  main()
