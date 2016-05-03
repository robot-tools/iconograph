#!/usr/bin/python3

import argparse
from gevent import pywsgi
import ssl


parser = argparse.ArgumentParser(description='iconograph https_server')
parser.add_argument(
    '--ca-cert',
    dest='ca_cert',
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

  def __call__(self, env, start_response):
    print(env['PATH_INFO'])
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'foo']


class ImageServer(object):

  def __init__(self, listen_host, listen_port, server_key, server_cert, ca_cert):

    self._handler = ImageRequestHandler()

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
      FLAGS.ca_cert)
  server.Serve()


if __name__ == '__main__':
  main()
