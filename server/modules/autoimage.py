#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess

import icon_lib


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


def main():
  module = icon_lib.IconModule(FLAGS.chroot_path)
  module.InstallPackages('git', 'grub-pc', 'python3-openssl', 'python3-requests')

  os.makedirs(os.path.join(FLAGS.chroot_path, 'icon', 'config'), exist_ok=True)

  if not os.path.exists(os.path.join(FLAGS.chroot_path, 'icon', 'iconograph')):
    module.ExecChroot(
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

  tags = {
      'device': FLAGS.device,
      'persistent_percent': FLAGS.persistent_percent,
      'server': FLAGS.server,
      'image_type': FLAGS.image_type,
      'image_flags': ' '.join(image_flags),
  }

  tool_path = os.path.join(FLAGS.chroot_path, 'icon', 'autoimage-%(image_type)s' % tags)
  os.makedirs(tool_path, exist_ok=True)

  script = os.path.join(tool_path, 'startup.sh')
  with open(script, 'w') as fh:
    os.fchmod(fh.fileno(), 0o755)
    fh.write("""\
#!/bin/bash

exec </dev/tty8 >/dev/tty8 2>&1
chvt 8
/icon/iconograph/client/wait_for_service.py --host=%(server)s --service=https
chvt 8
/icon/iconograph/client/image.py --device=%(device)s --persistent-percent=%(persistent_percent)d --ca-cert=/icon/config/ca.image.cert.pem --server=%(server)s --image-type=%(image_type)s %(image_flags)s
chvt 8

echo
echo "=================="
echo "autoimage complete"
echo "=================="
""" % tags)

  with module.ServiceFile('autoimage-%(image_type)s.service' % tags) as fh:
    fh.write("""
[Unit]
Description=AutoImage %(image_type)s

[Service]
Type=simple
RemainAfterExit=yes
ExecStart=/icon/autoimage-%(image_type)s/startup.sh

[Install]
WantedBy=multi-user.target
""" % tags)
  module.EnableService('autoimage-%(image_type)s.service' % tags)


if __name__ == '__main__':
  main()
