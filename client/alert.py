#!/usr/bin/python3

import argparse
import sys
import time


parser = argparse.ArgumentParser(description='iconograph wait_for_service')
parser.add_argument(
    '--type',
    dest='type',
    action='store',
    choices={'happy', 'angry'},
    required=True)
FLAGS = parser.parse_args()


def Happy():
  yield '\a'
  time.sleep(3.0)


def Angry():
  yield '\a'
  time.sleep(0.2)


_TYPES = {
  'happy': Happy,
  'angry': Angry,
}


def main():
  handler = _TYPES[FLAGS.type]
  while True:
    for item in handler():
      sys.stdout.write(item)
      sys.stdout.flush()


if __name__ == '__main__':
  main()
