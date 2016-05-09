#!/usr/bin/python3

import argparse
import json
import os
import socket
import time
from ws4py.client import threadedclient


parser = argparse.ArgumentParser(description='iconograph fetcher')
parser.add_argument(
    '--config',
    dest='config',
    action='store',
    default='/etc/iconograph.json')
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
    '--server',
    dest='server',
    action='store',
    required=True)
FLAGS = parser.parse_args()


class Client(threadedclient.WebSocketClient):

  def __init__(self, config_path, *args, **kwargs):
    super().__init__(*args, **kwargs)
    with open(config_path, 'r') as fh:
      self._config = json.load(fh)

  def Loop(self):
    self.daemon = True
    self.connect()
    while True:
      report = {
        'hostname': socket.gethostname(),
        'uptime_seconds': self._Uptime(),
        'next_timestamp': self._NextTimestamp(),
      }
      report.update(self._config)
      self.send(json.dumps({
        'type': 'report',
        'data': report,
      }), False)
      time.sleep(5.0)

  def _Uptime(self):
    with open('/proc/uptime', 'r') as fh:
      return int(float(fh.readline().split(' ', 1)[0]))

  def _NextTimestamp(self):
    next_image = os.path.basename(os.readlink('/isodevice/iconograph/current'))
    return int(next_image.split('.', 1)[0])

  def received_message(self, msg):
    parsed = json.loads(msg.data.decode('utf8'))
    if parsed['type'] == 'image_types':
      assert self._config['image_type'] in parsed['data']['image_types']


def main():
  ssl_options = {
    'keyfile': FLAGS.https_client_key,
    'certfile': FLAGS.https_client_cert,
    'ca_certs': FLAGS.https_ca_cert,
  }
  client = Client(
      FLAGS.config,
      'wss://%s/ws/slave' % FLAGS.server,
      protocols=['iconograph-slave'],
      ssl_options=ssl_options)
  client.Loop()


if __name__ == '__main__':
  main()
