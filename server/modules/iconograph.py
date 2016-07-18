#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess

import icon_lib


parser = argparse.ArgumentParser(description='iconograph install module')
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
    '--https-ca-cert',
    dest='https_ca_cert',
    action='store')
parser.add_argument(
    '--server',
    dest='server',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def main():
  module = icon_lib.IconModule(FLAGS.chroot_path)
  module.InstallPackages(
      'upstart', 'daemontools-run', 'genisoimage', 'git', 'python3-openssl',
      'python3-requests', 'python3-ws4py')

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

  if FLAGS.https_ca_cert:
    shutil.copyfile(
        FLAGS.https_ca_cert,
        os.path.join(FLAGS.chroot_path, 'icon', 'config', 'ca.www.cert.pem'))

  client_flags = os.path.join(FLAGS.chroot_path, 'icon', 'config', 'client.flags')
  with open(client_flags, 'w') as fh:
    fh.write('--server=%(server)s\n' % {
      'server': FLAGS.server,
    })

  os.symlink(
      '/icon/iconograph/client',
      os.path.join(FLAGS.chroot_path, 'etc', 'service', 'iconograph-client'))


if __name__ == '__main__':
  main()
