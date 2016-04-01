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
      'daemontools-run', 'git', 'python3-openssl')

  ExecChroot(
      'git',
      'clone',
      'https://github.com/robot-tools/iconograph.git')

  os.mkdir(os.path.join(FLAGS.chroot_path, 'iconograph', 'config'))
  shutil.copyfile(
      FLAGS.ca_cert,
      os.path.join(FLAGS.chroot_path, 'iconograph', 'config', 'ca.cert.pem'))

  path = os.path.join(FLAGS.chroot_path, 'iconograph', 'client', 'flags')
  with open(path, 'w') as fh:
    fh.write('--base-url=%(base_url)s\n' % {
      'base_url': FLAGS.base_url,
    })

  os.symlink(
      '/iconograph/client',
      os.path.join(FLAGS.chroot_path, 'etc', 'service', 'iconograph'))


if __name__ == '__main__':
  main()
