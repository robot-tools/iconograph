#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess


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
FLAGS = parser.parse_args()


def Exec(*args, **kwargs):
    print('+', args)
    subprocess.check_call(args, **kwargs)


def ExecChroot(*args, **kwargs):
    Exec('chroot', FLAGS.chroot_path, *args, **kwargs)


def main():
  ExecChroot('adduser', '--system', '--group', '--disabled-password', 
             FLAGS.username)

  if FLAGS.sudo:
    ExecChroot('usermod', '--append', '--groups', 'sudo', FLAGS.username)

  if FLAGS.authorized_keys_file:
    dest_dir = os.path.join(FLAGS.chroot_path, 'home', FLAGS.username, '.ssh')
    dest_path = os.path.join(dest_dir, 'authorized_keys')
    os.mkdir(dest_dir)
    shutil.copy(FLAGS.authorized_keys_file, dest_path)
    ExecChroot('chown', '--recursive', '%s:%s' % (FLAGS.username, FLAGS.username), '/home/%s' % FLAGS.username)


if __name__ == '__main__':
  main()
