#!/usr/bin/python3

import argparse
import os


parser = argparse.ArgumentParser(description='iconograph systemid')
parser.add_argument(
    '--chroot-path',
    dest='chroot_path',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def main():
  os.mkdir(os.path.join(FLAGS.chroot_path, 'systemid'))

  init = os.path.join(FLAGS.chroot_path, 'etc', 'init', 'systemid.conf')
  with open(init, 'w') as fh:
    fh.write("""
description "Mount /systemid"

start on filesystem
task

emits systemid-ready

script
  mount LABEL=SYSTEMID /systemid
  . /systemid/systemid
  echo ${SYSTEMID} > /etc/hostname
  hostname --file /etc/hostname
  grep ${SYSTEMID} /etc/hosts >/dev/null || echo "127.0.2.1 ${SYSTEMID}" >> /etc/hosts
  initctl emit --no-wait systemid-ready
end script
""")


if __name__ == '__main__':
  main()