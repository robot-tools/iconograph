#!/usr/bin/python3

import argparse
import os
import shutil

import icon_lib


parser = argparse.ArgumentParser(description='iconograph adduser')
parser.add_argument(
    '--authorized_keys_file',
    dest='authorized_keys_file',
    action='store')
parser.add_argument(
    '--chroot-path',
    dest='chroot_path',
    action='store',
    required=True)
parser.add_argument(
    '--sudo',
    dest='sudo',
    action='store_true')
parser.add_argument(
    '--username',
    dest='username',
    action='store',
    required=True)
parser.add_argument(
    '--groups',
    dest='groups',
    action='store')
FLAGS = parser.parse_args()


def main():
  module = icon_lib.IconModule(FLAGS.chroot_path)
  module.ExecChroot('adduser', '--system', '--group', '--disabled-password', 
                    '--shell=/bin/bash', FLAGS.username)

  if FLAGS.sudo:
    with open(os.path.join(FLAGS.chroot_path, 'etc', 'sudoers.d', FLAGS.username), 'w') as fh:
      fh.write('%s\tALL=(ALL) NOPASSWD: ALL\n' % FLAGS.username)

  if FLAGS.groups:
    for group in FLAGS.groups.split(","):
      module.ExecChroot('adduser', FLAGS.username, group)

  if FLAGS.authorized_keys_file:
    dest_dir = os.path.join(FLAGS.chroot_path, 'home', FLAGS.username, '.ssh')
    dest_path = os.path.join(dest_dir, 'authorized_keys')
    os.mkdir(dest_dir)
    shutil.copy(FLAGS.authorized_keys_file, dest_path)
    module.ExecChroot('chown', '--recursive', '%s:%s' % (FLAGS.username, FLAGS.username), '/home/%s' % FLAGS.username)


if __name__ == '__main__':
  main()
