#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess
from urllib import parse


parser = argparse.ArgumentParser(description='iconograph autoimage')
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
parser.add_argument(
    '--persistent-percent',
    dest='persistent_percent',
    action='store',
    type=int,
    default=0)
parser.add_argument(
    '--server',
    dest='server',
    action='store',
    required=True)
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
      'git', 'grub-pc', 'python3-openssl', 'python3-requests')

  os.makedirs(os.path.join(FLAGS.chroot_path, 'icon', 'config'), exist_ok=True)

  if not os.path.exists(os.path.join(FLAGS.chroot_path, 'icon', 'iconograph')):
    ExecChroot(
        'git',
        'clone',
        'https://github.com/robot-tools/iconograph.git',
        'icon/iconograph')

  shutil.copyfile(
      FLAGS.ca_cert,
      os.path.join(FLAGS.chroot_path, 'icon', 'config', 'ca.image.cert.pem'))

  image_flags = []

  https_ca_cert_path = os.path.join('icon', 'config', 'ca.www.cert.pem')
  shutil.copyfile(
    FLAGS.https_ca_cert,
    os.path.join(FLAGS.chroot_path, https_ca_cert_path))
  image_flags.extend([
      '--https-ca-cert', os.path.join('/', https_ca_cert_path),
  ])

  https_client_cert_path = os.path.join('icon', 'config', 'client.www.cert.pem')
  shutil.copyfile(
    FLAGS.https_client_cert,
    os.path.join(FLAGS.chroot_path, https_client_cert_path))
  https_client_key_path = os.path.join('icon', 'config', 'client.www.key.pem')
  shutil.copyfile(
    FLAGS.https_client_key,
  os.path.join(FLAGS.chroot_path, https_client_key_path))
  os.chmod(os.path.join(FLAGS.chroot_path, https_client_key_path), 0o400)
  image_flags.extend([
      '--https-client-cert', os.path.join('/', https_client_cert_path),
      '--https-client-key', os.path.join('/', https_client_key_path),
  ])

  init = os.path.join(FLAGS.chroot_path, 'etc', 'init', 'autoimage.conf')
  with open(init, 'w') as fh:
    fh.write("""
description "AutoImage"

start on runlevel [2345]

script
  exec </dev/tty8 >/dev/tty8 2>&1
  chvt 8
  /icon/iconograph/client/wait_for_service.py --host=%(host)s --service=%(service)s
  chvt 8
  /icon/iconograph/client/image.py --device=%(device)s --persistent-percent=%(persistent_percent)d --ca-cert=/icon/config/ca.image.cert.pem --server=%(server)s --image-type=%(image_type)s %(image_flags)s
  chvt 8

  echo
  echo "=================="
  echo "autoimage complete"
  echo "=================="

  /icon/iconograph/client/alert.py --type=happy
end script
""" % {
      'host': FLAGS.server,
      'service': 'https',
      'device': FLAGS.device,
      'persistent_percent': FLAGS.persistent_percent,
      'server': FLAGS.server,
      'image_type': FLAGS.image_type,
      'image_flags': ' '.join(image_flags),
    })


if __name__ == '__main__':
  main()
