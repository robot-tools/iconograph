#!/usr/bin/python3

import argparse
import json
from http import server
import socket
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


class HTTPServer6(server.HTTPServer):
  address_family = socket.AF_INET6


class CertServer(object):

  def __init__(self, listen_host, listen_port, server_key, server_cert, ca_cert):

    class RequestHandler(server.BaseHTTPRequestHandler):
      def do_POST(self):
        print('Request from: [%s]:%d' % (self.client_address[0], self.client_address[1]))
        peer_cert = json.dumps(dict(x[0] for x in self.request.getpeercert()['subject']), sort_keys=True)
        print('Client cert:\n\t%s' % peer_cert.replace('\n', '\n\t'))
        size = int(self.headers['Content-Length'])

        # XXX

    self._httpd = HTTPServer6((listen_host, listen_port), RequestHandler)
    self._httpd.socket = ssl.wrap_socket(
        self._httpd.socket,
        keyfile=server_key,
        certfile=server_cert,
        ca_certs=ca_cert,
        server_side=True,
        cert_reqs=ssl.CERT_REQUIRED,
        ssl_version=ssl.PROTOCOL_TLSv1_2)
    self._httpd.socket.settimeout(5.0)

  def Serve(self):
    self._httpd.serve_forever()


def main():
  server = CertServer(
      FLAGS.listen_host,
      FLAGS.listen_port,
      FLAGS.server_key,
      FLAGS.server_cert,
      FLAGS.ca_cert)
  server.Serve()


if __name__ == '__main__':
  main()
