#!/usr/bin/python3

import argparse
import json
import socket
import time
from ws4py.client import threadedclient


parser = argparse.ArgumentParser(description='iconograph fetcher')
parser.add_argument(
    '--server',
    dest='server',
    action='store',
    required=True)
parser.add_argument(
    '--https-ca-cert',
    dest='https_ca_cert',
    action='store',
    required=True)
parser.add_argument(
    '--https-client-cert',
    dest='https_client_cert',
    action='store',
    required=True)
parser.add_argument(
    '--https-client-key',
    dest='https_client_key',
    action='store',
    required=True)
parser.add_argument(
    '--image-type',
    dest='image_type',
    action='store',
    required=True)
FLAGS = parser.parse_args()


class Client(threadedclient.WebSocketClient):

  def Loop(self):
    self.daemon = True
    self.connect()
    while True:
      self.send(json.dumps({
        'type': 'report',
        'data': {
          'hostname': socket.gethostname(),
          'uptime_seconds': self._Uptime(),
          'image_type': FLAGS.image_type,
        },
      }), False)
      time.sleep(5.0)

  def _Uptime(self):
    with open('/proc/uptime', 'r') as fh:
      return int(float(fh.readline().split(' ', 1)[0]))

  def received_message(self, msg):
    parsed = json.loads(str(msg))
    if parsed['type'] == 'image_types':
      assert FLAGS.image_type in parsed['data']['image_types']


def main():
  ssl_options = {
    'keyfile': FLAGS.https_client_key,
    'certfile': FLAGS.https_client_cert,
    'ca_certs': FLAGS.https_ca_cert,
  }
  client = Client('wss://%s/ws/slave' % FLAGS.server, protocols=['iconograph-slave'], ssl_options=ssl_options)
  client.Loop()


if __name__ == '__main__':
  main()
