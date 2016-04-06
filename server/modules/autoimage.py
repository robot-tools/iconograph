#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess
from urllib import parse


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
    '--https-ca-cert',
    dest='https_ca_cert',
    action='store')
parser.add_argument(
    '--https-client-cert',
    dest='https_client_cert',
    action='store')
parser.add_argument(
    '--https-client-key',
    dest='https_client_key',
    action='store')
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
      'git', 'grub-pc', 'python3-openssl', 'python3-requests')

  ExecChroot(
      'git',
      'clone',
      'https://github.com/robot-tools/iconograph.git',
      'autoimage')

  os.mkdir(os.path.join(FLAGS.chroot_path, 'autoimage', 'config'))
  shutil.copyfile(
      FLAGS.ca_cert,
      os.path.join(FLAGS.chroot_path, 'autoimage', 'config', 'ca.cert.pem'))

  image_flags = []

  if FLAGS.https_ca_cert:
    https_ca_cert_path = os.path.join('autoimage', 'config', 'https-ca.cert.pem')
    shutil.copyfile(
      FLAGS.https_ca_cert,
      os.path.join(FLAGS.chroot_path, https_ca_cert_path))
    image_flags.extend([
        '--https-ca-cert', os.path.join('/', https_ca_cert_path),
    ])

  if FLAGS.https_client_cert and FLAGS.https_client_key:
    https_client_cert_path = os.path.join('autoimage', 'config', 'https-client.cert.pem')
    shutil.copyfile(
      FLAGS.https_client_cert,
      os.path.join(FLAGS.chroot_path, https_client_cert_path))
    https_client_key_path = os.path.join('autoimage', 'config', 'https-client.key.pem')
    shutil.copyfile(
      FLAGS.https_client_key,
      os.path.join(FLAGS.chroot_path, https_client_key_path))
    os.chmod(os.path.join(FLAGS.chroot_path, https_client_key_path), 0o400)
    image_flags.extend([
        '--https-client-cert', os.path.join('/', https_client_cert_path),
        '--https-client-key', os.path.join('/', https_client_key_path),
    ])

  parsed = parse.urlparse(FLAGS.base_url)

  init = os.path.join(FLAGS.chroot_path, 'etc', 'init', 'autoimage.conf')
  with open(init, 'w') as fh:
    fh.write("""
description "AutoImage"

start on stopped rc RUNLEVEL=[2345]

stop on runlevel [!2345]

script
  chvt 7
  /autoimage/client/wait_for_service.py --host=%(host)s --service=%(service)s </dev/tty7 >/dev/tty7 2>&1
  chvt 7
  /autoimage/imager/image.py --device=%(device)s --persistent-percent=%(persistent_percent)d --ca-cert=/autoimage/config/ca.cert.pem --base-url=%(base_url)s %(image_flags)s </dev/tty7 >/dev/tty7 2>&1
  chvt 7

  echo >/dev/tty7
  echo "==================" >/dev/tty7
  echo "autoimage complete" >/dev/tty7
  echo "==================" >/dev/tty7

  /autoimage/client/alert.py --type=happy </dev/tty7 >/dev/tty7
end script
""" % {
      'host': parsed.hostname,
      'service': parsed.port or parsed.scheme,
      'device': FLAGS.device,
      'persistent_percent': FLAGS.persistent_percent,
      'base_url': FLAGS.base_url,
      'image_flags': ' '.join(image_flags),
    })


if __name__ == '__main__':
  main()
