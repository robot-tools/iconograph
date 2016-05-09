#!/usr/bin/python3

import argparse
import os
import shutil
import subprocess


parser = argparse.ArgumentParser(description='iconograph install module')
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
    '--https-ca-cert',
    dest='https_ca_cert',
    action='store')
parser.add_argument(
    '--max-images',
    dest='max_images',
    action='store',
    type=int,
    default=5)
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
      'daemontools-run', 'genisoimage', 'git', 'python3-openssl',
      'python3-requests')

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

  if FLAGS.https_ca_cert:
    shutil.copyfile(
        FLAGS.https_ca_cert,
        os.path.join(FLAGS.chroot_path, 'icon', 'config', 'ca.www.cert.pem'))


  path = os.path.join(FLAGS.chroot_path, 'icon', 'config', 'fetcher.flags')
  with open(path, 'w') as fh:
    fh.write('--base-url=%(base_url)s --max-images=%(max_images)d\n' % {
      'base_url': FLAGS.base_url,
      'max_images': FLAGS.max_images,
    })

  os.symlink(
      '/icon/iconograph/client',
      os.path.join(FLAGS.chroot_path, 'etc', 'service', 'iconograph-client'))


if __name__ == '__main__':
  main()
