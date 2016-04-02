#!/usr/bin/python3

import argparse
import socket
import time


parser = argparse.ArgumentParser(description='iconograph wait_for_service')
parser.add_argument(
    '--host',
    dest='host',
    action='store',
    required=True)
parser.add_argument(
    '--service',
    dest='service',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def main():
  conn = (FLAGS.host, FLAGS.service)
  print('Trying to connect to %s:%s' % conn)
  while True:
    try:
      socket.create_connection(conn, timeout=5)
      break
    except Exception:
      time.sleep(1)
      continue
  print('Connection successful')


if __name__ == '__main__':
  main()
