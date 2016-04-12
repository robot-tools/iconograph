#!/usr/bin/python3

import argparse
import glob
import os
import subprocess


parser = argparse.ArgumentParser(description='iconograph openssh')
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
      'openssh-server')

  for path in glob.glob(os.path.join(FLAGS.chroot_path, 'etc', 'ssh', 'ssh_host_*')):
    os.unlink(path)

  os.symlink(
      '/systemid/ssh_host_ed25519_key',
      os.path.join(FLAGS.chroot_path, 'etc', 'ssh', 'ssh_host_ed25519_key'))


if __name__ == '__main__':
  main()
