#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess


parser = argparse.ArgumentParser(description='iconograph autoimage')
parser.add_argument(
    '--base-url',
    dest='base_url',
    action='store',
    required=True)
parser.add_argument(
    '--ca-cert',
    dest='ca_cert',
    action='store',
    required=True)
parser.add_argument(
    '--chroot-path',
    dest='chroot_path',
    action='store',
    required=True)
parser.add_argument(
    '--device',
    dest='device',
    action='store',
    required=True)
parser.add_argument(
    '--persistent-percent',
    dest='persistent_percent',
    action='store',
    type=int,
    default=0)
FLAGS = parser.parse_args()


def Exec(*args, **kwargs):
  print('+', args)
  subprocess.check_call(args, **kwargs)


def ExecChroot(*args, **kwargs):
  Exec('chroot', FLAGS.chroot_path, *args, **kwargs)


def main():
  ExecChroot(
      'apt-get',
      'install',
      '--assume-yes',
      'git', 'grub-pc', 'python3-openssl')

  ExecChroot(
      'git',
      'clone',
      'https://github.com/robot-tools/iconograph.git',
      'autoimage')

  os.mkdir(os.path.join(FLAGS.chroot_path, 'autoimage', 'config'))
  shutil.copyfile(
      FLAGS.ca_cert,
      os.path.join(FLAGS.chroot_path, 'autoimage', 'config', 'ca.cert.pem'))

  init = os.path.join(FLAGS.chroot_path, 'etc', 'init', 'autoimage.conf')
  with open(init, 'w') as fh:
    fh.write("""
description "AutoImage"

start on net-device-up

script
  /autoimage/server/image.py --device=%(device)s --persistent-percent=%(persistent_percent)d --ca-cert=/autoimage/config/ca.cert.pem --base-url=%(base_url)s
end script
""" % {
      'device': FLAGS.device,
      'persistent_percent': FLAGS.persistent_percent,
      'base_url': FLAGS.base_url,
    })


if __name__ == '__main__':
  main()
