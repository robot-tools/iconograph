#!/usr/bin/python3

import argparse
import os


parser = argparse.ArgumentParser(description='iconograph persistent')
parser.add_argument(
    '--chroot-path',
    dest='chroot_path',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def main():
  os.mkdir(os.path.join(FLAGS.chroot_path, 'persistent'))

  init = os.path.join(FLAGS.chroot_path, 'etc', 'init', 'persistent.conf')
  with open(init, 'w') as fh:
    fh.write("""
description "Mount /persistent"

start on filesystem
task

emits persistent-ready

script
  mount LABEL=PERSISTENT /persistent
  initctl emit --no-wait persistent-ready
end script
""")


if __name__ == '__main__':
  main()
