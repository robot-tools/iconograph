#!/usr/bin/python3

import argparse
import glob
import os

import icon_lib


parser = argparse.ArgumentParser(description='iconograph openssh')
parser.add_argument(
    '--chroot-path',
    dest='chroot_path',
    action='store',
    required=True)
FLAGS = parser.parse_args()


def main():
  module = icon_lib.IconModule(FLAGS.chroot_path)
  module.InstallPackages('openssh-server')

  for path in glob.glob(os.path.join(FLAGS.chroot_path, 'etc', 'ssh', 'ssh_host_*')):
    os.unlink(path)

  os.symlink(
      '/systemid/ssh_host_ed25519_key',
      os.path.join(FLAGS.chroot_path, 'etc', 'ssh', 'ssh_host_ed25519_key'))


if __name__ == '__main__':
  main()
